"""Base skills shared across all agent types.

Provides utility methods for smart replies, urgency detection,
contact extraction, and follow-up scheduling.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)


class BaseSkills:
    """Utility skills available to every agent."""

    # ------------------------------------------------------------------
    # Urgency keyword maps
    # ------------------------------------------------------------------

    _URGENCY_KEYWORDS: dict[str, list[str]] = {
        "critical": [
            "urgent", "asap", "immediately", "legal",
            "lawsuit", "complaint", "emergency",
        ],
        "high": [
            "important", "deadline", "today", "tomorrow",
            "time-sensitive", "priority",
        ],
        "medium": [
            "soon", "this week", "follow up", "follow-up",
            "reminder", "pending",
        ],
    }

    # ------------------------------------------------------------------
    # Smart reply
    # ------------------------------------------------------------------

    def smart_reply(
        self,
        email: dict,
        tone: str = "professional",
        template: str = "",
    ) -> str:
        """Generate an appropriate reply using GPT-4o.

        Args:
            email: Email dict with 'subject', 'body', and 'sender' keys.
            tone: One of 'professional', 'warm', 'urgent', 'formal'.
            template: Optional template to guide the reply style.

        Returns:
            Generated reply string, or a fallback acknowledgment.
        """
        if OPENAI_API_KEY:
            try:
                return self._smart_reply_gpt(email, tone, template)
            except Exception as exc:
                logger.warning("BaseSkills: GPT smart_reply failed: %s", exc)

        # Fallback
        sender = email.get("sender", {})
        sender_name = sender.get("name", "there") if isinstance(sender, dict) else "there"
        return (
            f"Dear {sender_name},\n\n"
            "Thank you for your email. We have received your message "
            "and will respond shortly.\n\n"
            "Best regards"
        )

    def _smart_reply_gpt(
        self,
        email: dict,
        tone: str,
        template: str,
    ) -> str:
        """Generate reply via GPT-4o."""
        import httpx

        subject = email.get("subject", "")
        body = email.get("body", "") or email.get("snippet", "")

        prompt = (
            f"Write a concise email reply (max 150 words) in a {tone} tone.\n"
        )
        if template:
            prompt += f"Use this template as a guide:\n{template}\n\n"
        prompt += (
            f"Original email subject: {subject}\n"
            f"Original email body:\n{body[:2000]}\n\n"
            "Reply only with the email body text, no subject line."
        )

        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 300,
            },
            timeout=30,
        )
        response.raise_for_status()

        reply = response.json()["choices"][0]["message"]["content"].strip()
        logger.info("BaseSkills: Generated smart reply (%d chars).", len(reply))
        return reply

    # ------------------------------------------------------------------
    # Urgency detection
    # ------------------------------------------------------------------

    def detect_urgency(self, email: dict) -> str:
        """Detect the urgency level of an email.

        Args:
            email: Email dict with 'subject' and 'body' keys.

        Returns:
            One of 'critical', 'high', 'medium', 'low'.
        """
        subject = (email.get("subject", "") or "").lower()
        body = (email.get("body", "") or email.get("snippet", "") or "").lower()
        text = f"{subject} {body}"

        for level in ("critical", "high", "medium"):
            for keyword in self._URGENCY_KEYWORDS[level]:
                if keyword in text:
                    logger.info(
                        "BaseSkills: Urgency '%s' detected (keyword: '%s').",
                        level, keyword,
                    )
                    return level

        return "low"

    # ------------------------------------------------------------------
    # Contact extraction
    # ------------------------------------------------------------------

    def extract_contact_info(self, text: str) -> dict[str, Any]:
        """Extract contact information from text using regex.

        Args:
            text: Free-form text to scan.

        Returns:
            Dict with 'email', 'phone', 'name', 'company' keys.
        """
        # Email
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        email = email_match.group(0) if email_match else None

        # Phone
        phone_match = re.search(r"[\+]?[\d\s\-\(\)]{7,15}", text)
        phone = phone_match.group(0).strip() if phone_match else None

        # Name (heuristic: "Name:" or "My name is ...")
        name = None
        name_match = re.search(
            r"(?:my name is|name:\s*|i am|i'm)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            text,
            re.IGNORECASE,
        )
        if name_match:
            name = name_match.group(1).strip()

        # Company
        company = None
        company_match = re.search(
            r"(?:company|organization|firm|employer)[\s:]+([A-Za-z0-9 &.,]+)",
            text,
            re.IGNORECASE,
        )
        if company_match:
            company = company_match.group(1).strip()

        return {
            "email": email,
            "phone": phone,
            "name": name,
            "company": company,
        }

    # ------------------------------------------------------------------
    # Follow-up date suggestion
    # ------------------------------------------------------------------

    def suggest_follow_up_date(self, context: str = "") -> str:
        """Suggest a follow-up date (default: 3 business days from today).

        Args:
            context: Optional context that may influence the date.

        Returns:
            ISO date string, e.g. '2026-03-05'.
        """
        today = datetime.now(timezone.utc).date()
        business_days_added = 0
        current = today

        while business_days_added < 3:
            current += timedelta(days=1)
            # Skip weekends
            if current.weekday() < 5:
                business_days_added += 1

        follow_up = current.isoformat()
        logger.info("BaseSkills: Suggested follow-up date: %s", follow_up)
        return follow_up
