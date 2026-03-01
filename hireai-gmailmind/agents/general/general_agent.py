"""General-purpose email agent — wraps Phase 1 GmailMind functionality.

Provides tier-specific system prompts, tool sets, and email
classification for the default 'general' industry.
"""

import logging
import re

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class GeneralAgent(BaseAgent):
    """General-purpose email management agent."""

    agent_name = "GmailMind General Agent"
    industry = "general"
    supported_tiers = ["tier1", "tier2", "tier3"]

    # ------------------------------------------------------------------
    # Tier-specific system prompts
    # ------------------------------------------------------------------

    _PROMPTS = {
        "tier1": (
            "You are an email organization assistant. "
            "Read emails, apply labels, archive newsletters. "
            "Do NOT auto-reply. Just organize."
        ),
        "tier2": (
            "You are an intelligent email assistant. "
            "Read emails, organize, auto-reply to inquiries, "
            "escalate urgent issues, track follow-ups."
        ),
        "tier3": (
            "You are an advanced business email manager. "
            "Full automation, analytics, team coordination, "
            "CRM sync, comprehensive reporting."
        ),
    }

    # ------------------------------------------------------------------
    # Tier-specific tool sets
    # ------------------------------------------------------------------

    _TOOLS = {
        "tier1": [
            "read_emails",
            "label_email",
            "search_emails",
        ],
        "tier2": [
            "read_emails",
            "label_email",
            "search_emails",
            "reply_to_email",
            "send_escalation_alert",
            "schedule_followup",
            "create_draft",
        ],
        "tier3": [
            "read_emails",
            "label_email",
            "search_emails",
            "reply_to_email",
            "send_escalation_alert",
            "schedule_followup",
            "create_draft",
            "send_email",
            "create_calendar_event",
            "get_crm_contact",
            "update_crm",
        ],
    }

    # ------------------------------------------------------------------
    # Email classification keywords
    # ------------------------------------------------------------------

    _CATEGORIES = {
        "spam": [
            r"lottery", r"winner", r"click here", r"act now",
            r"limited time", r"nigerian", r"viagra", r"cialis",
        ],
        "newsletter": [
            r"unsubscribe", r"newsletter", r"promotional",
            r"weekly digest", r"mailing list",
        ],
        "urgent": [
            r"urgent", r"asap", r"emergency", r"immediately",
            r"critical", r"legal", r"lawsuit", r"complaint",
        ],
        "inquiry": [
            r"interested", r"pricing", r"demo", r"quote",
            r"inquiry", r"information about", r"learn more",
        ],
        "notification": [
            r"notification", r"alert", r"automated", r"noreply",
            r"do not reply", r"system notification",
        ],
        "personal": [
            r"hey\b", r"hi\b", r"hello\b", r"how are you",
            r"miss you", r"love\b", r"family",
        ],
    }

    # ------------------------------------------------------------------
    # Abstract method implementations
    # ------------------------------------------------------------------

    def get_system_prompt(self, tier: str) -> str:
        """Return the system prompt for the given tier."""
        prompt = self._PROMPTS.get(tier, self._PROMPTS["tier1"])
        logger.info("%s: Using system prompt for tier=%s", self.agent_name, tier)
        return prompt

    def get_available_tools(self, tier: str) -> list[str]:
        """Return the list of available tools for the given tier."""
        tools = self._TOOLS.get(tier, self._TOOLS["tier1"])
        logger.info("%s: %d tools available for tier=%s", self.agent_name, len(tools), tier)
        return tools

    def classify_email(self, email: dict) -> str:
        """Classify an email into a category using keyword matching.

        Categories: 'newsletter', 'inquiry', 'urgent', 'spam',
                    'notification', 'personal', 'business'

        Args:
            email: Email dict with 'subject' and 'body' keys.

        Returns:
            Category string.
        """
        subject = (email.get("subject", "") or "").lower()
        body = (email.get("body", "") or email.get("snippet", "") or "").lower()
        text = f"{subject} {body}"

        for category, patterns in self._CATEGORIES.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    logger.info(
                        "%s: Classified email as '%s' (matched: %s)",
                        self.agent_name, category, pattern,
                    )
                    return category

        # Default category
        logger.info("%s: Classified email as 'business' (no keyword match).", self.agent_name)
        return "business"
