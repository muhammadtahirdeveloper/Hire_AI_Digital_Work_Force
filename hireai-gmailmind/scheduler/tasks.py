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
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from config.database import SessionLocal
from scheduler.celery_app import app

logger = logging.getLogger(__name__)


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
    start = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()
    logger.info("[run_gmailmind_for_user] START user=%s at %s", user_id, started_at)

    _ensure_status_table()
    _set_agent_status(user_id, "running")

    try:
        from agent.reasoning_loop import get_daily_summary, run_agent_loop
        from config.business_config import load_business_config

        config = load_business_config(user_id=user_id)

        # run_agent_loop is async — run it in an event loop.
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                run_agent_loop(user_config=config, user_id=user_id, single_run=True)
            )
        finally:
            loop.close()

        duration = time.monotonic() - start
        summary_items = get_daily_summary()

        _set_agent_status(user_id, "idle")
        logger.info(
            "[run_gmailmind_for_user] DONE user=%s duration=%.1fs emails_processed=%d",
            user_id, duration, len(summary_items),
        )

        return {
            "status": "success",
            "user_id": user_id,
            "started_at": started_at,
            "duration_s": round(duration, 2),
            "emails_processed": len(summary_items),
        }

    except Exception as exc:
        duration = time.monotonic() - start
        error_msg = f"{type(exc).__name__}: {exc}"
        _set_agent_status(user_id, "error", error_msg=error_msg)
        logger.exception(
            "[run_gmailmind_for_user] ERROR user=%s after %.1fs: %s",
            user_id, duration, exc,
        )

        return {
            "status": "error",
            "user_id": user_id,
            "started_at": started_at,
            "duration_s": round(duration, 2),
            "error": error_msg,
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

    Collects all actions taken today from the database, builds a
    summary, and sends it via Gmail to the user's configured email.

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
        from memory.long_term import get_pending_follow_ups
        from memory.schemas import ActionLogRead

        config = load_business_config(user_id=user_id)
        owner_email = config.get("owner_email", "")

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
        report = {
            "date": today,
            "user_id": user_id,
            "total_actions": total_actions,
            "unique_senders": len(email_senders),
            "tools_breakdown": tools_used,
            "pending_followups": len(pending_followups),
        }

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

---
This report was generated automatically by GmailMind.
"""

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
