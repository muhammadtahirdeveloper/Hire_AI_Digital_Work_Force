"""Short-term (in-memory) session state for GmailMind.

This module provides a lightweight, per-process memory store that resets on
every application restart. It tracks the current session's working context
so the agent can reason about what has happened *this run* without hitting
the database.

Typical usage::

    from memory.short_term import session_memory

    session_memory.add_email("msg_abc123", {...})
    session_memory.log_action("read_emails", "Fetched 5 new emails")
    session_memory.add_escalation("msg_xyz", "Urgent billing complaint")
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """In-memory session state that resets each run.

    Attributes:
        current_session_emails: Map of email_id -> email metadata seen this session.
        actions_taken_today: Chronological list of actions taken this session.
        pending_escalations: Emails flagged for human review this session.
    """

    def __init__(self) -> None:
        self.current_session_emails: dict[str, dict[str, Any]] = {}
        self.actions_taken_today: list[dict[str, Any]] = []
        self.pending_escalations: list[dict[str, Any]] = []
        logger.info("ShortTermMemory initialized (empty session).")

    # -- Session Emails ---------------------------------------------------

    def add_email(self, email_id: str, metadata: dict[str, Any]) -> None:
        """Register an email as seen in the current session.

        Args:
            email_id: Gmail message ID.
            metadata: Arbitrary email data (subject, sender, snippet, etc.).
        """
        self.current_session_emails[email_id] = {
            **metadata,
            "seen_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info("ShortTermMemory: Tracked email %s.", email_id)

    def get_email(self, email_id: str) -> Optional[dict[str, Any]]:
        """Retrieve metadata for a previously seen email.

        Args:
            email_id: Gmail message ID.

        Returns:
            The metadata dict, or None if the email was not seen this session.
        """
        return self.current_session_emails.get(email_id)

    def list_session_emails(self) -> list[str]:
        """Return all email IDs seen this session."""
        return list(self.current_session_emails.keys())

    # -- Actions ----------------------------------------------------------

    def log_action(self, tool_used: str, description: str, **extra: Any) -> None:
        """Record an action taken by the agent this session.

        Args:
            tool_used: Name of the tool/function that was invoked.
            description: Human-readable description of what happened.
            **extra: Any additional context to store.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_used": tool_used,
            "description": description,
            **extra,
        }
        self.actions_taken_today.append(entry)
        logger.info("ShortTermMemory: Logged action — %s: %s", tool_used, description)

    def get_actions(self) -> list[dict[str, Any]]:
        """Return all actions recorded this session (chronological order)."""
        return list(self.actions_taken_today)

    def action_count(self) -> int:
        """Return the total number of actions taken this session."""
        return len(self.actions_taken_today)

    # -- Escalations ------------------------------------------------------

    def add_escalation(self, email_id: str, reason: str, **extra: Any) -> None:
        """Flag an email for human escalation.

        Args:
            email_id: Gmail message ID that needs attention.
            reason: Why this email requires escalation.
            **extra: Additional context (sender, urgency, etc.).
        """
        entry = {
            "email_id": email_id,
            "reason": reason,
            "flagged_at": datetime.now(timezone.utc).isoformat(),
            **extra,
        }
        self.pending_escalations.append(entry)
        logger.info(
            "ShortTermMemory: Escalation added for %s — %s", email_id, reason
        )

    def get_escalations(self) -> list[dict[str, Any]]:
        """Return all pending escalations from this session."""
        return list(self.pending_escalations)

    def escalation_count(self) -> int:
        """Return the number of pending escalations."""
        return len(self.pending_escalations)

    # -- Reset ------------------------------------------------------------

    def reset(self) -> None:
        """Clear all session state."""
        self.current_session_emails.clear()
        self.actions_taken_today.clear()
        self.pending_escalations.clear()
        logger.info("ShortTermMemory: Session state reset.")

    # -- Summary ----------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        """Return a snapshot of the current session state.

        Useful for injecting context into agent prompts.
        """
        return {
            "emails_seen": len(self.current_session_emails),
            "actions_taken": len(self.actions_taken_today),
            "pending_escalations": len(self.pending_escalations),
            "recent_actions": self.actions_taken_today[-5:],
        }


# Module-level singleton — import and use directly.
session_memory = ShortTermMemory()
