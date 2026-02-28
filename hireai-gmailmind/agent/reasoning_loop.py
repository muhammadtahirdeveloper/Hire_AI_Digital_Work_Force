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
from datetime import datetime, timezone
from typing import Any, Optional

from agents import Runner

from agent.gmailmind import build_email_context_message, create_agent
from agent.safety_guard import SafetyViolationError, safety_guard
from agent.tool_wrappers import set_services
from config.business_config import load_business_config
from config.credentials import build_credentials, refresh_credentials
from config.settings import OPENAI_API_KEY, POLL_INTERVAL_SECONDS
from memory.long_term import (
    create_follow_up,
    get_actions_for_sender,
    get_pending_follow_ups,
    get_sender_memory,
    log_action as persist_action,
    update_sender_memory,
)
from memory.schemas import ActionLogCreate, SenderProfileUpdate
from memory.short_term import session_memory

logger = logging.getLogger(__name__)


# ============================================================================
# Service initialisation helpers
# ============================================================================


def _build_gmail_service(user_config: dict[str, Any]) -> Any:
    """Build an authenticated Gmail API service from stored credentials.

    Args:
        user_config: Business config that may contain OAuth token data.

    Returns:
        An authenticated Gmail API ``Resource`` object.

    Raises:
        RuntimeError: If credentials are missing or invalid.
    """
    from googleapiclient.discovery import build as google_build

    token_data = user_config.get("oauth_token", {})
    if not token_data:
        raise RuntimeError(
            "No OAuth token found in user config. "
            "Run the OAuth setup flow first."
        )

    creds = build_credentials(
        token=token_data.get("access_token", ""),
        refresh_token=token_data.get("refresh_token", ""),
    )
    creds = refresh_credentials(creds)

    service = google_build("gmail", "v1", credentials=creds)
    logger.info("Gmail service built successfully.")
    return service


def _build_calendar_service(user_config: dict[str, Any]) -> Optional[Any]:
    """Build an authenticated Google Calendar service (optional).

    Returns None if Calendar scopes are not configured.
    """
    try:
        from googleapiclient.discovery import build as google_build

        token_data = user_config.get("oauth_token", {})
        if not token_data:
            return None

        creds = build_credentials(
            token=token_data.get("access_token", ""),
            refresh_token=token_data.get("refresh_token", ""),
        )
        creds = refresh_credentials(creds)

        service = google_build("calendar", "v3", credentials=creds)
        logger.info("Calendar service built successfully.")
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


def _update_memory_after_action(
    sender_email: str,
    email_data: dict[str, Any],
    agent_output: str,
) -> None:
    """Update long-term and short-term memory after the agent acts.

    Args:
        sender_email: The sender's email address.
        email_data: The original email data dict.
        agent_output: The agent's textual output / summary.
    """
    # Update sender profile with interaction record
    history_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "email_id": email_data.get("id", ""),
        "subject": email_data.get("subject", ""),
        "action": "processed",
        "note": agent_output[:500],  # truncate to keep history manageable
    }

    update_sender_memory(
        email=sender_email,
        data=SenderProfileUpdate(history_entry=history_entry),
    )

    # Persist action to audit log
    persist_action(ActionLogCreate(
        email_from=sender_email,
        action_taken="agent_processed_email",
        tool_used="gmailmind_agent",
        outcome=agent_output[:1000],
        metadata={
            "email_id": email_data.get("id", ""),
            "subject": email_data.get("subject", ""),
        },
    ))

    logger.info("Memory updated for sender %s after processing.", sender_email)


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
) -> str:
    """Run the GmailMind agent against a single email.

    Args:
        agent: The GmailMind Agent instance.
        email_data: The email dict to process.
        user_config: The business configuration.

    Returns:
        The agent's textual output after processing.
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

    # Gather memory context
    sender_history = _get_sender_context(sender_email)
    sender_followups = _get_sender_followups(sender_email)
    business_goals = user_config.get("business_goals", [])
    today_actions = session_memory.action_count()

    # Build the context message
    context_message = build_email_context_message(
        email_data=email_data,
        sender_history=sender_history,
        business_goals=business_goals,
        today_actions_count=today_actions,
        pending_followups=sender_followups if sender_followups else None,
    )

    # Run the agent
    logger.info(
        "Running GmailMind agent for email %s from %s: %s",
        email_data.get("id", "?"),
        sender_email,
        email_data.get("subject", "(no subject)"),
    )

    try:
        result = await Runner.run(agent, input=context_message)
        agent_output = result.final_output if result.final_output else ""
        logger.info(
            "Agent completed for email %s. Output length: %d chars.",
            email_data.get("id", "?"),
            len(agent_output),
        )
    except SafetyViolationError as exc:
        agent_output = f"[SAFETY BLOCK] {exc}"
        logger.warning("Safety violation for email %s: %s", email_data.get("id", "?"), exc)
        session_memory.add_escalation(
            email_data.get("id", ""),
            reason=str(exc),
            sender=sender_email,
        )
    except Exception as exc:
        agent_output = f"[ERROR] Failed to process: {exc}"
        logger.exception("Agent error for email %s.", email_data.get("id", "?"))

    # Post-action: update memory and summary
    _update_memory_after_action(sender_email, email_data, agent_output)
    _append_to_daily_summary(email_data, agent_output)

    return agent_output


async def _process_due_followup(
    agent: Any,
    followup: dict[str, Any],
    user_config: dict[str, Any],
) -> str:
    """Handle a follow-up that has come due.

    Creates a synthetic context message for the agent so it can decide
    what to do (e.g. send a follow-up email, create a draft, escalate).

    Args:
        agent: The GmailMind Agent instance.
        followup: The follow-up dict (email_id, sender, note, due_time).
        user_config: The business configuration.

    Returns:
        The agent's output.
    """
    sender_email = followup.get("sender", "")
    email_id = followup.get("email_id", "")
    note = followup.get("note", "")

    sender_history = _get_sender_context(sender_email)
    business_goals = user_config.get("business_goals", [])
    today_actions = session_memory.action_count()

    goals_text = "\n".join(
        f"  {i}. {g}" for i, g in enumerate(business_goals, 1)
    )

    context = f"""
═══════════════════════════════════════════════
FOLLOW-UP DUE — ACTION REQUIRED
═══════════════════════════════════════════════

A scheduled follow-up is now due:

  Original Email ID: {email_id}
  Sender: {sender_email}
  Follow-up Note: {note}
  Due Time: {followup.get('due_time', 'now')}

**Sender Memory:**
{json.dumps(sender_history, indent=2, default=str) if sender_history else '  (no history)'}

**Session Context:**
  Actions taken today: {today_actions}
  Active business goals:
{goals_text}

═══════════════════════════════════════════════
INSTRUCTIONS: Decide what follow-up action to take.
Options: send a follow-up email, create a draft, search for the original
thread and reply, or escalate if the matter seems unresolved.
═══════════════════════════════════════════════
"""

    try:
        result = await Runner.run(agent, input=context)
        agent_output = result.final_output if result.final_output else ""
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

    return agent_output


# ============================================================================
# Main reasoning loop
# ============================================================================


async def run_agent_loop(
    user_config: dict[str, Any] | None = None,
    user_id: str | None = None,
    single_run: bool = False,
) -> None:
    """Run the GmailMind autonomous reasoning loop.

    This is the main entry point for the agent. It continuously:
      1. Fetches new emails and due follow-ups.
      2. Processes each with the GmailMind agent.
      3. Updates memory and daily summary.
      4. Sleeps until the next interval.

    Args:
        user_config: Pre-loaded business config, or None to load automatically.
        user_id: User ID for config loading (used if user_config is None).
        single_run: If True, run once and return (for testing / Celery tasks).
    """
    # Load config
    if user_config is None:
        user_config = load_business_config(user_id=user_id)

    logger.info(
        "Starting GmailMind reasoning loop for %s (interval=%ds, single_run=%s).",
        user_config.get("business_name", "unknown"),
        POLL_INTERVAL_SECONDS,
        single_run,
    )

    # Build services
    try:
        gmail_service = _build_gmail_service(user_config)
        calendar_service = _build_calendar_service(user_config)
        set_services(gmail_service, calendar_service)
    except RuntimeError as exc:
        logger.error("Cannot start agent loop: %s", exc)
        raise

    # Create agent
    agent = create_agent(user_config)

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

            # --- 2. THINK + ACT (per email) ---
            for email_data in emails:
                # Check daily limit before processing
                if safety_guard.is_daily_limit_exceeded():
                    logger.warning("Daily limit exceeded — stopping processing.")
                    session_memory.add_escalation(
                        "SYSTEM",
                        reason="Daily action limit exceeded. Remaining emails skipped.",
                    )
                    break

                await _process_single_email(agent, email_data, user_config)

            # --- 3. Handle due follow-ups ---
            for followup in followups:
                if safety_guard.is_daily_limit_exceeded():
                    logger.warning("Daily limit exceeded — stopping follow-up processing.")
                    break

                await _process_due_followup(agent, followup, user_config)

            # --- 4. REPORT ---
            summary = session_memory.summary()
            logger.info(
                "Loop iteration complete. Summary: emails_seen=%d, "
                "actions=%d, escalations=%d.",
                summary["emails_seen"],
                summary["actions_taken"],
                summary["pending_escalations"],
            )

        except Exception as exc:
            logger.exception("Error in agent loop iteration: %s", exc)

        # --- 5. SLEEP ---
        if single_run:
            logger.info("Single-run mode — exiting loop.")
            break

        logger.info("Sleeping for %d seconds...", POLL_INTERVAL_SECONDS)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
