"""High-level email processing pipeline.

Wires together: Gmail → Agent → AI Router → Action → Database.
This is the primary entry point for processing a user's inbox,
used by scheduler tasks and API endpoints.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from agent.tool_wrappers import (
    standalone_create_draft,
    standalone_label_email,
    standalone_mark_as_read,
    standalone_read_emails,
    standalone_reply_to_email,
)
from config.database import SessionLocal

logger = logging.getLogger(__name__)


class EmailProcessor:
    """High-level email processing pipeline.

    Usage::

        processor = EmailProcessor(user_id="usr_123")
        result = await processor.process_inbox()
        print(result)  # {"processed": 5, "total": 5, "results": [...]}
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.logger = logging.getLogger(f"{__name__}.{user_id}")

    async def process_inbox(self) -> dict[str, Any]:
        """Full pipeline: fetch → classify → decide → act → log.

        Returns:
            Dict with processed count, total emails, and per-email results.
        """
        # 1. Get Gmail service
        service = self._build_service()
        if not service:
            return {"error": "Gmail not connected", "processed": 0}

        # 2. Fetch unread emails
        try:
            emails = standalone_read_emails(service, max_results=20)
        except Exception as exc:
            self.logger.error("Failed to fetch emails: %s", exc)
            return {"error": f"Failed to fetch emails: {exc}", "processed": 0}

        if not emails:
            return {"processed": 0, "message": "No new emails"}

        # 3. Get agent for this user
        agent = self._get_agent()

        # 4. Process each email
        results = []
        processed = 0
        for email in emails:
            try:
                decision = await agent.process_email(self.user_id, email)
                action_result = await self._execute(service, email, decision)
                self._log(email, decision)
                processed += 1

                results.append({
                    "email_from": email.get("from", email.get("sender", "")),
                    "subject": email.get("subject", ""),
                    "action": decision.get("action", "unknown"),
                    "provider": decision.get("provider", "unknown"),
                    "model": decision.get("model", "unknown"),
                    "status": action_result.get("status", "processed"),
                })
            except Exception as exc:
                self.logger.error("Email processing failed: %s", exc)
                results.append({
                    "email_from": email.get("from", ""),
                    "error": str(exc),
                })

        # 5. Update agent status
        self._update_status(processed)

        return {"processed": processed, "total": len(emails), "results": results}

    def _build_service(self) -> Any:
        """Build Gmail API service from stored credentials.

        Returns:
            Gmail API service or None if not available.
        """
        try:
            from config.business_config import load_business_config
            from agent.reasoning_loop import _build_gmail_service
            config = load_business_config(user_id=self.user_id)
            return _build_gmail_service(config, user_id=self.user_id)
        except Exception as exc:
            self.logger.error("Failed to build Gmail service: %s", exc)
            return None

    def _get_agent(self) -> Any:
        """Get the correct agent for this user via Orchestrator.

        Returns:
            An instantiated BaseAgent subclass.
        """
        from orchestrator.orchestrator import GmailMindOrchestrator
        orchestrator = GmailMindOrchestrator()
        return orchestrator.get_agent_for_user(self.user_id)

    async def _execute(
        self,
        service: Any,
        email: dict[str, Any],
        decision: dict[str, Any],
    ) -> dict[str, str]:
        """Execute the AI decision (reply, draft, label, etc.).

        Args:
            service: Gmail API service.
            email: Original email dict.
            decision: AI decision with 'action' and 'ai_response'.

        Returns:
            Dict with status and action taken.
        """
        import re

        action = decision.get("action", "DRAFT_REPLY")
        ai_response = decision.get("ai_response", "")

        # Extract reply text
        reply_text = self._extract_reply(ai_response)

        sender = email.get("sender", {})
        sender_email = (
            sender.get("email", "unknown")
            if isinstance(sender, dict)
            else str(sender)
        )
        subject = email.get("subject", "(no subject)")
        message_id = email.get("id", "")

        if action == "AUTO_REPLY":
            if reply_text and service:
                sent = standalone_reply_to_email(service, message_id, reply_text)
                if sent:
                    standalone_mark_as_read(service, message_id)
                    return {"status": "sent", "action": "auto_replied"}
            # Fallback to draft
            if service:
                standalone_create_draft(service, sender_email, f"Re: {subject}", reply_text)
            return {"status": "drafted", "action": "draft_created"}

        elif action == "DRAFT_REPLY":
            if service:
                standalone_create_draft(service, sender_email, f"Re: {subject}", reply_text)
            return {"status": "drafted", "action": "draft_created"}

        elif action == "ESCALATE":
            return {"status": "escalated", "action": "escalated"}

        elif action == "LABEL_ARCHIVE":
            category = decision.get("category", "processed")
            if service:
                standalone_label_email(service, message_id, category)
                standalone_mark_as_read(service, message_id)
            return {"status": "archived", "action": "labeled_archived"}

        elif action == "SCHEDULE_FOLLOWUP":
            return {"status": "followup", "action": "followup_scheduled"}

        return {"status": "skipped", "action": "no_action"}

    def _extract_reply(self, ai_response: str) -> str:
        """Extract reply text from AI response."""
        import re
        match = re.search(r"REPLY:\s*(.+?)(?:\nREASON:|\Z)", ai_response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ai_response.strip()

    def _log(self, email: dict[str, Any], decision: dict[str, Any]) -> None:
        """Log action to action_logs table.

        Args:
            email: The email dict.
            decision: The AI decision dict.
        """
        sender = email.get("sender", {})
        sender_email = (
            sender.get("email", email.get("from", "unknown"))
            if isinstance(sender, dict)
            else str(sender)
        )

        try:
            db = SessionLocal()
            try:
                db.execute(
                    text("""
                        INSERT INTO action_logs
                            (email_from, action_taken, tool_used, outcome, metadata, timestamp)
                        VALUES
                            (:from_addr, :action, :tool, :outcome, :meta::jsonb, NOW())
                    """),
                    {
                        "from_addr": sender_email,
                        "action": decision.get("action", "unknown"),
                        "tool": f"{decision.get('provider', 'unknown')}/{decision.get('model', 'unknown')}",
                        "outcome": "processed",
                        "meta": json.dumps({
                            "subject": email.get("subject", ""),
                            "category": decision.get("category", ""),
                            "provider": decision.get("provider", ""),
                            "model": decision.get("model", ""),
                            "user_id": self.user_id,
                        }),
                    },
                )
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            self.logger.error("Failed to log action: %s", exc)

    def _update_status(self, processed: int) -> None:
        """Update user_agents with last run info.

        Args:
            processed: Number of emails processed.
        """
        try:
            db = SessionLocal()
            try:
                db.execute(
                    text("""
                        UPDATE user_agents
                        SET last_processed_at = NOW(),
                            last_error = NULL,
                            updated_at = NOW()
                        WHERE user_id = :uid
                    """),
                    {"uid": self.user_id},
                )
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            self.logger.error("Failed to update agent status: %s", exc)
