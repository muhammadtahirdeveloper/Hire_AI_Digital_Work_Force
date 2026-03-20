"""High-level email processing pipeline.

Wires together: Gmail → Agent → AI Router → Action → Database.
This is the primary entry point for processing a user's inbox,
used by scheduler tasks and API endpoints.
"""

import asyncio
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

# Max concurrent email processing tasks
_MAX_CONCURRENT = 5


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

        # 2. Ensure HireAI-Processed label exists
        processed_label_id = self._ensure_label(service, "HireAI-Processed")

        # 3. Fetch unread emails (excluding already-processed)
        try:
            emails = standalone_read_emails(
                service, max_results=20,
                filter="is:unread -label:HireAI-Processed",
            )
        except Exception as exc:
            self.logger.error("Failed to fetch emails: %s", exc)
            return {"error": f"Failed to fetch emails: {exc}", "processed": 0}

        if not emails:
            return {"processed": 0, "message": "No new emails"}

        # 3b. Check daily limit
        daily_usage = self._get_daily_usage()
        daily_limit = self._get_daily_limit()
        if daily_usage >= daily_limit:
            self.logger.warning(
                "Daily limit reached (%d/%d) for user %s — skipping",
                daily_usage, daily_limit, self.user_id,
            )
            return {
                "processed": 0,
                "message": f"Daily limit reached ({daily_usage}/{daily_limit})",
                "daily_limit_reached": True,
            }

        # Cap emails to process within remaining daily quota
        remaining = daily_limit - daily_usage
        if len(emails) > remaining:
            emails = emails[:remaining]
            self.logger.info("Capping to %d emails (daily limit)", remaining)

        # 4. Smart pre-filtering: skip emails that don't need AI
        filtered_emails = self._pre_filter(emails, service, processed_label_id)
        self.logger.info(
            "Pre-filter: %d/%d emails need AI processing",
            len(filtered_emails), len(emails),
        )

        # 5. Get agent for this user
        agent = self._get_agent()

        # 6. Process emails concurrently (up to _MAX_CONCURRENT at a time)
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

        async def _process_one(email: dict) -> dict:
            async with semaphore:
                try:
                    decision = await agent.process_email(self.user_id, email)
                    action_result = await self._execute(service, email, decision)
                    self._log(email, decision, action_result)

                    # Auto-create/update contact record
                    self._upsert_contact(email)

                    # Mark as processed to prevent duplicate processing
                    msg_id = email.get("id", "")
                    if msg_id and processed_label_id:
                        self._add_label(service, msg_id, processed_label_id)

                    return {
                        "email_from": email.get("from", email.get("sender", "")),
                        "subject": email.get("subject", ""),
                        "action": decision.get("action", "unknown"),
                        "provider": decision.get("provider", "unknown"),
                        "model": decision.get("model", "unknown"),
                        "status": action_result.get("status", "processed"),
                        "ok": True,
                    }
                except Exception as exc:
                    self.logger.error("Email processing failed: %s", exc)
                    return {
                        "email_from": email.get("from", ""),
                        "error": str(exc),
                        "ok": False,
                    }

        results = await asyncio.gather(*[_process_one(e) for e in filtered_emails])
        processed = sum(1 for r in results if r.get("ok"))

        # 7. Update agent status
        self._update_status(processed)

        return {"processed": processed, "total": len(emails), "results": list(results)}

    def _get_auto_send(self) -> bool:
        """Check if auto-send is enabled.

        Logic:
        - trial: always draft (auto-send disabled)
        - tier1+: respect user's auto_send setting
        - Default: ON for tier2+, OFF for tier1
        """
        try:
            db = SessionLocal()
            try:
                row = db.execute(
                    text(
                        "SELECT tier, config FROM user_agents WHERE user_id = :uid LIMIT 1"
                    ),
                    {"uid": self.user_id},
                ).fetchone()
                if row:
                    tier = row[0] or "trial"
                    config = row[1] or {}
                    # Trial users always draft — never auto-send
                    if tier == "trial":
                        return False
                    # If user explicitly set auto_send, respect it
                    if isinstance(config, dict) and "auto_send" in config:
                        return bool(config["auto_send"])
                    # Default: True for tier2+, False for tier1
                    return tier in ("tier2", "tier3")
            finally:
                db.close()
        except Exception as exc:
            self.logger.warning("Could not check auto_send: %s", exc)
        return False

    def _validate_reply(self, reply_text: str) -> bool:
        """Validate reply text before auto-sending.

        Returns True if the reply is safe to send automatically.
        """
        if not reply_text or not reply_text.strip():
            return False
        # Check for placeholder/template text
        placeholders = [
            "[your name]", "[name]", "[company]", "[insert",
            "{{", "}}", "[placeholder", "[TODO", "[FILL",
            "PLACEHOLDER", "INSERT_HERE",
        ]
        lower = reply_text.lower()
        for p in placeholders:
            if p.lower() in lower:
                self.logger.warning("Reply contains placeholder '%s' — creating draft instead", p)
                return False
        # Minimum length check
        if len(reply_text.strip()) < 10:
            self.logger.warning("Reply too short (%d chars) — creating draft instead", len(reply_text.strip()))
            return False
        return True

    def _get_daily_usage(self) -> int:
        """Get today's email processing count for this user."""
        try:
            db = SessionLocal()
            try:
                row = db.execute(
                    text("""
                        SELECT COUNT(*) FROM action_logs
                        WHERE user_id = :uid
                          AND timestamp::date = CURRENT_DATE
                    """),
                    {"uid": self.user_id},
                ).fetchone()
                return row[0] if row else 0
            finally:
                db.close()
        except Exception:
            return 0

    def _get_daily_limit(self) -> int:
        """Get daily email limit based on user's tier."""
        limits = {
            "trial": 100,
            "tier1": 500,
            "tier2": 2000,
            "tier3": 10000,
        }
        try:
            db = SessionLocal()
            try:
                row = db.execute(
                    text("SELECT tier FROM user_agents WHERE user_id = :uid LIMIT 1"),
                    {"uid": self.user_id},
                ).fetchone()
                tier = row[0] if row else "trial"
                return limits.get(tier, 100)
            finally:
                db.close()
        except Exception:
            return 100

    def _pre_filter(
        self,
        emails: list[dict],
        service: Any,
        processed_label_id: str | None,
    ) -> list[dict]:
        """Pre-filter emails before sending to AI.

        Skips:
        - Already processed emails (HireAI-Processed label)
        - Blocked senders (blacklist)
        - Blocked keywords in subject/body
        - Noreply/automated senders (archived silently)

        Returns only emails that need AI classification.
        """
        blocked_senders = self._get_blocked_senders()
        blocked_keywords = self._get_blocked_keywords()

        noreply_patterns = [
            "noreply", "no-reply", "do-not-reply", "donotreply",
            "automated", "mailer-daemon", "notification", "alerts",
            "system", "postmaster", "bounce",
        ]

        filtered = []
        for email in emails:
            sender = email.get("sender", {})
            sender_email = (
                sender.get("email", "unknown")
                if isinstance(sender, dict)
                else str(sender)
            ).lower()
            subject = (email.get("subject", "") or "").lower()
            body = (email.get("snippet", "") or email.get("body", "") or "").lower()
            msg_id = email.get("id", "")

            # Skip noreply senders — archive silently
            if any(p in sender_email for p in noreply_patterns):
                self.logger.debug("Pre-filter: skipping noreply sender %s", sender_email)
                if service and msg_id:
                    try:
                        standalone_mark_as_read(service, msg_id)
                        if processed_label_id:
                            self._add_label(service, msg_id, processed_label_id)
                    except Exception:
                        pass
                continue

            # Skip blocked senders
            if sender_email in blocked_senders:
                self.logger.info("Pre-filter: blocked sender %s", sender_email)
                if service and msg_id:
                    try:
                        standalone_mark_as_read(service, msg_id)
                        if processed_label_id:
                            self._add_label(service, msg_id, processed_label_id)
                    except Exception:
                        pass
                continue

            # Skip blocked keywords
            skip = False
            for kw in blocked_keywords:
                if kw in subject or kw in body:
                    self.logger.info("Pre-filter: blocked keyword '%s' in email from %s", kw, sender_email)
                    if service and msg_id:
                        try:
                            standalone_mark_as_read(service, msg_id)
                            if processed_label_id:
                                self._add_label(service, msg_id, processed_label_id)
                        except Exception:
                            pass
                    skip = True
                    break
            if skip:
                continue

            filtered.append(email)

        return filtered

    def _get_blocked_senders(self) -> set[str]:
        """Get set of blocked sender emails from user config."""
        try:
            db = SessionLocal()
            try:
                row = db.execute(
                    text("SELECT config FROM user_agents WHERE user_id = :uid LIMIT 1"),
                    {"uid": self.user_id},
                ).fetchone()
                if row and row[0]:
                    config = row[0] if isinstance(row[0], dict) else {}
                    # Support both comma-separated string and list
                    bl = config.get("blacklist_emails", []) or config.get("blacklist", "")
                    if isinstance(bl, str):
                        return {e.strip().lower() for e in bl.split(",") if e.strip()}
                    if isinstance(bl, list):
                        return {e.strip().lower() for e in bl if e.strip()}
            finally:
                db.close()
        except Exception:
            pass
        return set()

    def _get_blocked_keywords(self) -> set[str]:
        """Get set of blocked keywords from user config."""
        try:
            db = SessionLocal()
            try:
                row = db.execute(
                    text("SELECT config FROM user_agents WHERE user_id = :uid LIMIT 1"),
                    {"uid": self.user_id},
                ).fetchone()
                if row and row[0]:
                    config = row[0] if isinstance(row[0], dict) else {}
                    bk = config.get("blocked_keywords", "")
                    if isinstance(bk, str):
                        return {k.strip().lower() for k in bk.split(",") if k.strip()}
                    if isinstance(bk, list):
                        return {k.strip().lower() for k in bk if k.strip()}
            finally:
                db.close()
        except Exception:
            pass
        return set()

    def _ensure_label(self, service: Any, label_name: str) -> str | None:
        """Get or create a Gmail label, return its ID."""
        try:
            results = service.users().labels().list(userId="me").execute()
            for lbl in results.get("labels", []):
                if lbl["name"] == label_name:
                    return lbl["id"]
            # Create the label
            body = {
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            created = service.users().labels().create(userId="me", body=body).execute()
            return created.get("id")
        except Exception as exc:
            self.logger.warning("Could not ensure label '%s': %s", label_name, exc)
            return None

    def _add_label(self, service: Any, message_id: str, label_id: str) -> None:
        """Add a label to a Gmail message."""
        try:
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"addLabelIds": [label_id]},
            ).execute()
        except Exception as exc:
            self.logger.warning("Could not add label to %s: %s", message_id, exc)

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

        # Auto-send: tier2+ defaults to True unless user disabled it
        auto_send = self._get_auto_send()
        if action == "AUTO_REPLY" and not auto_send:
            action = "DRAFT_REPLY"

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

        # Never reply to noreply/automated senders
        noreply_patterns = [
            "noreply", "no-reply", "do-not-reply", "donotreply",
            "automated", "mailer-daemon", "notification", "alerts",
            "system", "postmaster", "bounce",
        ]
        sender_lower = sender_email.lower()
        if any(p in sender_lower for p in noreply_patterns):
            self.logger.info("Skipping reply to noreply sender: %s", sender_email)
            if service and message_id:
                standalone_mark_as_read(service, message_id)
            return {"status": "archived", "action": "noreply_archived"}

        if action == "AUTO_REPLY":
            # Validate reply before auto-sending
            if reply_text and self._validate_reply(reply_text) and service:
                self.logger.info("Auto-sending reply to %s", sender_email)
                sent = standalone_reply_to_email(service, message_id, reply_text)
                if sent:
                    standalone_mark_as_read(service, message_id)
                    return {
                        "status": "sent",
                        "action": "auto_replied",
                        "sent_at": datetime.now(timezone.utc).isoformat(),
                        "reply_content": reply_text,
                    }
            # Fallback to draft if validation fails or send fails
            if service:
                self.logger.info("Creating draft for %s (auto-send validation failed or disabled)", sender_email)
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

    def _log(
        self,
        email: dict[str, Any],
        decision: dict[str, Any],
        action_result: dict[str, str] | None = None,
    ) -> None:
        """Log action to action_logs table.

        Args:
            email: The email dict.
            decision: The AI decision dict.
            action_result: Result from _execute (status, sent_at, reply_content).
        """
        action_result = action_result or {}
        sender = email.get("sender", {})
        sender_email = (
            sender.get("email", email.get("from", "unknown"))
            if isinstance(sender, dict)
            else str(sender)
        )

        outcome = action_result.get("status", "processed")

        try:
            db = SessionLocal()
            try:
                db.execute(
                    text("""
                        INSERT INTO action_logs
                            (user_id, email_from, action_taken, tool_used, outcome, metadata, timestamp)
                        VALUES
                            (:uid, :from_addr, :action, :tool, :outcome, CAST(:meta AS jsonb), NOW())
                    """),
                    {
                        "uid": self.user_id,
                        "from_addr": sender_email,
                        "action": decision.get("action", "unknown"),
                        "tool": f"{decision.get('provider', 'unknown')}/{decision.get('model', 'unknown')}",
                        "outcome": outcome,
                        "meta": json.dumps({
                            "subject": email.get("subject", ""),
                            "body": email.get("snippet", "") or email.get("body", ""),
                            "from_name": email.get("sender_name", "") or email.get("from", "").split("@")[0],
                            "category": decision.get("category", ""),
                            "agent_response": decision.get("ai_response", ""),
                            "provider": decision.get("provider", ""),
                            "model": decision.get("model", ""),
                            "user_id": self.user_id,
                            "sent_at": action_result.get("sent_at", ""),
                            "reply_content": action_result.get("reply_content", ""),
                        }),
                    },
                )
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            self.logger.error("Failed to log action: %s", exc)

    def _upsert_contact(self, email: dict) -> None:
        """Create or update a contact record from email sender.

        Extracts name, email, company from the sender and upserts
        into the contacts table, updating last_contact_date and
        incrementing total_emails.
        """
        try:
            sender = email.get("sender", {})
            if isinstance(sender, dict):
                sender_email = sender.get("email", "").lower().strip()
                sender_name = sender.get("name", "")
            else:
                sender_email = str(sender).lower().strip()
                sender_name = ""

            if not sender_email or sender_email == "unknown":
                return

            # Try to extract company from domain
            company = ""
            domain = sender_email.split("@")[-1] if "@" in sender_email else ""
            if domain and domain not in (
                "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
                "live.com", "icloud.com", "aol.com", "protonmail.com",
            ):
                company = domain.split(".")[0].title()

            db = SessionLocal()
            try:
                # Check if contact exists
                existing = db.execute(
                    text("SELECT id, total_emails FROM contacts WHERE user_id = :uid AND email = :email LIMIT 1"),
                    {"uid": self.user_id, "email": sender_email},
                ).fetchone()

                if existing:
                    # Update existing contact
                    db.execute(
                        text("""
                            UPDATE contacts
                            SET last_contact_date = NOW(),
                                total_emails = total_emails + 1,
                                updated_at = NOW(),
                                name = COALESCE(NULLIF(:name, ''), name),
                                company = COALESCE(NULLIF(:company, ''), company)
                            WHERE id = :cid
                        """),
                        {"cid": existing[0], "name": sender_name, "company": company},
                    )
                else:
                    # Create new contact
                    db.execute(
                        text("""
                            INSERT INTO contacts (user_id, email, name, company, total_emails,
                                                  first_contact_date, last_contact_date)
                            VALUES (:uid, :email, :name, :company, 1, NOW(), NOW())
                        """),
                        {
                            "uid": self.user_id,
                            "email": sender_email,
                            "name": sender_name,
                            "company": company,
                        },
                    )

                db.commit()
            finally:
                db.close()
        except Exception as exc:
            self.logger.debug("Contact upsert failed (non-critical): %s", exc)

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
