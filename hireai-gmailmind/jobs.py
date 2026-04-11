"""Background jobs for GmailMind — powered by APScheduler.

All periodic tasks that were previously Celery tasks are defined here
as plain functions. APScheduler calls them on schedule from api/main.py.

Tasks:
  1. run_gmailmind_all_users  — Dispatch agent loop for all active users.
  2. run_gmailmind_for_user   — Run one agent iteration for a single user.
  3. process_due_followups    — Trigger follow-ups whose due time has passed.
  4. send_daily_report        — End-of-day summary email.
  5. send_hr_weekly_report    — Weekly HR recruitment report.
  6. send_real_estate_weekly_report — Weekly Real Estate report.
  7. send_ecommerce_weekly_report  — Weekly E-commerce report.
  8. renew_gmail_watches      — Renew Gmail Pub/Sub watches.
  9. send_event_reminders     — Reminder emails for upcoming interviews.
 10. send_weekly_user_summary — Weekly per-user summary email.
"""

import asyncio
import logging
import time
import traceback
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from config.database import SessionLocal

logger = logging.getLogger(__name__)


# ============================================================================
# Agent status helpers
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
    try:
        db = SessionLocal()
        try:
            db.execute(text(_CREATE_STATUS_TABLE))
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.debug("Status table check skipped: %s", exc)


def _set_agent_status(user_id: str, status: str, error_msg: str = "") -> None:
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
# Job 0 — Dispatcher: fan out per-user tasks
# ============================================================================


def run_gmailmind_all_users() -> dict[str, Any]:
    """Query all active users and run the agent loop for each."""
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

        results = []
        for row in rows:
            uid = str(row[0])
            email = row[1] if len(row) > 1 else "unknown"
            logger.info("[run_gmailmind_all_users] Processing user=%s (%s)", uid, email)
            try:
                run_gmailmind_for_user(uid)
                results.append(uid)
            except Exception as exc:
                logger.error("[run_gmailmind_all_users] Failed for user=%s: %s", uid, exc)

        logger.info("=== DISPATCHER: processed %d users ===", len(results))
        return {"status": "dispatched", "dispatched": len(results), "user_ids": results}

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("=== DISPATCHER FAILED ===\n%s", tb)
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}


# ============================================================================
# Job 1 — Run agent loop for a single user
# ============================================================================


def run_gmailmind_for_user(user_id: str) -> dict[str, Any]:
    """Run one iteration of the GmailMind reasoning loop for a user."""
    start = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        "========== [run_gmailmind_for_user] STARTED user_id=%s at %s ==========",
        user_id, started_at,
    )

    try:
        # --- Trial expiry check ---
        try:
            db = SessionLocal()
            try:
                row = db.execute(
                    text("SELECT u.tier, u.trial_end_date FROM users u WHERE u.id = :uid"),
                    {"uid": user_id},
                ).fetchone()
                if row and row[0] == "trial" and row[1] is not None:
                    trial_end = row[1]
                    if hasattr(trial_end, "tzinfo") and trial_end.tzinfo is None:
                        trial_end = trial_end.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) > trial_end:
                        logger.info("[run_gmailmind_for_user] Trial EXPIRED for user=%s. Pausing.", user_id)
                        db.execute(
                            text("UPDATE user_agents SET is_paused = true WHERE user_id = :uid"),
                            {"uid": user_id},
                        )
                        db.commit()
                        _ensure_status_table()
                        _set_agent_status(user_id, "idle", error_msg="trial_expired")
                        return {"status": "trial_expired", "user_id": user_id}
            finally:
                db.close()
        except Exception as exc:
            logger.warning("[run_gmailmind_for_user] Trial check failed (non-fatal): %s", exc)

        # --- Ensure status table & set running ---
        _ensure_status_table()
        _set_agent_status(user_id, "running")

        # --- Orchestrator gate check ---
        try:
            from orchestrator.orchestrator import GmailMindOrchestrator
            orchestrator = GmailMindOrchestrator()
            routing = orchestrator.process_user(user_id)
        except Exception:
            logger.error("[run_gmailmind_for_user] Orchestrator error:\n%s", traceback.format_exc())
            raise

        if routing.get("status") == "skipped":
            _set_agent_status(user_id, "idle")
            return {"status": "skipped", "user_id": user_id, "reason": routing.get("reason", "unknown")}

        # --- Load credentials ---
        try:
            from memory.long_term import get_user_credentials
            creds = get_user_credentials(user_id)
            if creds:
                logger.info("[run_gmailmind_for_user] Gmail token loaded for user=%s", user_id)
            else:
                logger.warning("[run_gmailmind_for_user] No credentials for user=%s", user_id)
        except Exception:
            logger.error("[run_gmailmind_for_user] Credential check error:\n%s", traceback.format_exc())

        # --- Create EmailProcessor and process inbox ---
        from agent.email_processor import EmailProcessor
        processor = EmailProcessor(user_id)

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(processor.process_inbox())
        finally:
            loop.close()

        emails_processed = result.get("processed", 0)

        # --- Finalize ---
        duration = time.monotonic() - start
        _set_agent_status(user_id, "idle")

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
            "========== [run_gmailmind_for_user] COMPLETED user=%s duration=%.1fs emails=%d ==========",
            user_id, duration, emails_processed,
        )
        return {
            "status": "success",
            "user_id": user_id,
            "duration_s": round(duration, 2),
            "emails_processed": emails_processed,
        }

    except Exception as exc:
        duration = time.monotonic() - start
        error_msg = f"{type(exc).__name__}: {exc}"
        try:
            _set_agent_status(user_id, "error", error_msg=error_msg)
        except Exception:
            pass
        logger.error(
            "========== [run_gmailmind_for_user] FAILED user=%s duration=%.1fs error=%s ==========",
            user_id, duration, error_msg,
        )
        return {"status": "error", "user_id": user_id, "error": error_msg}


# ============================================================================
# Job 2 — Process due follow-ups
# ============================================================================


def process_due_followups() -> dict[str, Any]:
    """Check for follow-ups that are due and trigger the agent to act."""
    start = time.monotonic()
    logger.info("[process_due_followups] START")

    try:
        from agent.gmailmind import create_agent
        from agent.reasoning_loop import _process_due_followup
        from config.business_config import load_business_config
        from memory.long_term import get_pending_follow_ups

        now = datetime.now(timezone.utc)
        pending = get_pending_follow_ups()
        due = [fu for fu in pending if fu.due_time <= now]

        if not due:
            return {"status": "success", "processed": 0, "duration_s": round(time.monotonic() - start, 2)}

        config = load_business_config()
        agent = create_agent(config)

        loop = asyncio.new_event_loop()
        processed = 0
        try:
            for followup in due:
                try:
                    fu_dict = followup.model_dump(mode="json")
                    loop.run_until_complete(_process_due_followup(agent, fu_dict, config))
                    processed += 1
                except Exception as exc:
                    logger.error("[process_due_followups] Failed for id=%s: %s", followup.id, exc)
        finally:
            loop.close()

        duration = time.monotonic() - start
        logger.info("[process_due_followups] DONE processed=%d/%d duration=%.1fs", processed, len(due), duration)
        return {"status": "success", "processed": processed, "total_due": len(due), "duration_s": round(duration, 2)}

    except Exception as exc:
        duration = time.monotonic() - start
        logger.exception("[process_due_followups] ERROR after %.1fs: %s", duration, exc)
        return {"status": "error", "duration_s": round(duration, 2), "error": str(exc)}


# ============================================================================
# Job 3 — Send daily summary report
# ============================================================================


def send_daily_report(user_id: str = "default") -> dict[str, Any]:
    """Generate and email the end-of-day summary report."""
    start = time.monotonic()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    logger.info("[send_daily_report] START user=%s date=%s", user_id, today)

    try:
        from config.business_config import load_business_config
        from config.settings import ESCALATION_WHATSAPP_TO
        from memory.long_term import get_pending_follow_ups

        config = load_business_config(user_id=user_id)
        owner_email = config.get("owner_email", "")

        user_tier = "tier2"
        user_industry = "general"
        try:
            from orchestrator.feature_gates import FeatureGate
            from orchestrator.user_router import UserRouter
            user_tier = FeatureGate().get_user_tier(user_id)
            user_industry = UserRouter().get_user_industry(user_id)
        except Exception:
            pass

        db = SessionLocal()
        try:
            from models.schemas import ActionLog
            from sqlalchemy import select

            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            stmt = select(ActionLog).where(ActionLog.timestamp >= today_start).order_by(ActionLog.timestamp.asc())
            rows = db.execute(stmt).scalars().all()

            total_actions = len(rows)
            tools_used: dict[str, int] = {}
            email_senders: set[str] = set()
            for row in rows:
                tools_used[row.tool_used] = tools_used.get(row.tool_used, 0) + 1
                email_senders.add(row.email_from)

            pending_followups = get_pending_follow_ups(db=db)
        finally:
            db.close()

        report: dict[str, Any] = {
            "date": today,
            "user_id": user_id,
            "total_actions": total_actions,
            "unique_senders": len(email_senders),
            "tools_breakdown": tools_used,
            "pending_followups": len(pending_followups),
        }

        if user_industry == "hr":
            try:
                from agent.report_generator import ReportGenerator
                rg = ReportGenerator()
                report["hr_data"] = rg.generate_hr_daily_summary(user_id, today)
            except Exception as hr_exc:
                logger.warning("[send_daily_report] HR metrics failed: %s", hr_exc)

        tool_lines = "\n".join(f"    - {t}: {c}" for t, c in tools_used.items()) or "    (no actions today)"
        email_body = (
            f"GmailMind Daily Summary — {today}\n{'=' * 50}\n\n"
            f"Total Actions Taken:   {total_actions}\n"
            f"Unique Senders:        {len(email_senders)}\n"
            f"Pending Follow-ups:    {len(pending_followups)}\n\n"
            f"Tools Used:\n{tool_lines}\n"
        )

        if report.get("hr_data"):
            hr = report["hr_data"]
            email_body += (
                f"\nHR Recruitment Summary:\n"
                f"    New CVs:              {hr.get('new_candidates', 0)}\n"
                f"    Interviews Scheduled: {hr.get('interviews_scheduled', 0)}\n"
            )

        email_body += "\n---\nThis report was generated automatically by GmailMind.\n"

        if owner_email:
            try:
                from agent.tool_wrappers import services
                from tools.gmail_tools import send_email as gmail_send
                gmail_svc = services.get("gmail")
                if gmail_svc:
                    gmail_send(gmail_svc, to=owner_email, subject=f"GmailMind Daily Report — {today}", body=email_body)
            except Exception as send_exc:
                logger.warning("[send_daily_report] Email send failed: %s", send_exc)

        if user_tier in ("tier2", "tier3") and ESCALATION_WHATSAPP_TO:
            try:
                from tools.whatsapp_tools import send_whatsapp_report
                send_whatsapp_report(to_phone=ESCALATION_WHATSAPP_TO, report=report, report_type="daily")
            except Exception as wa_exc:
                logger.warning("[send_daily_report] WhatsApp failed: %s", wa_exc)

        try:
            from agent.reasoning_loop import reset_daily_summary
            reset_daily_summary()
        except Exception:
            pass

        duration = time.monotonic() - start
        logger.info("[send_daily_report] DONE user=%s actions=%d duration=%.1fs", user_id, total_actions, duration)
        return {"status": "success", "report": report, "duration_s": round(duration, 2)}

    except Exception as exc:
        duration = time.monotonic() - start
        logger.exception("[send_daily_report] ERROR: %s", exc)
        return {"status": "error", "duration_s": round(duration, 2), "error": str(exc)}


# ============================================================================
# Job 4 — Weekly HR recruitment report
# ============================================================================


def send_hr_weekly_report(user_id: str = "default") -> dict[str, Any]:
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

        if owner_email:
            try:
                from agent.tool_wrappers import services
                from tools.gmail_tools import send_email as gmail_send
                gmail_svc = services.get("gmail")
                if gmail_svc:
                    gmail_send(gmail_svc, to=owner_email, subject=f"GmailMind HR Weekly Report", body=whatsapp_text)
            except Exception as send_exc:
                logger.warning("[send_hr_weekly_report] Email failed: %s", send_exc)

        if ESCALATION_WHATSAPP_TO:
            try:
                from tools.whatsapp_tools import send_whatsapp_report
                send_whatsapp_report(to_phone=ESCALATION_WHATSAPP_TO, report=report, report_type="weekly")
            except Exception as wa_exc:
                logger.warning("[send_hr_weekly_report] WhatsApp failed: %s", wa_exc)

        duration = time.monotonic() - start
        return {"status": "success", "report": report, "duration_s": round(duration, 2)}
    except Exception as exc:
        duration = time.monotonic() - start
        logger.exception("[send_hr_weekly_report] ERROR: %s", exc)
        return {"status": "error", "duration_s": round(duration, 2), "error": str(exc)}


# ============================================================================
# Job 5 — Weekly Real Estate report
# ============================================================================


def send_real_estate_weekly_report(user_id: str = "default") -> dict[str, Any]:
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

        if owner_email:
            try:
                from agent.tool_wrappers import services
                from tools.gmail_tools import send_email as gmail_send
                gmail_svc = services.get("gmail")
                if gmail_svc:
                    gmail_send(gmail_svc, to=owner_email, subject="GmailMind Real Estate Weekly Report", body=whatsapp_text)
            except Exception as send_exc:
                logger.warning("[send_real_estate_weekly_report] Email failed: %s", send_exc)

        if ESCALATION_WHATSAPP_TO:
            try:
                from tools.whatsapp_tools import send_whatsapp_report
                send_whatsapp_report(to_phone=ESCALATION_WHATSAPP_TO, report=report, report_type="weekly")
            except Exception as wa_exc:
                logger.warning("[send_real_estate_weekly_report] WhatsApp failed: %s", wa_exc)

        duration = time.monotonic() - start
        return {"status": "success", "report": report, "duration_s": round(duration, 2)}
    except Exception as exc:
        duration = time.monotonic() - start
        logger.exception("[send_real_estate_weekly_report] ERROR: %s", exc)
        return {"status": "error", "duration_s": round(duration, 2), "error": str(exc)}


# ============================================================================
# Job 6 — Weekly E-commerce report
# ============================================================================


def send_ecommerce_weekly_report(user_id: str = "default") -> dict[str, Any]:
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

        if owner_email:
            try:
                from agent.tool_wrappers import services
                from tools.gmail_tools import send_email as gmail_send
                gmail_svc = services.get("gmail")
                if gmail_svc:
                    gmail_send(gmail_svc, to=owner_email, subject="GmailMind E-commerce Weekly Report", body=whatsapp_text)
            except Exception as send_exc:
                logger.warning("[send_ecommerce_weekly_report] Email failed: %s", send_exc)

        if ESCALATION_WHATSAPP_TO:
            try:
                from tools.whatsapp_tools import send_whatsapp_report
                send_whatsapp_report(to_phone=ESCALATION_WHATSAPP_TO, report=report, report_type="weekly")
            except Exception as wa_exc:
                logger.warning("[send_ecommerce_weekly_report] WhatsApp failed: %s", wa_exc)

        duration = time.monotonic() - start
        return {"status": "success", "report": report, "duration_s": round(duration, 2)}
    except Exception as exc:
        duration = time.monotonic() - start
        logger.exception("[send_ecommerce_weekly_report] ERROR: %s", exc)
        return {"status": "error", "duration_s": round(duration, 2), "error": str(exc)}


# ============================================================================
# Job 7 — Renew Gmail push notification watches
# ============================================================================


def renew_gmail_watches() -> dict[str, Any]:
    """Renew Gmail Pub/Sub watches for all active users."""
    start = time.monotonic()
    logger.info("[renew_gmail_watches] START")

    try:
        db = SessionLocal()
        try:
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
            return {"status": "success", "renewed": 0, "duration_s": round(time.monotonic() - start, 2)}

        renewed = 0
        errors = 0
        now = datetime.now(timezone.utc)
        threshold = now + timedelta(hours=24)

        for row in rows:
            user_id = row[0]
            config = row[2] or {}

            watch_exp_str = config.get("watch_expiration") if isinstance(config, dict) else None
            needs_renewal = True

            if watch_exp_str:
                try:
                    watch_exp = datetime.fromisoformat(watch_exp_str.replace("Z", "+00:00"))
                    if watch_exp > threshold:
                        needs_renewal = False
                except (ValueError, AttributeError):
                    pass

            if not needs_renewal:
                continue

            try:
                from memory.long_term import get_user_credentials
                from config.credentials import refresh_credentials
                from config.settings import GOOGLE_PUBSUB_TOPIC

                creds_data = get_user_credentials(user_id)
                if not creds_data:
                    continue

                credentials = refresh_credentials(creds_data, user_id=user_id)
                if not credentials:
                    continue

                from googleapiclient.discovery import build
                gmail_svc = build("gmail", "v1", credentials=credentials)
                watch_response = gmail_svc.users().watch(
                    userId="me",
                    body={"topicName": GOOGLE_PUBSUB_TOPIC, "labelIds": ["INBOX"]},
                ).execute()

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
                logger.info("[renew_gmail_watches] Renewed for user=%s", user_id)

            except Exception as exc:
                errors += 1
                logger.error("[renew_gmail_watches] Failed for user=%s: %s", user_id, exc)

        duration = time.monotonic() - start
        logger.info("[renew_gmail_watches] DONE renewed=%d errors=%d duration=%.1fs", renewed, errors, duration)
        return {"status": "success", "renewed": renewed, "errors": errors, "duration_s": round(duration, 2)}

    except Exception as exc:
        duration = time.monotonic() - start
        logger.exception("[renew_gmail_watches] ERROR: %s", exc)
        return {"status": "error", "duration_s": round(duration, 2), "error": str(exc)}


# ============================================================================
# Job 8 — Send event reminder emails
# ============================================================================


def send_event_reminders() -> dict[str, Any]:
    """Send reminder emails for upcoming interviews/events."""
    start = time.monotonic()
    logger.info("[send_event_reminders] START")

    reminders_sent = 0
    errors = 0

    try:
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            one_hour = now + timedelta(hours=1)
            twenty_four_hours = now + timedelta(hours=24)

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
            return {"status": "success", "reminders_sent": 0, "duration_s": round(time.monotonic() - start, 2)}

        for row in rows:
            interview_id = row[0]
            user_id = row[1]
            candidate_email = row[2]
            scheduled_at = row[3]
            duration_min = row[4] or 45
            interview_type = row[5] or "video"
            notes = row[7] or ""

            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
            time_until = (scheduled_at - now).total_seconds() / 3600

            if 0.5 <= time_until <= 1.5 and "reminded_1h" not in notes:
                reminder_type = "1h"
                subject = "Reminder: Your interview is in 1 hour"
                body = (
                    f"This is a reminder that your {interview_type} interview "
                    f"is scheduled for {scheduled_at.strftime('%B %d at %H:%M UTC')}.\n\n"
                    f"Duration: {duration_min} minutes\n"
                )
            elif 23 <= time_until <= 25 and "reminded_24h" not in notes:
                reminder_type = "24h"
                subject = "Reminder: Interview tomorrow"
                body = (
                    f"This is a reminder that your {interview_type} interview "
                    f"is scheduled for tomorrow, {scheduled_at.strftime('%B %d at %H:%M UTC')}.\n\n"
                    f"Duration: {duration_min} minutes\n"
                )
            else:
                continue

            try:
                from memory.long_term import get_user_credentials
                from config.credentials import refresh_credentials
                from googleapiclient.discovery import build
                import base64
                from email.mime.text import MIMEText

                creds_data = get_user_credentials(user_id)
                if not creds_data:
                    continue
                credentials = refresh_credentials(creds_data, user_id=user_id)
                if not credentials:
                    continue

                gmail_svc = build("gmail", "v1", credentials=credentials)
                message = MIMEText(body)
                message["to"] = candidate_email
                message["subject"] = subject
                raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
                gmail_svc.users().messages().send(userId="me", body={"raw": raw}).execute()

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
                logger.info("[send_event_reminders] Sent %s reminder to %s", reminder_type, candidate_email)

            except Exception as exc:
                errors += 1
                logger.error("[send_event_reminders] Failed for interview %d: %s", interview_id, exc)

        duration = time.monotonic() - start
        return {"status": "success", "reminders_sent": reminders_sent, "errors": errors, "duration_s": round(duration, 2)}

    except Exception as exc:
        duration = time.monotonic() - start
        logger.exception("[send_event_reminders] ERROR: %s", exc)
        return {"status": "error", "duration_s": round(duration, 2), "error": str(exc)}


# ============================================================================
# Job 9 — Weekly user summary email
# ============================================================================


def send_weekly_user_summary(scope: str = "default") -> dict[str, Any]:
    """Send weekly summary email to each user."""
    start = time.monotonic()
    logger.info("[send_weekly_user_summary] START scope=%s", scope)
    sent = 0
    errors = 0

    try:
        db = SessionLocal()
        try:
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
                    logger.error("[send_weekly_user_summary] Failed for user %s: %s", user_id, exc)
        finally:
            db.close()

        duration = time.monotonic() - start
        return {"status": "success", "sent": sent, "errors": errors, "duration_s": round(duration, 2)}

    except Exception as exc:
        duration = time.monotonic() - start
        logger.exception("[send_weekly_user_summary] ERROR: %s", exc)
        return {"status": "error", "error": str(exc), "duration_s": round(duration, 2)}


def _send_one_weekly_summary(db, user_id: str, gmail_email: str) -> None:
    """Build and send the weekly summary email for one user."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    emails_processed = int(db.execute(
        text("SELECT COUNT(*) FROM action_logs WHERE user_id = :uid AND timestamp >= :since"),
        {"uid": user_id, "since": week_ago},
    ).scalar() or 0)

    new_contacts = int(db.execute(
        text("SELECT COUNT(*) FROM contacts WHERE user_id = :uid AND created_at >= :since"),
        {"uid": user_id, "since": week_ago},
    ).scalar() or 0)

    time_saved_hours = round(emails_processed * 3 / 60, 1)

    priority_rows = db.execute(
        text("""
            SELECT email_subject, timestamp FROM action_logs
            WHERE user_id = :uid AND action_type = 'escalated' AND timestamp >= :since
            ORDER BY timestamp DESC LIMIT 5
        """),
        {"uid": user_id, "since": week_ago},
    ).fetchall()

    priority_list = ""
    for pr in priority_rows:
        subj = pr[0] or "No subject"
        priority_list += f"  - {subj}\n"
    if not priority_list:
        priority_list = "  None — great job, your agent handled everything!\n"

    body = (
        f"Hi there,\n\n"
        f"Here's your weekly HireAI summary for the past 7 days:\n\n"
        f"Emails Processed: {emails_processed}\n"
        f"New Contacts Added: {new_contacts}\n"
        f"Time Saved: ~{time_saved_hours} hours\n\n"
        f"Priority Emails Needing Attention:\n{priority_list}\n"
        f"Keep it up! Your AI agent is working hard for you.\n\n"
        f"— HireAI Team\n"
    )

    from memory.long_term import get_user_credentials
    from config.credentials import refresh_credentials
    from googleapiclient.discovery import build
    import base64
    from email.mime.text import MIMEText

    creds_data = get_user_credentials(user_id)
    if not creds_data:
        return
    credentials = refresh_credentials(creds_data, user_id=user_id)
    if not credentials:
        return

    gmail_svc = build("gmail", "v1", credentials=credentials)
    message = MIMEText(body)
    message["to"] = gmail_email
    message["subject"] = f"Your HireAI Weekly Summary — {emails_processed} emails handled"
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    gmail_svc.users().messages().send(userId="me", body={"raw": raw}).execute()

    logger.info("[weekly_summary] Sent to %s: %d emails, %d contacts", gmail_email, emails_processed, new_contacts)


# ============================================================================
# Helper: run a job in a background thread (fire-and-forget)
# ============================================================================


def run_in_background(func, *args, **kwargs) -> None:
    """Run a job function in a background thread (non-blocking)."""
    import threading
    thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
    thread.start()
