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


@app.task(bind=True, name="scheduler.tasks.run_gmailmind_for_user", max_retries=3)
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
        # --- Step 0: Trial expiry check ---
        logger.info("[run_gmailmind_for_user] Step 0: Checking trial expiry for user=%s...", user_id)
        try:
            db = SessionLocal()
            try:
                row = db.execute(
                    text("""
                        SELECT u.tier, u.trial_end_date
                        FROM users u
                        WHERE u.id = :uid
                    """),
                    {"uid": user_id},
                ).fetchone()
                if row and row[0] == "trial" and row[1] is not None:
                    trial_end = row[1]
                    # Ensure timezone-aware comparison
                    if hasattr(trial_end, "tzinfo") and trial_end.tzinfo is None:
                        from datetime import timezone as tz
                        trial_end = trial_end.replace(tzinfo=tz.utc)
                    if datetime.now(timezone.utc) > trial_end:
                        logger.info(
                            "[run_gmailmind_for_user] Trial EXPIRED for user=%s (ended %s). Pausing agent.",
                            user_id, trial_end.isoformat(),
                        )
                        # Pause the agent
                        db.execute(
                            text("UPDATE user_agents SET is_paused = true WHERE user_id = :uid"),
                            {"uid": user_id},
                        )
                        db.commit()
                        _ensure_status_table()
                        _set_agent_status(user_id, "idle", error_msg="trial_expired")
                        duration = time.monotonic() - start
                        return {
                            "status": "trial_expired",
                            "user_id": user_id,
                            "started_at": started_at,
                            "duration_s": round(duration, 2),
                            "reason": "Trial period has ended. Upgrade to continue.",
                        }
            finally:
                db.close()
        except Exception as exc:
            logger.warning("[run_gmailmind_for_user] Trial check failed (non-fatal): %s", exc)

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

        # Update last_processed_at in user_agents
        try:
            db = SessionLocal()
            try:
                db.execute(
                    text("UPDATE user_agents SET last_processed_at = NOW() WHERE user_id = :uid"),
                    {"uid": user_id},
                )
                db.commit()
            finally:
                db.close()
        except Exception:
            pass
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
        retry_num = self.request.retries

        try:
            _set_agent_status(user_id, "error", error_msg=error_msg)
        except Exception:
            pass

        logger.error(
            "========== [run_gmailmind_for_user] TASK FAILED ==========\n"
            "  user_id  : %s\n"
            "  duration : %.1fs\n"
            "  attempt  : %d/3\n"
            "  error    : %s\n"
            "  traceback:\n%s",
            user_id, duration, retry_num + 1, error_msg, tb,
        )

        # Retry with exponential backoff: 60s, 180s, 300s
        if retry_num < self.max_retries:
            backoff = 60 * (retry_num + 1)
            logger.info(
                "[run_gmailmind_for_user] Retrying user=%s in %ds (attempt %d/%d)",
                user_id, backoff, retry_num + 1, self.max_retries,
            )
            raise self.retry(exc=exc, countdown=backoff)

        # After max retries: pause agent and log failure
        logger.error(
            "[run_gmailmind_for_user] All %d retries exhausted for user=%s — pausing agent.",
            self.max_retries, user_id,
        )
        try:
            db = SessionLocal()
            try:
                db.execute(
                    text("""
                        UPDATE user_agents
                        SET is_paused = true,
                            last_error = :err,
                            updated_at = NOW()
                        WHERE user_id = :uid
                    """),
                    {"uid": user_id, "err": f"Agent paused after {self.max_retries} failures: {error_msg}"},
                )
                db.commit()
            finally:
                db.close()
        except Exception:
            pass
        _set_agent_status(user_id, "error", error_msg=f"Paused after {self.max_retries} failures: {error_msg}")

        return {
            "status": "error",
            "user_id": user_id,
            "started_at": started_at,
            "duration_s": round(duration, 2),
            "error": error_msg,
            "traceback": tb,
            "retries_exhausted": True,
            "agent_paused": True,
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


# ============================================================================
# Task 8 — Renew Gmail Push Notification Watches
# ============================================================================


@app.task(bind=True, name="scheduler.tasks.renew_gmail_watches")
def renew_gmail_watches(self) -> dict[str, Any]:
    """Renew Gmail Pub/Sub watches for all active users.

    Gmail watches expire after ~7 days. This task runs daily and
    renews watches for any user whose watch will expire within 24 hours,
    or for users that don't have a watch_expiration set yet.

    Returns:
        A dict with ``status``, ``renewed`` count, and ``duration_s``.
    """
    start = time.monotonic()
    logger.info("[renew_gmail_watches] START")

    try:
        db = SessionLocal()
        try:
            # Get all active users with Gmail connected
            rows = db.execute(
                text("""
                    SELECT user_id, gmail_email, config
                    FROM user_agents
                    WHERE is_paused = false
                      AND gmail_email IS NOT NULL
                      AND gmail_email != ''
                """)
            ).fetchall()
        finally:
            db.close()

        if not rows:
            duration = time.monotonic() - start
            logger.info("[renew_gmail_watches] No active Gmail users found. duration=%.1fs", duration)
            return {"status": "success", "renewed": 0, "duration_s": round(duration, 2)}

        renewed = 0
        errors = 0
        now = datetime.now(timezone.utc)
        threshold = now + timedelta(hours=24)

        for row in rows:
            user_id = row[0]
            config = row[2] or {}

            # Check if watch needs renewal
            watch_exp_str = config.get("watch_expiration") if isinstance(config, dict) else None
            needs_renewal = True

            if watch_exp_str:
                try:
                    watch_exp = datetime.fromisoformat(watch_exp_str.replace("Z", "+00:00"))
                    if watch_exp > threshold:
                        needs_renewal = False
                except (ValueError, AttributeError):
                    pass  # Invalid date — renew

            if not needs_renewal:
                continue

            # Renew the watch
            try:
                from memory.long_term import get_user_credentials
                from config.credentials import refresh_credentials
                from config.settings import GOOGLE_PUBSUB_TOPIC

                creds_data = get_user_credentials(user_id)
                if not creds_data:
                    logger.warning("[renew_gmail_watches] No credentials for user=%s", user_id)
                    continue

                credentials = refresh_credentials(creds_data, user_id=user_id)
                if not credentials:
                    logger.warning("[renew_gmail_watches] Could not refresh credentials for user=%s", user_id)
                    continue

                from googleapiclient.discovery import build

                gmail_svc = build("gmail", "v1", credentials=credentials)
                watch_response = gmail_svc.users().watch(
                    userId="me",
                    body={
                        "topicName": GOOGLE_PUBSUB_TOPIC,
                        "labelIds": ["INBOX"],
                    },
                ).execute()

                # Save new expiration
                expiration_ms = int(watch_response.get("expiration", 0))
                if expiration_ms:
                    exp_dt = datetime.fromtimestamp(expiration_ms / 1000, tz=timezone.utc)
                    db2 = SessionLocal()
                    try:
                        db2.execute(
                            text("""
                                UPDATE user_agents
                                SET config = COALESCE(config, '{}'::jsonb)
                                    || jsonb_build_object('watch_expiration', :exp)
                                WHERE user_id = :uid
                            """),
                            {"exp": exp_dt.isoformat(), "uid": user_id},
                        )
                        db2.commit()
                    finally:
                        db2.close()

                renewed += 1
                logger.info("[renew_gmail_watches] Renewed watch for user=%s", user_id)

            except Exception as exc:
                errors += 1
                logger.error("[renew_gmail_watches] Failed for user=%s: %s", user_id, exc)

        duration = time.monotonic() - start
        logger.info(
            "[renew_gmail_watches] DONE renewed=%d errors=%d duration=%.1fs",
            renewed, errors, duration,
        )

        return {
            "status": "success",
            "renewed": renewed,
            "errors": errors,
            "total_users": len(rows),
            "duration_s": round(duration, 2),
        }

    except Exception as exc:
        duration = time.monotonic() - start
        logger.exception(
            "[renew_gmail_watches] ERROR after %.1fs: %s", duration, exc,
        )

        return {
            "status": "error",
            "duration_s": round(duration, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }


# ============================================================================
# Task 9 — Send Event Reminder Emails
# ============================================================================


@app.task(bind=True, name="scheduler.tasks.send_event_reminders")
def send_event_reminders(self) -> dict[str, Any]:
    """Send reminder emails for upcoming calendar events.

    Checks for interviews/events due within the next 24 hours and 1 hour,
    and sends appropriate reminder emails to attendees.

    Runs every 30 minutes via Celery Beat.

    Returns:
        Dict with status and count of reminders sent.
    """
    start = time.monotonic()
    logger.info("[send_event_reminders] START")

    reminders_sent = 0
    errors = 0

    try:
        from datetime import timedelta

        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            one_hour = now + timedelta(hours=1)
            twenty_four_hours = now + timedelta(hours=24)

            # Find interviews needing reminders:
            # 1) 24-hour reminder: due in 23.5-24.5 hours, not yet reminded_24h
            # 2) 1-hour reminder: due in 0.5-1.5 hours, not yet reminded_1h
            rows = db.execute(
                text("""
                    SELECT id, user_id, candidate_email, scheduled_at,
                           duration_minutes, interview_type, calendar_event_id,
                           COALESCE(notes, '') as notes
                    FROM interviews
                    WHERE status = 'scheduled'
                      AND scheduled_at > :now
                      AND (
                          (scheduled_at BETWEEN :t24_start AND :t24_end
                           AND (notes NOT LIKE '%%reminded_24h%%' OR notes IS NULL))
                          OR
                          (scheduled_at BETWEEN :t1_start AND :t1_end
                           AND (notes NOT LIKE '%%reminded_1h%%' OR notes IS NULL))
                      )
                    ORDER BY scheduled_at ASC
                """),
                {
                    "now": now,
                    "t24_start": twenty_four_hours - timedelta(minutes=30),
                    "t24_end": twenty_four_hours + timedelta(minutes=30),
                    "t1_start": one_hour - timedelta(minutes=30),
                    "t1_end": one_hour + timedelta(minutes=30),
                },
            ).fetchall()
        finally:
            db.close()

        if not rows:
            duration = time.monotonic() - start
            return {"status": "success", "reminders_sent": 0, "duration_s": round(duration, 2)}

        for row in rows:
            interview_id = row[0]
            user_id = row[1]
            candidate_email = row[2]
            scheduled_at = row[3]
            duration_min = row[4] or 45
            interview_type = row[5] or "video"
            calendar_event_id = row[6]
            notes = row[7] or ""

            # Determine which reminder to send
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
            time_until = (scheduled_at - now).total_seconds() / 3600  # hours

            if 0.5 <= time_until <= 1.5 and "reminded_1h" not in notes:
                reminder_type = "1h"
                subject = f"Reminder: Your interview is in 1 hour"
                body = (
                    f"This is a reminder that your {interview_type} interview "
                    f"is scheduled for {scheduled_at.strftime('%B %d at %H:%M UTC')}.\n\n"
                    f"Duration: {duration_min} minutes\n"
                )
            elif 23 <= time_until <= 25 and "reminded_24h" not in notes:
                reminder_type = "24h"
                subject = f"Reminder: Interview tomorrow"
                body = (
                    f"This is a reminder that your {interview_type} interview "
                    f"is scheduled for tomorrow, {scheduled_at.strftime('%B %d at %H:%M UTC')}.\n\n"
                    f"Duration: {duration_min} minutes\n"
                    f"Please make sure to prepare any necessary materials.\n"
                )
            else:
                continue

            # Send the reminder via Gmail
            try:
                from tools.calendar_tools import build_calendar_service
                from agent.tool_wrappers import standalone_reply_to_email

                # Build Gmail service for the user to send reminder
                from memory.long_term import get_user_credentials
                from config.credentials import refresh_credentials
                from googleapiclient.discovery import build

                creds_data = get_user_credentials(user_id)
                if creds_data:
                    credentials = refresh_credentials(creds_data, user_id=user_id)
                    if credentials:
                        gmail_svc = build("gmail", "v1", credentials=credentials)

                        # Create and send the reminder email
                        import base64
                        from email.mime.text import MIMEText

                        message = MIMEText(body)
                        message["to"] = candidate_email
                        message["subject"] = subject

                        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
                        gmail_svc.users().messages().send(
                            userId="me",
                            body={"raw": raw},
                        ).execute()

                        # Mark as reminded
                        db2 = SessionLocal()
                        try:
                            flag = f"reminded_{reminder_type}"
                            new_notes = f"{notes} {flag}".strip()
                            db2.execute(
                                text("UPDATE interviews SET notes = :notes WHERE id = :iid"),
                                {"notes": new_notes, "iid": interview_id},
                            )
                            db2.commit()
                        finally:
                            db2.close()

                        reminders_sent += 1
                        logger.info(
                            "[send_event_reminders] Sent %s reminder to %s for interview %d",
                            reminder_type, candidate_email, interview_id,
                        )

            except Exception as exc:
                errors += 1
                logger.error(
                    "[send_event_reminders] Failed for interview %d: %s",
                    interview_id, exc,
                )

        duration = time.monotonic() - start
        logger.info(
            "[send_event_reminders] DONE sent=%d errors=%d duration=%.1fs",
            reminders_sent, errors, duration,
        )

        return {
            "status": "success",
            "reminders_sent": reminders_sent,
            "errors": errors,
            "duration_s": round(duration, 2),
        }

    except Exception as exc:
        duration = time.monotonic() - start
        logger.exception(
            "[send_event_reminders] ERROR after %.1fs: %s", duration, exc,
        )
        return {
            "status": "error",
            "duration_s": round(duration, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }


# ============================================================================
# Weekly user summary email
# ============================================================================


@app.task(name="scheduler.tasks.send_weekly_user_summary")
def send_weekly_user_summary(scope: str = "default") -> dict[str, Any]:
    """Send a weekly summary email to each user every Monday morning.

    Includes: emails processed, new contacts, time saved, priority emails.
    """
    start = time.monotonic()
    logger.info("[send_weekly_user_summary] START scope=%s", scope)
    sent = 0
    errors = 0

    try:
        db = SessionLocal()
        try:
            # Get all active users with Gmail connected
            rows = db.execute(
                text("""
                    SELECT ua.user_id, ua.gmail_email
                    FROM user_agents ua
                    WHERE ua.status = 'active'
                      AND ua.gmail_email IS NOT NULL
                """)
            ).fetchall()

            for row in rows:
                user_id = row[0]
                gmail_email = row[1]

                try:
                    _send_one_weekly_summary(db, user_id, gmail_email)
                    sent += 1
                except Exception as exc:
                    errors += 1
                    logger.error(
                        "[send_weekly_user_summary] Failed for user %s: %s",
                        user_id, exc,
                    )
        finally:
            db.close()

        duration = time.monotonic() - start
        logger.info(
            "[send_weekly_user_summary] DONE sent=%d errors=%d duration=%.1fs",
            sent, errors, duration,
        )
        return {"status": "success", "sent": sent, "errors": errors, "duration_s": round(duration, 2)}

    except Exception as exc:
        duration = time.monotonic() - start
        logger.exception("[send_weekly_user_summary] ERROR: %s", exc)
        return {"status": "error", "error": str(exc), "duration_s": round(duration, 2)}


def _send_one_weekly_summary(db, user_id: str, gmail_email: str) -> None:
    """Build and send the weekly summary email for one user."""
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # Emails processed last week
    result = db.execute(
        text("""
            SELECT COUNT(*) FROM action_logs
            WHERE user_id = :uid AND timestamp >= :since
        """),
        {"uid": user_id, "since": week_ago},
    ).scalar() or 0
    emails_processed = int(result)

    # New contacts added
    new_contacts = int(db.execute(
        text("""
            SELECT COUNT(*) FROM contacts
            WHERE user_id = :uid AND created_at >= :since
        """),
        {"uid": user_id, "since": week_ago},
    ).scalar() or 0)

    # Time saved (3 min per email)
    time_saved_hours = round(emails_processed * 3 / 60, 1)

    # Priority emails needing attention (escalated, not yet handled)
    priority_rows = db.execute(
        text("""
            SELECT email_subject, timestamp FROM action_logs
            WHERE user_id = :uid
              AND action_type = 'escalated'
              AND timestamp >= :since
            ORDER BY timestamp DESC
            LIMIT 5
        """),
        {"uid": user_id, "since": week_ago},
    ).fetchall()

    priority_list = ""
    for pr in priority_rows:
        subj = pr[0] or "No subject"
        priority_list += f"  - {subj}\n"

    if not priority_list:
        priority_list = "  None — great job, your agent handled everything!\n"

    # Build email body
    body = (
        f"Hi there,\n\n"
        f"Here's your weekly HireAI summary for the past 7 days:\n\n"
        f"Emails Processed: {emails_processed}\n"
        f"New Contacts Added: {new_contacts}\n"
        f"Time Saved: ~{time_saved_hours} hours\n\n"
        f"Priority Emails Needing Attention:\n"
        f"{priority_list}\n"
        f"Keep it up! Your AI agent is working hard for you.\n\n"
        f"— HireAI Team\n"
    )

    # Send via Gmail API
    from memory.long_term import get_user_credentials
    from config.credentials import refresh_credentials
    from googleapiclient.discovery import build
    import base64
    from email.mime.text import MIMEText

    creds_data = get_user_credentials(user_id)
    if not creds_data:
        logger.warning("[weekly_summary] No credentials for user %s", user_id)
        return

    credentials = refresh_credentials(creds_data, user_id=user_id)
    if not credentials:
        logger.warning("[weekly_summary] Could not refresh creds for user %s", user_id)
        return

    gmail_svc = build("gmail", "v1", credentials=credentials)

    message = MIMEText(body)
    message["to"] = gmail_email
    message["subject"] = f"Your HireAI Weekly Summary — {emails_processed} emails handled"

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    gmail_svc.users().messages().send(
        userId="me",
        body={"raw": raw},
    ).execute()

    logger.info(
        "[weekly_summary] Sent to %s: %d emails, %d contacts, %.1fh saved",
        gmail_email, emails_processed, new_contacts, time_saved_hours,
    )
