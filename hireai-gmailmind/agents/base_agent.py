"""Base agent abstract class for all GmailMind specialist agents.

All industry-specific agents (GeneralAgent, HRAgent, etc.) must
inherit from BaseAgent and implement the abstract methods.
Concrete methods provide shared functionality like logging,
sender context lookup, and email formatting.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from memory.long_term import get_sender_memory, log_action
from memory.schemas import ActionLogCreate

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all GmailMind agents."""

    # Subclasses must set these
    agent_name: str = "BaseAgent"
    industry: str = "general"
    supported_tiers: list[str] = ["tier1", "tier2", "tier3"]

    # ------------------------------------------------------------------
    # Abstract methods — subclasses MUST implement
    # ------------------------------------------------------------------

    @abstractmethod
    def get_system_prompt(self, tier: str) -> str:
        """Return the system prompt for this agent at the given tier.

        Args:
            tier: Subscription tier (tier1/tier2/tier3).

        Returns:
            System prompt string.
        """
        ...

    @abstractmethod
    def get_available_tools(self, tier: str) -> list[str]:
        """Return the list of tool names available for this tier.

        Args:
            tier: Subscription tier.

        Returns:
            List of tool name strings.
        """
        ...

    @abstractmethod
    def classify_email(self, email: dict) -> str:
        """Classify an email into a category.

        Args:
            email: Email dict with 'subject', 'body', 'sender', etc.

        Returns:
            Category string.
        """
        ...

    # ------------------------------------------------------------------
    # Concrete methods — shared by all agents
    # ------------------------------------------------------------------

    def validate_tier(self, tier: str) -> bool:
        """Check if this agent supports the given tier.

        Args:
            tier: Subscription tier to validate.

        Returns:
            True if the tier is supported.
        """
        valid = tier in self.supported_tiers
        if not valid:
            logger.warning(
                "%s: Tier '%s' not supported. Supported: %s",
                self.agent_name, tier, self.supported_tiers,
            )
        return valid

    def log_action(
        self,
        user_id: str,
        action: str,
        details: str,
        outcome: str = "success",
    ) -> None:
        """Log an agent action to the persistent audit log.

        Args:
            user_id: The user ID.
            action: Action name (e.g. 'auto_reply', 'label_email').
            details: Description of what was done.
            outcome: Result ('success' or 'error').
        """
        try:
            log_action(ActionLogCreate(
                email_from=user_id,
                action_taken=action,
                tool_used=self.agent_name,
                outcome=outcome,
                metadata={"details": details},
            ))
            logger.info(
                "%s: Logged action '%s' for user=%s (outcome=%s)",
                self.agent_name, action, user_id, outcome,
            )
        except Exception as exc:
            logger.error("%s: Failed to log action: %s", self.agent_name, exc)

    def get_sender_context(self, sender_email: str) -> dict:
        """Load long-term memory for a sender.

        Args:
            sender_email: The sender's email address.

        Returns:
            Sender profile dict, or empty dict if not found.
        """
        try:
            profile = get_sender_memory(sender_email)
            if profile is None:
                return {}
            return profile.model_dump(mode="json")
        except Exception as exc:
            logger.warning(
                "%s: Error loading sender context for %s: %s",
                self.agent_name, sender_email, exc,
            )
            return {}

    def format_email_summary(self, email: dict) -> str:
        """Format an email into a one-line summary string.

        Args:
            email: Email dict with 'sender', 'subject', 'body'/'snippet'.

        Returns:
            Formatted summary string.
        """
        sender = email.get("sender", {})
        if isinstance(sender, dict):
            sender_str = sender.get("email", sender.get("name", "unknown"))
        else:
            sender_str = str(sender)

        subject = email.get("subject", "(no subject)")

        body = email.get("body", "") or email.get("snippet", "")
        preview = body[:100].replace("\n", " ").strip()
        if len(body) > 100:
            preview += "..."

        return f"From: {sender_str} | Subject: {subject} | Preview: {preview}"
