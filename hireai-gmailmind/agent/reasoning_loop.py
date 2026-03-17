"""GmailMind Reasoning Loop — Observe → Think → Act → Remember → Report.

This module implements the core autonomous loop that:
  1. **Observes** — fetches new unread emails + pending follow-ups.
  2. **Thinks** — runs the GmailMind agent with full memory context per email.
  3. **Remembers** — updates long-term memory after each decision.
  4. **Reports** — appends each action to the daily summary.
  5. **Sleeps** — waits until the next polling interval.

Usage::

    import asyncio
    from agent.reasoning_loop import run_agent_loop

    asyncio.run(run_agent_loop(user_config))
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from agent.safety_guard import SafetyViolationError, safety_guard
from agent.tool_wrappers import set_services
from config.business_config import load_business_config
from config.credentials import build_credentials, refresh_credentials
from config.database import SessionLocal
from config.settings import ENCRYPTION_KEY, POLL_INTERVAL_SECONDS
from memory.long_term import (
    create_follow_up,
    get_actions_for_sender,
    get_pending_follow_ups,
    get_sender_memory,
    get_user_credentials,
    log_action as persist_action,
    save_user_credentials,
    update_sender_memory,
)
from memory.schemas import ActionLogCreate, SenderProfileUpdate
from memory.short_term import session_memory

logger = logging.getLogger(__name__)


# ============================================================================
# Service initialisation helpers
# ============================================================================


def _load_token_from_db(user_id: str) -> dict[str, Any]:
    """Read and decrypt OAuth token from the user_credentials table.

    Uses the new get_user_credentials function with EncryptionManager
    for consistent encryption handling across the app.

    Args:
        user_id: The user ID to look up.

    Returns:
        Decrypted token data dict.

    Raises:
        RuntimeError: If no credentials are found for the user.
    """
    credentials = get_user_credentials(user_id)

    if not credentials:
        raise RuntimeError(
            f"No OAuth token found in database for user '{user_id}'. "
            "Run the OAuth setup flow first: visit /auth/google"
        )

    return credentials


def _build_credentials_from_db(user_id: str):
    """Build Google OAuth2 Credentials from database-stored token.

    Loads token data from the DB, builds a Credentials object with the
    stored expiry so that ``credentials.expired`` works correctly, refreshes
    the token when expired, and **persists the refreshed token back** to the
    database so subsequent runs start with a valid access token.

    Args:
        user_id: The user ID whose credentials to load.

    Returns:
        A refreshed google.oauth2.credentials.Credentials instance.
    """
    token_data = _load_token_from_db(user_id)

    # Parse stored expiry string into a datetime
    expiry = None
    expiry_raw = token_data.get("expiry")
    if expiry_raw:
        try:
            expiry = datetime.fromisoformat(str(expiry_raw))
        except (ValueError, TypeError):
            logger.warning("Could not parse expiry '%s', treating as expired.", expiry_raw)

    creds = build_credentials(
        token=token_data.get("token", ""),
        refresh_token=token_data.get("refresh_token", ""),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        expiry=expiry,
    )

    # Force refresh if the token looks expired even when the library can't tell
    needs_refresh = creds.expired or (
        expiry is not None
        and expiry.replace(tzinfo=timezone.utc)
        <= datetime.now(timezone.utc)
    )

    if needs_refresh and creds.refresh_token:
        logger.info("Token expired for user=%s, refreshing...", user_id)
        creds = refresh_credentials(creds)

        # Persist the refreshed token back to the DB
        updated_token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token or token_data.get("refresh_token", ""),
            "token_uri": creds.token_uri or token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            "client_id": creds.client_id or token_data.get("client_id", ""),
            "client_secret": creds.client_secret or token_data.get("client_secret", ""),
            "scopes": list(creds.scopes or token_data.get("scopes", [])),
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        }
        try:
            save_user_credentials(user_id, updated_token_data)
            logger.info("Refreshed token saved to DB for user=%s", user_id)
        except Exception as exc:
            logger.error("Failed to save refreshed token for user=%s: %s", user_id, exc)
    elif not creds.refresh_token:
        logger.warning("No refresh_token available for user=%s, cannot auto-refresh.", user_id)

    return creds


def _build_gmail_service(user_config: dict[str, Any], user_id: str = "default") -> Any:
    """Build an authenticated Gmail API service from database credentials.

    Args:
        user_config: Business config (kept for interface compatibility).
        user_id: User ID to look up credentials in user_credentials table.

    Returns:
        An authenticated Gmail API ``Resource`` object.

    Raises:
        RuntimeError: If credentials are missing or invalid.
    """
    from googleapiclient.discovery import build as google_build

    creds = _build_credentials_from_db(user_id)
    service = google_build("gmail", "v1", credentials=creds)
    logger.info("Gmail service built successfully (user_id=%s).", user_id)
    return service


def _build_calendar_service(user_config: dict[str, Any], user_id: str = "default") -> Optional[Any]:
    """Build an authenticated Google Calendar service (optional).

    Reads credentials from the database. Returns None if not available.
    """
    try:
        from googleapiclient.discovery import build as google_build

        creds = _build_credentials_from_db(user_id)
        service = google_build("calendar", "v3", credentials=creds)
        logger.info("Calendar service built successfully (user_id=%s).", user_id)
        return service
    except Exception as exc:
        logger.warning("Calendar service not available: %s", exc)
        return None


# ============================================================================
# Email fetching
# ============================================================================


def _fetch_new_emails(gmail_service: Any, max_results: int = 20) -> list[dict[str, Any]]:
    """Fetch unread emails from the Gmail inbox.

    Args:
        gmail_service: Authenticated Gmail API Resource.
        max_results: Maximum number of emails to fetch.

    Returns:
        List of email dicts parsed from the Gmail API.
    """
    from tools.gmail_tools import read_emails

    emails = read_emails(gmail_service, max_results=max_results, filter="is:unread")
    logger.info("Fetched %d unread emails.", len(emails))
    return [e.model_dump(mode="json") for e in emails]


def _fetch_due_followups() -> list[dict[str, Any]]:
    """Fetch follow-ups that are now due.

    Returns:
        List of follow-up dicts where due_time <= now and status is pending.
    """
    now = datetime.now(timezone.utc)
    pending = get_pending_follow_ups()

    due = []
    for fu in pending:
        if fu.due_time <= now:
            due.append(fu.model_dump(mode="json"))

    logger.info("Found %d due follow-ups (out of %d pending).", len(due), len(pending))
    return due


# ============================================================================
# Memory context assembly
# ============================================================================


def _get_sender_context(sender_email: str) -> dict[str, Any] | None:
    """Load long-term memory for a sender.

    Args:
        sender_email: The sender's email address.

    Returns:
        Sender profile dict or None if not found.
    """
    profile = get_sender_memory(sender_email)
    if profile is None:
        return None
    return profile.model_dump(mode="json")


def _get_sender_followups(sender_email: str) -> list[dict[str, Any]]:
    """Get pending follow-ups for a specific sender.

    Args:
        sender_email: The sender's email address.

    Returns:
        List of pending follow-up dicts for this sender.
    """
    now = datetime.now(timezone.utc)
    all_pending = get_pending_follow_ups()
    return [
        fu.model_dump(mode="json")
        for fu in all_pending
        if fu.sender == sender_email
    ]


# ============================================================================
# Post-action memory update
# ============================================================================


# ============================================================================
# Daily summary tracking
# ============================================================================

# In-memory accumulator for the current run's daily summary.
_daily_summary: list[dict[str, Any]] = []


def _append_to_daily_summary(
    email_data: dict[str, Any],
    agent_output: str,
) -> None:
    """Append a processed-email record to the daily summary.

    Args:
        email_data: The email dict.
        agent_output: The agent's summary output.
    """
    _daily_summary.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "email_id": email_data.get("id", ""),
        "sender": (
            email_data.get("sender", {}).get("email", "")
            if isinstance(email_data.get("sender"), dict)
            else str(email_data.get("sender", ""))
        ),
        "subject": email_data.get("subject", ""),
        "agent_summary": agent_output[:500],
    })


def get_daily_summary() -> list[dict[str, Any]]:
    """Return the accumulated daily summary records.

    Returns:
        List of processed-email summary dicts.
    """
    return list(_daily_summary)


def reset_daily_summary() -> None:
    """Clear the daily summary for a new day."""
    _daily_summary.clear()


# ============================================================================
# Core agent execution
# ============================================================================


async def _process_single_email(
    agent: Any,
    email_data: dict[str, Any],
    user_config: dict[str, Any],
    user_id: str = "default",
    gmail_service: Any = None,
) -> dict[str, Any]:
    """Run the agent against a single email using the AI Router.

    Args:
        agent: A BaseAgent subclass instance (with ai_router).
        email_data: The email dict to process.
        user_config: The business configuration.
        user_id: The user ID (passed to AI Router for tier/provider lookup).
        gmail_service: Gmail API service for executing actions.

    Returns:
        Dict with action result and metadata.
    """
    # Extract sender email
    sender = email_data.get("sender", {})
    sender_email = (
        sender.get("email", "unknown")
        if isinstance(sender, dict)
        else str(sender)
    )

    # Track in short-term memory
    session_memory.add_email(email_data.get("id", ""), {
        "sender": sender_email,
        "subject": email_data.get("subject", ""),
        "snippet": email_data.get("snippet", ""),
    })

    logger.info(
        "Processing email %s from %s: %s",
        email_data.get("id", "?"),
        sender_email,
        email_data.get("subject", "(no subject)"),
    )

    try:
        # Use AI Router through agent.process_email
        decision = await agent.process_email(user_id, email_data)

        logger.info(
            "AI decision for email %s: action=%s provider=%s model=%s",
            email_data.get("id", "?"),
            decision.get("action", "?"),
            decision.get("provider", "?"),
            decision.get("model", "?"),
        )

        # Execute the action
        action_result = await _execute_action(
            gmail_service, email_data, decision, user_config,
        )

        # Log to database
        _log_action(user_id, email_data, decision, action_result)

        # Update sender memory
        _update_sender_memory(sender_email, email_data, decision)

        # Append to daily summary
        agent_output = decision.get("ai_response", "")
        _append_to_daily_summary(email_data, agent_output)

        return {
            "email_from": sender_email,
            "action": decision.get("action", "DRAFT_REPLY"),
            "provider": decision.get("provider", "unknown"),
            "status": action_result.get("status", "processed"),
        }

    except SafetyViolationError as exc:
        logger.warning("Safety violation for email %s: %s", email_data.get("id", "?"), exc)
        session_memory.add_escalation(
            email_data.get("id", ""),
            reason=str(exc),
            sender=sender_email,
        )
        return {"email_from": sender_email, "action": "BLOCKED", "error": str(exc)}

    except Exception as exc:
        logger.exception("Error processing email %s.", email_data.get("id", "?"))
        return {"email_from": sender_email, "error": str(exc)}


async def _process_due_followup(
    agent: Any,
    followup: dict[str, Any],
    user_config: dict[str, Any],
    user_id: str = "default",
) -> dict[str, Any]:
    """Handle a follow-up that has come due using the AI Router.

    Args:
        agent: A BaseAgent subclass instance.
        followup: The follow-up dict (email_id, sender, note, due_time).
        user_config: The business configuration.
        user_id: The user ID.

    Returns:
        Dict with action result.
    """
    sender_email = followup.get("sender", "")
    email_id = followup.get("email_id", "")
    note = followup.get("note", "")

    # Build a synthetic email dict for the agent
    followup_email = {
        "id": email_id,
        "subject": f"Follow-up due: {note[:80]}",
        "body": (
            f"A scheduled follow-up is now due.\n"
            f"Original email ID: {email_id}\n"
            f"Sender: {sender_email}\n"
            f"Note: {note}\n"
            f"Due: {followup.get('due_time', 'now')}"
        ),
        "sender": {"email": sender_email, "name": sender_email},
    }

    try:
        decision = await agent.process_email(user_id, followup_email)
        agent_output = decision.get("ai_response", "")
    except Exception as exc:
        agent_output = f"[ERROR] Follow-up processing failed: {exc}"
        logger.exception("Error processing follow-up for %s.", email_id)

    # Mark the follow-up as completed
    from memory.long_term import update_follow_up
    from memory.schemas import FollowUpUpdate

    followup_id = followup.get("id")
    if followup_id:
        update_follow_up(
            follow_up_id=followup_id,
            data=FollowUpUpdate(status="completed"),
        )

    return {"email_id": email_id, "sender": sender_email, "output": agent_output}


# ============================================================================
# Action execution
# ============================================================================


def _extract_reply(ai_response: str) -> str:
    """Extract reply text from AI response.

    Looks for 'REPLY: ...' in the AI output. Falls back to the full
    response if no REPLY line is found.

    Args:
        ai_response: Raw AI response text.

    Returns:
        The reply text string.
    """
    match = re.search(r"REPLY:\s*(.+?)(?:\nREASON:|\Z)", ai_response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ai_response.strip()


async def _execute_action(
    gmail_service: Any,
    email_data: dict[str, Any],
    decision: dict[str, Any],
    user_config: dict[str, Any],
) -> dict[str, str]:
    """Execute the AI's decision (reply, draft, label, etc.).

    Args:
        gmail_service: Authenticated Gmail API service.
        email_data: The original email dict.
        decision: The AI decision dict with 'action' and 'ai_response'.
        user_config: Business configuration.

    Returns:
        Dict with status and action taken.
    """
    action = decision.get("action", "DRAFT_REPLY")
    ai_response = decision.get("ai_response", "")

    if action == "AUTO_REPLY":
        reply_text = _extract_reply(ai_response)
        auto_reply_enabled = (
            user_config.get("autonomy", {}).get("auto_reply_known_contacts", False)
        )
        if reply_text and auto_reply_enabled and gmail_service:
            try:
                from tools.gmail_tools import send_reply
                send_reply(gmail_service, email_data, reply_text)
                return {"status": "sent", "action": "auto_replied"}
            except Exception as exc:
                logger.error("Failed to send auto-reply: %s", exc)
        # Fall back to draft if auto-reply not enabled or failed
        if gmail_service:
            try:
                from tools.gmail_tools import create_draft
                create_draft(gmail_service, email_data, reply_text)
            except Exception as exc:
                logger.error("Failed to create draft: %s", exc)
        return {"status": "drafted", "action": "draft_created"}

    elif action == "DRAFT_REPLY":
        reply_text = _extract_reply(ai_response)
        if gmail_service:
            try:
                from tools.gmail_tools import create_draft
                create_draft(gmail_service, email_data, reply_text)
            except Exception as exc:
                logger.error("Failed to create draft: %s", exc)
        return {"status": "drafted", "action": "draft_created"}

    elif action == "ESCALATE":
        return {"status": "escalated", "action": "escalated"}

    elif action == "LABEL_ARCHIVE":
        return {"status": "archived", "action": "labeled_archived"}

    elif action == "SCHEDULE_FOLLOWUP":
        return {"status": "followup", "action": "followup_scheduled"}

    return {"status": "skipped", "action": "no_action"}


def _log_action(
    user_id: str,
    email_data: dict[str, Any],
    decision: dict[str, Any],
    action_result: dict[str, str],
) -> None:
    """Log the processed action to the audit log.

    Args:
        user_id: The user ID.
        email_data: The email dict.
        decision: The AI decision.
        action_result: The execution result.
    """
    sender = email_data.get("sender", {})
    sender_email = (
        sender.get("email", "unknown")
        if isinstance(sender, dict)
        else str(sender)
    )

    try:
        persist_action(ActionLogCreate(
            email_from=sender_email,
            action_taken=decision.get("action", "unknown"),
            tool_used=f"{decision.get('provider', 'unknown')}/{decision.get('model', 'unknown')}",
            outcome=action_result.get("status", "unknown"),
            metadata={
                "email_id": email_data.get("id", ""),
                "subject": email_data.get("subject", ""),
                "category": decision.get("category", ""),
                "user_id": user_id,
            },
        ))
    except Exception as exc:
        logger.error("Failed to log action: %s", exc)


def _update_sender_memory(
    sender_email: str,
    email_data: dict[str, Any],
    decision: dict[str, Any],
) -> None:
    """Update long-term memory for the sender after processing.

    Args:
        sender_email: The sender's email address.
        email_data: The original email data.
        decision: The AI decision dict.
    """
    history_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "email_id": email_data.get("id", ""),
        "subject": email_data.get("subject", ""),
        "action": decision.get("action", "unknown"),
        "provider": decision.get("provider", "unknown"),
    }

    try:
        update_sender_memory(
            email=sender_email,
            data=SenderProfileUpdate(history_entry=history_entry),
        )
    except Exception as exc:
        logger.error("Failed to update sender memory for %s: %s", sender_email, exc)


# ============================================================================
# Main reasoning loop
# ============================================================================


async def run_agent_loop(
    user_config: dict[str, Any] | None = None,
    user_id: str | None = None,
    single_run: bool = False,
) -> dict[str, Any]:
    """Run the GmailMind autonomous reasoning loop using AI Router.

    This is the main entry point for the agent. It continuously:
      1. Fetches new emails and due follow-ups.
      2. Loads the correct agent via the Orchestrator.
      3. Processes each email through agent.process_email() (AI Router).
      4. Executes actions, logs results, updates memory.
      5. Sleeps until the next interval.

    Args:
        user_config: Pre-loaded business config, or None to load automatically.
        user_id: User ID for config loading (used if user_config is None).
        single_run: If True, run once and return (for testing / Celery tasks).

    Returns:
        Dict with processed count and results (in single_run mode).
    """
    _uid = user_id or "default"

    # Load config
    if user_config is None:
        user_config = load_business_config(user_id=_uid)

    logger.info(
        "Starting reasoning loop for %s (interval=%ds, single_run=%s).",
        user_config.get("business_name", "unknown"),
        POLL_INTERVAL_SECONDS,
        single_run,
    )

    # Build Gmail service
    gmail_service = None
    try:
        gmail_service = _build_gmail_service(user_config, user_id=_uid)
        calendar_service = _build_calendar_service(user_config, user_id=_uid)
        set_services(gmail_service, calendar_service)
    except RuntimeError as exc:
        logger.error("Cannot start agent loop: %s", exc)
        if single_run:
            return {"error": "Gmail not connected", "details": str(exc)}
        raise

    # Load the correct agent via Orchestrator
    from orchestrator.orchestrator import GmailMindOrchestrator
    orchestrator = GmailMindOrchestrator()
    agent = orchestrator.get_agent_for_user(_uid)

    all_results = []

    while True:
        loop_start = datetime.now(timezone.utc)
        logger.info("═══ Agent loop iteration starting at %s ═══", loop_start.isoformat())

        try:
            # --- 1. OBSERVE ---
            emails = _fetch_new_emails(gmail_service)
            followups = _fetch_due_followups()
            logger.info(
                "Observed: %d new emails, %d due follow-ups.",
                len(emails),
                len(followups),
            )

            if not emails and not followups and single_run:
                return {"processed": 0, "message": "No new emails", "results": []}

            # --- 2. THINK + ACT (per email via AI Router) ---
            results = []
            for email_data in emails:
                if safety_guard.is_daily_limit_exceeded():
                    logger.warning("Daily limit exceeded — stopping processing.")
                    session_memory.add_escalation(
                        "SYSTEM",
                        reason="Daily action limit exceeded. Remaining emails skipped.",
                    )
                    break

                result = await _process_single_email(
                    agent, email_data, user_config,
                    user_id=_uid, gmail_service=gmail_service,
                )
                results.append(result)

            # --- 3. Handle due follow-ups ---
            for followup in followups:
                if safety_guard.is_daily_limit_exceeded():
                    logger.warning("Daily limit exceeded — stopping follow-up processing.")
                    break

                await _process_due_followup(agent, followup, user_config, user_id=_uid)

            # --- 4. REPORT ---
            summary = session_memory.summary()
            logger.info(
                "Loop iteration complete. Summary: emails_seen=%d, "
                "actions=%d, escalations=%d.",
                summary["emails_seen"],
                summary["actions_taken"],
                summary["pending_escalations"],
            )

            all_results.extend(results)

        except Exception as exc:
            logger.exception("Error in agent loop iteration: %s", exc)

        # --- 5. SLEEP ---
        if single_run:
            logger.info("Single-run mode — exiting loop.")
            return {"processed": len(all_results), "results": all_results}

        logger.info("Sleeping for %d seconds...", POLL_INTERVAL_SECONDS)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
