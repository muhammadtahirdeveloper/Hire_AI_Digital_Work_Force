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

    # Noreply / automated sender patterns — never auto-reply to these
    NOREPLY_PATTERNS = [
        "noreply", "no-reply", "do-not-reply", "donotreply",
        "automated", "mailer-daemon", "notification", "alerts",
        "system", "postmaster", "bounce",
    ]

    # ------------------------------------------------------------------
    # Tier-specific system prompts
    # ------------------------------------------------------------------

    _PROMPTS = {
        "tier1": (
            "You are an email organization assistant. "
            "Read emails, apply labels, archive newsletters and social notifications. "
            "Do NOT auto-reply. Just organize.\n\n"
            "Classification rules (STRICT — follow in order):\n"
            "1. Job applications (CV, resume, cover letter, applying for) → label 'Applications', keep in INBOX\n"
            "2. Business inquiries (pricing, quote, demo, partnership, interested) → label 'Business', keep in INBOX\n"
            "3. Personal emails from known contacts → label 'Personal', keep in INBOX\n"
            "4. Facebook/LinkedIn/Twitter/Instagram/social media notifications → ARCHIVE immediately\n"
            "5. Newsletters with 'unsubscribe' link → ARCHIVE immediately\n"
            "6. Obvious spam (lottery, Nigerian prince, viagra, click-bait) → move to SPAM\n"
            "7. Urgent keywords (payment due, lawsuit, legal notice, urgent, emergency) → label 'Urgent', keep in INBOX\n\n"
            "IMPORTANT: NEVER mark legitimate business emails as spam. When in doubt, keep in INBOX."
        ),
        "tier2": (
            "You are an intelligent email assistant. "
            "Read emails, organize, auto-reply to inquiries, "
            "escalate urgent issues, track follow-ups.\n\n"
            "Classification and action rules (STRICT — follow in order):\n"
            "1. Job applications (CV, resume, cover letter, applying for) → AUTO_REPLY with professional acknowledgment\n"
            "2. Business inquiries (pricing, quote, demo, partnership, interested in services) → AUTO_REPLY with helpful response\n"
            "3. Personal emails from known contacts → keep in INBOX, do NOT auto-reply\n"
            "4. Facebook/LinkedIn/Twitter/Instagram/social media notifications → ARCHIVE immediately\n"
            "5. Newsletters with 'unsubscribe' link → ARCHIVE immediately\n"
            "6. Obvious spam (lottery, Nigerian prince, viagra, click-bait, phishing) → move to SPAM\n"
            "7. Urgent keywords (payment due, lawsuit, legal notice, urgent, emergency, overdue) → ESCALATE to owner immediately\n"
            "8. Automated system notifications (noreply, no-reply, system alerts) → label and ARCHIVE\n\n"
            "IMPORTANT: NEVER block or spam-mark legitimate business emails. "
            "NEVER auto-reply to spam or social notifications. "
            "When in doubt, keep in INBOX and let the user decide."
        ),
        "tier3": (
            "You are an advanced business email manager. "
            "Full automation, analytics, team coordination, "
            "CRM sync, comprehensive reporting.\n\n"
            "Classification and action rules (STRICT — follow in order):\n"
            "1. Job applications (CV, resume, cover letter, applying for) → AUTO_REPLY with professional acknowledgment, log to CRM\n"
            "2. Business inquiries (pricing, quote, demo, partnership) → AUTO_REPLY with helpful response, create CRM lead\n"
            "3. Personal emails from known contacts → keep in INBOX, do NOT auto-reply\n"
            "4. Facebook/LinkedIn/Twitter/Instagram/social media notifications → ARCHIVE immediately\n"
            "5. Newsletters with 'unsubscribe' link → ARCHIVE immediately\n"
            "6. Obvious spam (lottery, Nigerian prince, viagra, click-bait, phishing) → move to SPAM\n"
            "7. Urgent keywords (payment due, lawsuit, legal notice, urgent, emergency, overdue) → ESCALATE to owner immediately\n"
            "8. Automated system notifications (noreply, no-reply, system alerts) → label and ARCHIVE\n\n"
            "IMPORTANT: NEVER block or spam-mark legitimate business emails. "
            "NEVER auto-reply to spam or social notifications. "
            "When in doubt, keep in INBOX and let the user decide."
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
    # Email classification keywords (ordered by priority)
    # ------------------------------------------------------------------

    _CATEGORIES = {
        "spam": [
            r"lottery", r"winner", r"click here", r"act now",
            r"limited time", r"nigerian", r"viagra", r"cialis",
            r"earn money fast", r"million dollars", r"inheritance",
            r"prince", r"claim your prize", r"free money",
        ],
        "urgent": [
            r"urgent", r"asap", r"emergency", r"immediately",
            r"critical", r"legal\s+notice", r"lawsuit", r"complaint",
            r"payment\s+due", r"payment\s+overdue", r"overdue",
            r"final\s+notice", r"court\s+order", r"subpoena",
            r"deadline\s+today", r"action\s+required",
        ],
        "job_application": [
            r"applying\s+for", r"job\s+application", r"cover\s+letter",
            r"resume", r"curriculum\s+vitae", r"\bcv\b",
            r"position\s+of", r"open\s+position", r"job\s+opening",
            r"attached\s+my\s+resume", r"application\s+for",
            r"candidate\s+for", r"applying\s+to",
        ],
        "inquiry": [
            r"interested", r"pricing", r"demo", r"quote",
            r"inquiry", r"information about", r"learn more",
            r"partnership", r"proposal", r"collaboration",
            r"services", r"consultation", r"would like to discuss",
            r"business\s+opportunity", r"rates",
        ],
        "social_notification": [
            r"facebook", r"instagram", r"linkedin", r"twitter",
            r"tiktok", r"snapchat", r"pinterest", r"whatsapp",
            r"youtube", r"reddit",
            r"commented on your", r"liked your", r"tagged you",
            r"sent you a message", r"friend request",
            r"new follower", r"connection request",
            r"someone mentioned you",
        ],
        "newsletter": [
            r"unsubscribe", r"newsletter", r"promotional",
            r"weekly digest", r"mailing list", r"email preferences",
            r"manage\s+subscription", r"opt.?out",
            r"view in browser", r"update your preferences",
        ],
        "notification": [
            r"notification", r"alert", r"automated", r"noreply",
            r"no.reply", r"do not reply", r"system notification",
            r"auto.?generated", r"this is an automated",
        ],
        "personal": [
            r"hey\b", r"hi\b", r"hello\b", r"how are you",
            r"miss you", r"love\b", r"family",
            r"catch up", r"long time",
        ],
    }

    # ------------------------------------------------------------------
    # Category → recommended action mapping
    # ------------------------------------------------------------------

    CATEGORY_ACTIONS = {
        "noreply": "ARCHIVE",
        "job_application": "AUTO_REPLY",
        "inquiry": "AUTO_REPLY",
        "personal": "INBOX",
        "social_notification": "ARCHIVE",
        "newsletter": "ARCHIVE",
        "notification": "ARCHIVE",
        "spam": "SPAM",
        "urgent": "ESCALATE",
        "business": "INBOX",
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

        Categories (checked in priority order):
            'spam', 'urgent', 'job_application', 'inquiry',
            'social_notification', 'newsletter', 'notification',
            'personal', 'business'

        Args:
            email: Email dict with 'subject' and 'body' keys.

        Returns:
            Category string.
        """
        subject = (email.get("subject", "") or "").lower()
        body = (email.get("body", "") or email.get("snippet", "") or "").lower()
        sender = (
            email.get("from", "")
            or (email.get("sender", {}) or {}).get("email", "")
            or ""
        ).lower()
        text = f"{subject} {body}"

        # Check noreply/automated senders first — never reply to these
        for pattern in self.NOREPLY_PATTERNS:
            if pattern in sender:
                logger.info(
                    "%s: Sender '%s' matches noreply pattern '%s' → ARCHIVE only",
                    self.agent_name, sender, pattern,
                )
                return "noreply"

        # Check categories in priority order
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

    def get_recommended_action(self, email: dict) -> str:
        """Return the recommended action for an email based on its category.

        Actions: AUTO_REPLY, INBOX, ARCHIVE, SPAM, ESCALATE

        Args:
            email: Email dict with 'subject' and 'body' keys.

        Returns:
            Action string.
        """
        category = self.classify_email(email)
        action = self.CATEGORY_ACTIONS.get(category, "INBOX")
        logger.info(
            "%s: Recommended action for category '%s' → %s",
            self.agent_name, category, action,
        )
        return action
