"""Celery tasks for the GmailMind scheduler.

Tasks:
  1. ``run_gmailmind_for_user`` — Run one iteration of the agent loop for a user.
  2. ``process_due_followups``  — Find and trigger follow-ups whose due time has passed.
  3. ``send_daily_report``      — Generate and email the end-of-day summary.

Every task:
  - Handles exceptions gracefully (never crashes the worker).
  - Logs start time, end time, and duration.
  - Updates agent status in the database (running / idle / error).
"""

import asyncio
import logging
import time
import traceback
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from config.database import SessionLocal
from scheduler.celery_app import app

logger = logging.getLogger(__name__)

# Ensure Celery worker actually outputs our logs
logging.basicConfig(level=logging.INFO)

# --- Module-load confirmation (visible even if task never executes) ---
print("=== TASKS MODULE LOADED ===")
logger.info("=== TASKS MODULE LOADED ===")


# ============================================================================
# Agent status helpers  (status stored in DB table ``agent_status``)
# ============================================================================

_CREATE_STATUS_TABLE = """
CREATE TABLE IF NOT EXISTS agent_status (
    user_id   VARCHAR(128) PRIMARY KEY,
    status    VARCHAR(32)  NOT NULL DEFAULT 'idle',
    last_run  TIMESTAMP WITH TIME ZONE,
    error_msg TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""


def _ensure_status_table() -> None:
    """Create the ``agent_status`` table if it doesn't exist yet."""
    try:
        db = SessionLocal()
        try:
            db.execute(text(_CREATE_STATUS_TABLE))
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.debug("Status table check skipped (DB may be unavailable): %s", exc)


def _set_agent_status(user_id: str, status: str, error_msg: str = "") -> None:
    """Update the agent's status row in the database.

    Args:
        user_id: The user identifier.
        status: One of ``'running'``, ``'idle'``, ``'error'``.
        error_msg: Optional error description (cleared on success).
    """
    try:
        db = SessionLocal()
        try:
            db.execute(
                text("""
                    INSERT INTO agent_status (user_id, status, last_run, error_msg, updated_at)
                    VALUES (:uid, :status, :now, :err, :now)
                    ON CONFLICT (user_id) DO UPDATE
                        SET status     = :status,
                            last_run   = :now,
                            error_msg  = :err,
                            updated_at = :now
                """),
                {
                    "uid": user_id,
                    "status": status,
                    "now": datetime.now(timezone.utc),
                    "err": error_msg,
                },
            )
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Failed to update agent status for %s: %s", user_id, exc)


# ============================================================================
# Task 0 — Dispatcher: query all active users and fan out per-user tasks
# ============================================================================


@app.task(bind=True, name="scheduler.tasks.run_gmailmind_all_users")
def run_gmailmind_all_users(self) -> dict[str, Any]:
    """Query all active, non-paused users and dispatch a per-user task for each.

    This is the task that Celery Beat calls on every polling interval.
    It fans out individual ``run_gmailmind_for_user`` tasks so each user
    gets their own task (independent failure, parallel if concurrency > 1).
    """
    print("=== DISPATCHER: run_gmailmind_all_users STARTED ===")
    logger.info("=== DISPATCHER: run_gmailmind_all_users STARTED ===")

    try:
        db = SessionLocal()
        try:
            rows = db.execute(
                text("""
                    SELECT u.id, u.email
                    FROM users u
                    JOIN user_agents ua ON ua.user_id = CAST(u.id AS VARCHAR)
                    WHERE u.setup_complete = true
                      AND u.is_active = true
                      AND ua.is_paused = false
                """)
            ).fetchall()
        finally:
            db.close()

        if not rows:
            logger.info("[run_gmailmind_all_users] No active users found.")
            return {"status": "no_users", "dispatched": 0}

        dispatched = []
        for row in rows:
            uid = str(row[0])
            email = row[1] if len(row) > 1 else "unknown"
            logger.info("[run_gmailmind_all_users] Dispatching task for user=%s (%s)", uid, email)
            run_gmailmind_for_user.apply_async(
                args=(uid,),
                queue="agent",
            )
            dispatched.append(uid)

        logger.info(
            "=== DISPATCHER: dispatched %d user tasks: %s ===",
            len(dispatched), dispatched,
        )
        return {"status": "dispatched", "dispatched": len(dispatched), "user_ids": dispatched}

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(
            "=== DISPATCHER FAILED ===\n%s", tb,
        )
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}", "traceback": tb}


# ============================================================================
# Task 1 — Run the GmailMind agent loop for a single user
# ============================================================================


@app.task(bind=True, name="scheduler.tasks.run_gmailmind_for_user", max_retries=1)
def run_gmailmind_for_user(self, user_id: str) -> dict[str, Any]:
    """Run one iteration of the GmailMind reasoning loop for a user.

    Loads the user's business config, executes the agent loop in
    ``single_run=True`` mode, and records timing + status.

    Args:
        user_id: The user identifier whose inbox to process.

    Returns:
        A dict with ``status``, ``duration_s``, and summary counts.
    """
    # Unconditional print — bypasses any logging misconfiguration
    print(f"=== TASK EXECUTING user_id={user_id} ===")
    logger.info("=== TASK EXECUTING user_id=%s ===", user_id)

    start = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        "========== [run_gmailmind_for_user] TASK STARTED ==========\n"
        "  user_id   : %s\n"
        "  started_at: %s\n"
        "  task_id   : %s",
        user_id, started_at, self.request.id,
    )

    try:
        # --- Step 1: Ensure status table ---
        logger.info("[run_gmailmind_for_user] Step 1/6: Ensuring agent_status table exists...")
        _ensure_status_table()
        _set_agent_status(user_id, "running")
        logger.info("[run_gmailmind_for_user] Step 1/6: DONE — agent status set to 'running'")

        # --- Step 2: Orchestrator gate check ---
        logger.info("[run_gmailmind_for_user] Step 2/6: Running orchestrator gate check...")
        try:
            from orchestrator.orchestrator import GmailMindOrchestrator

            orchestrator = GmailMindOrchestrator()
            routing = orchestrator.process_user(user_id)
            logger.info(
                "[run_gmailmind_for_user] Step 2/6: DONE — routing=%s", routing,
            )
        except Exception as exc:
            logger.error(
                "[run_gmailmind_for_user] Step 2/6: FAILED — orchestrator error:\n%s",
                traceback.format_exc(),
            )
            raise

        if routing.get("status") == "skipped":
            _set_agent_status(user_id, "idle")
            duration = time.monotonic() - start
            logger.info(
                "[run_gmailmind_for_user] SKIPPED user=%s reason=%s duration=%.1fs",
                user_id, routing.get("reason", "unknown"), duration,
            )
            return {
                "status": "skipped",
                "user_id": user_id,
                "started_at": started_at,
                "duration_s": round(duration, 2),
                "reason": routing.get("reason", "unknown"),
            }

        # --- Step 3: Load user credentials / Gmail token ---
        logger.info("[run_gmailmind_for_user] Step 3/6: Loading Gmail credentials for user=%s...", user_id)
        try:
            from memory.long_term import get_user_credentials

            creds = get_user_credentials(user_id)
            if creds:
                has_token = bool(creds.get("token"))
                has_refresh = bool(creds.get("refresh_token"))
                expiry = creds.get("expiry", "N/A")
                logger.info(
                    "[run_gmailmind_for_user] Step 3/6: DONE — Gmail token loaded\n"
                    "  has_access_token : %s\n"
                    "  has_refresh_token: %s\n"
                    "  token_expiry     : %s",
                    has_token, has_refresh, expiry,
                )
            else:
                logger.warning(
                    "[run_gmailmind_for_user] Step 3/6: WARNING — No credentials found for user=%s", user_id,
                )
        except Exception as exc:
            logger.error(
                "[run_gmailmind_for_user] Step 3/6: FAILED — credential check error:\n%s",
                traceback.format_exc(),
            )
            # Don't raise here — let EmailProcessor handle it with its own error

        # --- Step 4: Create EmailProcessor ---
        logger.info("[run_gmailmind_for_user] Step 4/6: Creating EmailProcessor for user=%s...", user_id)
        try:
            from agent.email_processor import EmailProcessor

            processor = EmailProcessor(user_id)
            logger.info("[run_gmailmind_for_user] Step 4/6: DONE — EmailProcessor created")
        except Exception as exc:
            logger.error(
                "[run_gmailmind_for_user] Step 4/6: FAILED — EmailProcessor init error:\n%s",
                traceback.format_exc(),
            )
            raise

        # --- Step 5: Process inbox ---
        logger.info("[run_gmailmind_for_user] Step 5/6: Processing inbox (async)...")
        try:
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(processor.process_inbox())
            finally:
                loop.close()

            emails_processed = result.get("processed", 0)
            total_emails = result.get("total", 0)
            error_in_result = result.get("error")

            if error_in_result:
                logger.error(
                    "[run_gmailmind_for_user] Step 5/6: PIPELINE ERROR — %s", error_in_result,
                )
            else:
                logger.info(
                    "[run_gmailmind_for_user] Step 5/6: DONE — Emails fetched: %d, Processed: %d\n"
                    "  full result: %s",
                    total_emails, emails_processed, result,
                )
        except Exception as exc:
            logger.error(
                "[run_gmailmind_for_user] Step 5/6: FAILED — process_inbox error:\n%s",
                traceback.format_exc(),
            )
            raise

        # --- Step 6: Finalize ---
        duration = time.monotonic() - start
        _set_agent_status(user_id, "idle")
        logger.info(
            "========== [run_gmailmind_for_user] TASK COMPLETED ==========\n"
            "  user_id         : %s\n"
            "  duration         : %.1fs\n"
            "  emails_processed : %d\n"
            "  industry         : %s\n"
            "  tier             : %s",
            user_id, duration, emails_processed,
            routing.get("industry", "general"), routing.get("tier", "tier2"),
        )

        return {
            "status": "success",
            "user_id": user_id,
            "started_at": started_at,
            "duration_s": round(duration, 2),
            "emails_processed": emails_processed,
            "routing": routing,
            "pipeline_result": result,
        }

    except Exception as exc:
        duration = time.monotonic() - start
        error_msg = f"{type(exc).__name__}: {exc}"
        tb = traceback.format_exc()

        try:
            _set_agent_status(user_id, "error", error_msg=error_msg)
        except Exception:
            pass

        logger.error(
            "========== [run_gmailmind_for_user] TASK FAILED ==========\n"
            "  user_id  : %s\n"
            "  duration : %.1fs\n"
            "  error    : %s\n"
            "  traceback:\n%s",
            user_id, duration, error_msg, tb,
        )

        return {
            "status": "error",
            "user_id": user_id,
            "started_at": started_at,
            "duration_s": round(duration, 2),
            "error": error_msg,
            "traceback": tb,
        }


# ============================================================================
# Task 2 — Process due follow-ups
# ============================================================================


@app.task(bind=True, name="scheduler.tasks.process_due_followups", max_retries=1)
def process_due_followups(self) -> dict[str, Any]:
    """Check the database for follow-ups that are now due and trigger
    the agent to act on each one.

    Returns:
        A dict with ``status``, ``processed`` count, and ``duration_s``.
    """
    start = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()
    logger.info("[process_due_followups] START at %s", started_at)

    try:
        from agent.gmailmind import create_agent
        from agent.reasoning_loop import _process_due_followup
        from config.business_config import load_business_config
        from memory.long_term import get_pending_follow_ups

        now = datetime.now(timezone.utc)
        pending = get_pending_follow_ups()
        due = [fu for fu in pending if fu.due_time <= now]

        if not due:
            duration = time.monotonic() - start
            logger.info(
                "[process_due_followups] No due follow-ups. duration=%.1fs", duration,
            )
            return {
                "status": "success",
                "processed": 0,
                "duration_s": round(duration, 2),
            }

        # Load default config and create agent for follow-up processing
        config = load_business_config()
        agent = create_agent(config)

        loop = asyncio.new_event_loop()
        processed = 0
        try:
            for followup in due:
                try:
                    fu_dict = followup.model_dump(mode="json")
                    loop.run_until_complete(
                        _process_due_followup(agent, fu_dict, config)
                    )
                    processed += 1
                except Exception as exc:
                    logger.error(
                        "[process_due_followups] Failed for follow-up id=%s: %s",
                        followup.id, exc,
                    )
        finally:
            loop.close()

        duration = time.monotonic() - start
        logger.info(
            "[process_due_followups] DONE processed=%d/%d duration=%.1fs",
            processed, len(due), duration,
        )

        return {
            "status": "success",
            "processed": processed,
            "total_due": len(due),
            "duration_s": round(duration, 2),
        }

    except Exception as exc:
        duration = time.monotonic() - start
        logger.exception(
            "[process_due_followups] ERROR after %.1fs: %s", duration, exc,
        )

        return {
            "status": "error",
            "duration_s": round(duration, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }


# ============================================================================
# Task 3 — Send daily summary report
# ============================================================================


@app.task(bind=True, name="scheduler.tasks.send_daily_report", max_retries=2)
def send_daily_report(self, user_id: str) -> dict[str, Any]:
    """Generate and email the end-of-day summary report.

    Tier-aware behaviour:
      - tier1: email report only.
      - tier2/tier3: email + WhatsApp report (if configured).
      - HR industry users: include HR recruitment metrics.

    Args:
        user_id: The user to generate the report for.

    Returns:
        A dict with ``status`` and report statistics.
    """
    start = time.monotonic()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    logger.info("[send_daily_report] START user=%s date=%s", user_id, today)

    try:
        from config.business_config import load_business_config
        from config.settings import ESCALATION_WHATSAPP_TO
        from memory.long_term import get_pending_follow_ups
        from memory.schemas import ActionLogRead

        config = load_business_config(user_id=user_id)
        owner_email = config.get("owner_email", "")

        # --- Determine user tier and industry ---
        user_tier = "tier2"
        user_industry = "general"
        try:
            from orchestrator.feature_gates import FeatureGate
            from orchestrator.user_router import UserRouter

            user_tier = FeatureGate().get_user_tier(user_id)
            user_industry = UserRouter().get_user_industry(user_id)
        except Exception:
            pass

        # --- Gather today's actions from the database ---
        db = SessionLocal()
        try:
            from models.schemas import ActionLog
            from sqlalchemy import cast, Date, select, func

            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0,
            )

            stmt = (
                select(ActionLog)
                .where(ActionLog.timestamp >= today_start)
                .order_by(ActionLog.timestamp.asc())
            )
            rows = db.execute(stmt).scalars().all()

            total_actions = len(rows)
            tools_used: dict[str, int] = {}
            email_senders: set[str] = set()
            for row in rows:
                tools_used[row.tool_used] = tools_used.get(row.tool_used, 0) + 1
                email_senders.add(row.email_from)

            # Count pending follow-ups
            pending_followups = get_pending_follow_ups(db=db)
        finally:
            db.close()

        # --- Build report ---
        report: dict[str, Any] = {
            "date": today,
            "user_id": user_id,
            "total_actions": total_actions,
            "emails_processed": total_actions,
            "unique_senders": len(email_senders),
            "tools_breakdown": tools_used,
            "pending_followups": len(pending_followups),
            "labeled": 0,
            "archived": 0,
            "escalated": 0,
        }

        # --- Include HR metrics if industry is 'hr' ---
        if user_industry == "hr":
            try:
                from agent.report_generator import ReportGenerator

                rg = ReportGenerator()
                hr_data = rg.generate_hr_daily_summary(user_id, today)
                report["hr_data"] = hr_data
                logger.info("[send_daily_report] HR metrics included for user=%s", user_id)
            except Exception as hr_exc:
                logger.warning("[send_daily_report] Could not include HR metrics: %s", hr_exc)

        # --- Format as email body ---
        tool_lines = "\n".join(
            f"    - {tool}: {count}" for tool, count in tools_used.items()
        ) or "    (no actions today)"

        email_body = f"""GmailMind Daily Summary — {today}
{'=' * 50}

Total Actions Taken:   {total_actions}
Unique Senders:        {len(email_senders)}
Pending Follow-ups:    {len(pending_followups)}

Tools Used:
{tool_lines}
"""

        # Append HR section to email if applicable
        if report.get("hr_data"):
            hr = report["hr_data"]
            email_body += f"""
HR Recruitment Summary:
    New CVs:              {hr.get('new_candidates', 0)}
    Interviews Scheduled: {hr.get('interviews_scheduled', 0)}
    Interviews Today:     {hr.get('interviews_today', 0)}
    Hires:                {hr.get('hires', 0)}
    Rejections:           {hr.get('rejections', 0)}
"""

        email_body += "\n---\nThis report was generated automatically by GmailMind.\n"

        # --- Send via Gmail (if configured) ---
        if owner_email:
            try:
                from agent.tool_wrappers import services
                from tools.gmail_tools import send_email as gmail_send

                gmail_svc = services.get("gmail")
                if gmail_svc:
                    gmail_send(
                        gmail_svc,
                        to=owner_email,
                        subject=f"GmailMind Daily Report — {today}",
                        body=email_body,
                    )
                    logger.info(
                        "[send_daily_report] Report emailed to %s", owner_email,
                    )
                else:
                    logger.warning(
                        "[send_daily_report] Gmail service not available — "
                        "report generated but not emailed.",
                    )
            except Exception as send_exc:
                logger.warning(
                    "[send_daily_report] Could not send email: %s", send_exc,
                )
        else:
            logger.info("[send_daily_report] No owner_email configured — skipping send.")

        # --- Send WhatsApp report for tier2/tier3 ---
        if user_tier in ("tier2", "tier3") and ESCALATION_WHATSAPP_TO:
            try:
                from tools.whatsapp_tools import send_whatsapp_report

                send_whatsapp_report(
                    to_phone=ESCALATION_WHATSAPP_TO,
                    report=report,
                    report_type="daily",
                )
                logger.info(
                    "[send_daily_report] WhatsApp report sent to %s",
                    ESCALATION_WHATSAPP_TO,
                )
            except Exception as wa_exc:
                logger.warning(
                    "[send_daily_report] WhatsApp report failed: %s", wa_exc,
                )

        # --- Reset daily summary accumulator ---
        try:
            from agent.reasoning_loop import reset_daily_summary
            reset_daily_summary()
        except Exception:
            pass

        duration = time.monotonic() - start
        logger.info(
            "[send_daily_report] DONE user=%s actions=%d duration=%.1fs",
            user_id, total_actions, duration,
        )

        return {
            "status": "success",
            "user_id": user_id,
            "date": today,
            "report": report,
            "duration_s": round(duration, 2),
        }

    except Exception as exc:
        duration = time.monotonic() - start
        logger.exception(
            "[send_daily_report] ERROR user=%s after %.1fs: %s",
            user_id, duration, exc,
        )

        return {
            "status": "error",
            "user_id": user_id,
            "date": today,
            "duration_s": round(duration, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }


# ============================================================================
# Task 4 — Send weekly HR recruitment report
# ============================================================================


@app.task(bind=True, name="scheduler.tasks.send_hr_weekly_report", max_retries=2)
def send_hr_weekly_report(self, user_id: str = "default") -> dict[str, Any]:
    """Generate and send a weekly HR recruitment report.

    Sends via email and WhatsApp (if configured).

    Args:
        user_id: The recruiter/user ID.

    Returns:
        A dict with ``status`` and report data.
    """
    start = time.monotonic()
    logger.info("[send_hr_weekly_report] START user=%s", user_id)

    try:
        from config.business_config import load_business_config
        from config.settings import ESCALATION_WHATSAPP_TO
        from skills.hr_skills import HRSkills

        hr_skills = HRSkills()
        report = hr_skills.generate_weekly_recruitment_report(user_id)
        whatsapp_text = hr_skills.format_report_for_whatsapp(report)

        config = load_business_config(user_id=user_id)
        owner_email = config.get("owner_email", "")

        # --- Send via email ---
        if owner_email:
            try:
                from agent.tool_wrappers import services
                from tools.gmail_tools import send_email as gmail_send

                gmail_svc = services.get("gmail")
                if gmail_svc:
                    gmail_send(
                        gmail_svc,
                        to=owner_email,
                        subject=f"GmailMind HR Weekly Report — {report.get('week_start', '')[:10]}",
                        body=whatsapp_text,
                    )
                    logger.info(
                        "[send_hr_weekly_report] Report emailed to %s", owner_email,
                    )
            except Exception as send_exc:
                logger.warning(
                    "[send_hr_weekly_report] Email send failed: %s", send_exc,
                )

        # --- Send via WhatsApp ---
        if ESCALATION_WHATSAPP_TO:
            try:
                from tools.whatsapp_tools import send_whatsapp_report

                send_whatsapp_report(
                    to_phone=ESCALATION_WHATSAPP_TO,
                    report=report,
                    report_type="weekly",
                )
                logger.info(
                    "[send_hr_weekly_report] WhatsApp report sent to %s",
                    ESCALATION_WHATSAPP_TO,
                )
            except Exception as wa_exc:
                logger.warning(
                    "[send_hr_weekly_report] WhatsApp report failed: %s", wa_exc,
                )

        duration = time.monotonic() - start
        logger.info(
            "[send_hr_weekly_report] DONE user=%s duration=%.1fs", user_id, duration,
        )

        return {
            "status": "success",
            "user_id": user_id,
            "report": report,
            "duration_s": round(duration, 2),
        }

    except Exception as exc:
        duration = time.monotonic() - start
        logger.exception(
            "[send_hr_weekly_report] ERROR user=%s after %.1fs: %s",
            user_id, duration, exc,
        )

        return {
            "status": "error",
            "user_id": user_id,
            "duration_s": round(duration, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }


# ============================================================================
# Task 6 — Send Real Estate Weekly Report
# ============================================================================


@app.task(bind=True, name="scheduler.tasks.send_real_estate_weekly_report")
def send_real_estate_weekly_report(self, user_id: str = "default") -> dict[str, Any]:
    """Generate and send weekly Real Estate property management report.

    Args:
        user_id: The property manager/agent user ID.

    Returns:
        A dict with ``status`` and report data.
    """
    start = time.monotonic()
    logger.info("[send_real_estate_weekly_report] START user=%s", user_id)

    try:
        from config.business_config import load_business_config
        from config.settings import ESCALATION_WHATSAPP_TO
        from skills.real_estate_skills import RealEstateSkills

        re_skills = RealEstateSkills()
        report = re_skills.generate_weekly_property_report(user_id)
        whatsapp_text = re_skills.format_report_for_whatsapp(report)

        config = load_business_config(user_id=user_id)
        owner_email = config.get("owner_email", "")

        # --- Send via email ---
        if owner_email:
            try:
                from agent.tool_wrappers import services
                from tools.gmail_tools import send_email as gmail_send

                gmail_svc = services.get("gmail")
                if gmail_svc:
                    gmail_send(
                        gmail_svc,
                        to=owner_email,
                        subject=f"GmailMind Real Estate Weekly Report",
                        body=whatsapp_text,
                    )
                    logger.info(
                        "[send_real_estate_weekly_report] Report emailed to %s", owner_email,
                    )
            except Exception as send_exc:
                logger.warning(
                    "[send_real_estate_weekly_report] Email send failed: %s", send_exc,
                )

        # --- Send via WhatsApp ---
        if ESCALATION_WHATSAPP_TO:
            try:
                from tools.whatsapp_tools import send_whatsapp_report

                send_whatsapp_report(
                    to_phone=ESCALATION_WHATSAPP_TO,
                    report=report,
                    report_type="weekly",
                )
                logger.info(
                    "[send_real_estate_weekly_report] WhatsApp report sent to %s",
                    ESCALATION_WHATSAPP_TO,
                )
            except Exception as wa_exc:
                logger.warning(
                    "[send_real_estate_weekly_report] WhatsApp report failed: %s", wa_exc,
                )

        duration = time.monotonic() - start
        logger.info(
            "[send_real_estate_weekly_report] DONE user=%s duration=%.1fs", user_id, duration,
        )

        return {
            "status": "success",
            "user_id": user_id,
            "report": report,
            "duration_s": round(duration, 2),
        }

    except Exception as exc:
        duration = time.monotonic() - start
        logger.exception(
            "[send_real_estate_weekly_report] ERROR user=%s after %.1fs: %s",
            user_id, duration, exc,
        )

        return {
            "status": "error",
            "user_id": user_id,
            "duration_s": round(duration, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }


# ============================================================================
# Task 7 — Send E-commerce Weekly Report
# ============================================================================


@app.task(bind=True, name="scheduler.tasks.send_ecommerce_weekly_report")
def send_ecommerce_weekly_report(self, user_id: str = "default") -> dict[str, Any]:
    """Generate and send weekly E-commerce activity report.

    Args:
        user_id: The e-commerce business user ID.

    Returns:
        A dict with ``status`` and report data.
    """
    start = time.monotonic()
    logger.info("[send_ecommerce_weekly_report] START user=%s", user_id)

    try:
        from config.business_config import load_business_config
        from config.settings import ESCALATION_WHATSAPP_TO
        from skills.ecommerce_skills import EcommerceSkills

        ecom_skills = EcommerceSkills()
        report = ecom_skills.generate_weekly_ecommerce_report(user_id)
        whatsapp_text = ecom_skills.format_report_for_whatsapp(report)

        config = load_business_config(user_id=user_id)
        owner_email = config.get("owner_email", "")

        # --- Send via email ---
        if owner_email:
            try:
                from agent.tool_wrappers import services
                from tools.gmail_tools import send_email as gmail_send

                gmail_svc = services.get("gmail")
                if gmail_svc:
                    gmail_send(
                        gmail_svc,
                        to=owner_email,
                        subject=f"GmailMind E-commerce Weekly Report",
                        body=whatsapp_text,
                    )
                    logger.info(
                        "[send_ecommerce_weekly_report] Report emailed to %s", owner_email,
                    )
            except Exception as send_exc:
                logger.warning(
                    "[send_ecommerce_weekly_report] Email send failed: %s", send_exc,
                )

        # --- Send via WhatsApp ---
        if ESCALATION_WHATSAPP_TO:
            try:
                from tools.whatsapp_tools import send_whatsapp_report

                send_whatsapp_report(
                    to_phone=ESCALATION_WHATSAPP_TO,
                    report=report,
                    report_type="weekly",
                )
                logger.info(
                    "[send_ecommerce_weekly_report] WhatsApp report sent to %s",
                    ESCALATION_WHATSAPP_TO,
                )
            except Exception as wa_exc:
                logger.warning(
                    "[send_ecommerce_weekly_report] WhatsApp report failed: %s", wa_exc,
                )

        duration = time.monotonic() - start
        logger.info(
            "[send_ecommerce_weekly_report] DONE user=%s duration=%.1fs", user_id, duration,
        )

        return {
            "status": "success",
            "user_id": user_id,
            "report": report,
            "duration_s": round(duration, 2),
        }

    except Exception as exc:
        duration = time.monotonic() - start
        logger.exception(
            "[send_ecommerce_weekly_report] ERROR user=%s after %.1fs: %s",
            user_id, duration, exc,
        )

        return {
            "status": "error",
            "user_id": user_id,
            "duration_s": round(duration, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }
