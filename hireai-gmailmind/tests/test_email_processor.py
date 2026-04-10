"""Tests for the EmailProcessor pipeline (agent/email_processor.py).

Covers:
  - process_inbox: no Gmail, no emails, success path
  - _execute: AUTO_REPLY, DRAFT_REPLY, ESCALATE, LABEL_ARCHIVE
  - _extract_reply: parsing AI response text
  - _log: action logging (mocked DB)
  - _update_status: agent status update (mocked DB)
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from agent.email_processor import EmailProcessor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_processor(user_id="test_user"):
    """Create an EmailProcessor instance."""
    return EmailProcessor(user_id)


# ============================================================================
# _extract_reply
# ============================================================================


class TestExtractReply:
    def test_reply_with_reason(self):
        p = _make_processor()
        text = "ACTION: AUTO_REPLY\nREPLY: Thanks for your email!\nREASON: Standard inquiry."
        assert p._extract_reply(text) == "Thanks for your email!"

    def test_reply_multiline(self):
        p = _make_processor()
        text = "ACTION: DRAFT_REPLY\nREPLY: Hello,\nWe received your request.\nThanks.\nREASON: Polite."
        reply = p._extract_reply(text)
        assert "Hello," in reply
        assert "We received your request." in reply

    def test_no_reply_marker(self):
        p = _make_processor()
        text = "I think we should respond politely."
        assert p._extract_reply(text) == text.strip()

    def test_empty_response(self):
        p = _make_processor()
        assert p._extract_reply("") == ""

    def test_reply_at_end_of_string(self):
        p = _make_processor()
        text = "ACTION: AUTO_REPLY\nREPLY: Thank you for reaching out."
        assert p._extract_reply(text) == "Thank you for reaching out."


# ============================================================================
# _execute
# ============================================================================


class TestExecuteAction:
    def test_auto_reply_success(self):
        p = _make_processor()
        service = MagicMock()

        with patch("agent.email_processor.standalone_reply_to_email", return_value=True) as mock_reply, \
             patch("agent.email_processor.standalone_mark_as_read") as mock_read, \
             patch.object(p, "_get_auto_send", return_value=True):
            decision = {
                "action": "AUTO_REPLY",
                "ai_response": "REPLY: Thank you for reaching out! We will get back to you shortly.\nREASON: Quick response.",
            }
            email = {"id": "msg_1", "subject": "Hello", "sender": {"email": "a@b.com"}}

            result = _run(p._execute(service, email, decision))

            assert result["action"] == "auto_replied"
            assert result["status"] == "sent"
            mock_reply.assert_called_once()
            mock_read.assert_called_once()

    def test_auto_reply_fallback_to_draft(self):
        p = _make_processor()
        service = MagicMock()

        with patch("agent.email_processor.standalone_reply_to_email", return_value=False), \
             patch("agent.email_processor.standalone_create_draft") as mock_draft, \
             patch.object(p, "_get_auto_send", return_value=True):
            decision = {
                "action": "AUTO_REPLY",
                "ai_response": "REPLY: Hello!\nREASON: test",
            }
            email = {"id": "msg_2", "subject": "Test", "sender": {"email": "x@y.com"}}

            result = _run(p._execute(service, email, decision))

            assert result["action"] == "draft_created"
            mock_draft.assert_called_once()

    def test_draft_reply(self):
        p = _make_processor()
        service = MagicMock()

        with patch("agent.email_processor.standalone_create_draft") as mock_draft, \
             patch.object(p, "_get_auto_send", return_value=False):
            decision = {
                "action": "DRAFT_REPLY",
                "ai_response": "REPLY: I'll get back to you.\nREASON: Need review.",
            }
            email = {"id": "msg_3", "subject": "Question", "sender": {"email": "q@r.com"}}

            result = _run(p._execute(service, email, decision))

            assert result["action"] == "draft_created"
            assert result["status"] == "drafted"
            mock_draft.assert_called_once()

    def test_escalate(self):
        p = _make_processor()
        service = MagicMock()

        with patch.object(p, "_get_auto_send", return_value=False):
            decision = {"action": "ESCALATE", "ai_response": "REASON: Legal threat."}
            email = {"id": "msg_4", "subject": "Legal", "sender": {"email": "l@l.com"}}

            result = _run(p._execute(service, email, decision))

        assert result["action"] == "escalated"
        assert result["status"] == "escalated"

    def test_label_archive(self):
        p = _make_processor()
        service = MagicMock()

        with patch("agent.email_processor.standalone_label_email") as mock_label, \
             patch("agent.email_processor.standalone_mark_as_read") as mock_read, \
             patch.object(p, "_get_auto_send", return_value=False):
            decision = {
                "action": "LABEL_ARCHIVE",
                "ai_response": "Newsletter archived.",
                "category": "newsletter",
            }
            email = {"id": "msg_5", "subject": "Newsletter", "sender": {"email": "n@n.com"}}

            result = _run(p._execute(service, email, decision))

            assert result["action"] == "labeled_archived"
            assert result["status"] == "archived"
            mock_label.assert_called_once()
            mock_read.assert_called_once()

    def test_schedule_followup(self):
        p = _make_processor()
        service = MagicMock()

        with patch.object(p, "_get_auto_send", return_value=False):
            decision = {"action": "SCHEDULE_FOLLOWUP", "ai_response": "Follow up in 24h."}
            email = {"id": "msg_6", "subject": "Proposal", "sender": {"email": "f@f.com"}}

            result = _run(p._execute(service, email, decision))

        assert result["action"] == "followup_scheduled"

    def test_unknown_action(self):
        p = _make_processor()
        service = MagicMock()

        with patch.object(p, "_get_auto_send", return_value=False):
            decision = {"action": "UNKNOWN", "ai_response": "?"}
            email = {"id": "msg_7", "subject": "?", "sender": {"email": "u@u.com"}}

            result = _run(p._execute(service, email, decision))

        assert result["action"] == "no_action"
        assert result["status"] == "skipped"

    def test_sender_as_string(self):
        """Sender can be a plain string instead of dict."""
        p = _make_processor()
        service = MagicMock()

        with patch("agent.email_processor.standalone_create_draft"), \
             patch.object(p, "_get_auto_send", return_value=False):
            decision = {"action": "DRAFT_REPLY", "ai_response": "REPLY: Hi."}
            email = {"id": "msg_8", "subject": "Test", "sender": "plain@email.com"}

            result = _run(p._execute(service, email, decision))
            assert result["status"] == "drafted"


# ============================================================================
# _log (mocked DB)
# ============================================================================


class TestLog:
    @patch("agent.email_processor.SessionLocal")
    def test_log_inserts_to_db(self, mock_session_cls):
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        p = _make_processor("user_log")
        email = {"id": "msg_log", "subject": "Test", "sender": {"email": "log@test.com"}}
        decision = {
            "action": "AUTO_REPLY",
            "provider": "claude",
            "model": "claude-haiku-4-5-20251001",
            "category": "inquiry",
        }

        p._log(email, decision)

        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("agent.email_processor.SessionLocal")
    def test_log_handles_db_error(self, mock_session_cls):
        mock_session_cls.side_effect = Exception("DB down")

        p = _make_processor("user_err")
        email = {"id": "msg_err", "subject": "Error", "sender": {"email": "err@test.com"}}
        decision = {"action": "ESCALATE"}

        # Should not raise
        p._log(email, decision)


# ============================================================================
# _update_status (mocked DB)
# ============================================================================


class TestUpdateStatus:
    @patch("agent.email_processor.SessionLocal")
    def test_update_status_success(self, mock_session_cls):
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        p = _make_processor("user_status")
        p._update_status(5)

        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("agent.email_processor.SessionLocal")
    def test_update_status_handles_error(self, mock_session_cls):
        mock_session_cls.side_effect = Exception("DB down")

        p = _make_processor("user_status_err")
        # Should not raise
        p._update_status(0)


# ============================================================================
# process_inbox (integration with mocks)
# ============================================================================


class TestValidateReply:
    def test_valid_reply(self):
        p = _make_processor()
        assert p._validate_reply("Thank you for your email. We will get back to you shortly.") is True

    def test_empty_reply(self):
        p = _make_processor()
        assert p._validate_reply("") is False
        assert p._validate_reply("   ") is False

    def test_too_short_reply(self):
        p = _make_processor()
        assert p._validate_reply("Hi") is False

    def test_placeholder_reply(self):
        p = _make_processor()
        assert p._validate_reply("Hello [your name], thank you!") is False
        assert p._validate_reply("Please INSERT_HERE your details") is False
        assert p._validate_reply("Template {{variable}} text") is False

    def test_normal_reply_passes(self):
        p = _make_processor()
        assert p._validate_reply("We received your CV and will review it shortly. Thanks!") is True


class TestDailyLimit:
    @patch("agent.email_processor.SessionLocal")
    def test_get_daily_usage(self, mock_session_cls):
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = (42,)
        mock_session_cls.return_value = mock_db

        p = _make_processor("user_usage")
        assert p._get_daily_usage() == 42

    @patch("agent.email_processor.SessionLocal")
    def test_get_daily_limit_trial(self, mock_session_cls):
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = ("trial",)
        mock_session_cls.return_value = mock_db

        p = _make_processor("user_trial")
        assert p._get_daily_limit() == 100

    @patch("agent.email_processor.SessionLocal")
    def test_get_daily_limit_tier2(self, mock_session_cls):
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = ("tier2",)
        mock_session_cls.return_value = mock_db

        p = _make_processor("user_tier2")
        assert p._get_daily_limit() == 2000


class TestProcessInbox:
    def test_no_gmail_connection(self):
        p = _make_processor("user_no_gmail")

        with patch.object(p, "_build_service", return_value=None):
            result = _run(p.process_inbox())

        assert result["processed"] == 0
        assert "error" in result
        assert "Gmail" in result["error"]

    def test_no_new_emails(self):
        p = _make_processor("user_empty")

        with patch.object(p, "_build_service", return_value=MagicMock()), \
             patch("agent.email_processor.standalone_read_emails", return_value=[]):
            result = _run(p.process_inbox())

        assert result["processed"] == 0
        assert "No new emails" in result.get("message", "")

    def test_successful_processing(self):
        p = _make_processor("user_success")

        mock_email = {
            "id": "msg_inbox_1",
            "subject": "Hello",
            "body": "How are you?",
            "from": "sender@test.com",
            "sender": {"email": "sender@test.com"},
        }

        mock_agent = MagicMock()
        mock_agent.process_email = AsyncMock(return_value={
            "action": "AUTO_REPLY",
            "ai_response": "REPLY: I'm great, thanks!",
            "provider": "claude",
            "model": "claude-haiku-4-5-20251001",
            "category": "general",
        })

        with patch.object(p, "_build_service", return_value=MagicMock()), \
             patch("agent.email_processor.standalone_read_emails", return_value=[mock_email]), \
             patch.object(p, "_get_agent", return_value=mock_agent), \
             patch.object(p, "_execute", new_callable=AsyncMock, return_value={"status": "sent", "action": "auto_replied"}), \
             patch.object(p, "_log"), \
             patch.object(p, "_update_status"), \
             patch.object(p, "_get_daily_usage", return_value=0), \
             patch.object(p, "_get_daily_limit", return_value=500):
            result = _run(p.process_inbox())

        assert result["processed"] == 1
        assert result["total"] == 1
        assert result["results"][0]["action"] == "AUTO_REPLY"
        assert result["results"][0]["provider"] == "claude"

    def test_processing_error_captured(self):
        p = _make_processor("user_error")

        mock_email = {
            "id": "msg_err",
            "from": "err@test.com",
            "subject": "Fail",
            "body": "Will fail.",
            "sender": {"email": "err@test.com"},
        }

        mock_agent = MagicMock()
        mock_agent.process_email = AsyncMock(side_effect=Exception("AI timeout"))

        with patch.object(p, "_build_service", return_value=MagicMock()), \
             patch("agent.email_processor.standalone_read_emails", return_value=[mock_email]), \
             patch.object(p, "_get_agent", return_value=mock_agent), \
             patch.object(p, "_update_status"), \
             patch.object(p, "_get_daily_usage", return_value=0), \
             patch.object(p, "_get_daily_limit", return_value=500):
            result = _run(p.process_inbox())

        assert result["processed"] == 0
        assert result["total"] == 1
        assert "error" in result["results"][0]

    def test_fetch_error_handled(self):
        p = _make_processor("user_fetch_err")

        with patch.object(p, "_build_service", return_value=MagicMock()), \
             patch("agent.email_processor.standalone_read_emails", side_effect=Exception("Gmail API error")):
            result = _run(p.process_inbox())

        assert result["processed"] == 0
        assert "error" in result

    def test_multiple_emails_processed(self):
        p = _make_processor("user_multi")

        emails = [
            {"id": f"msg_{i}", "subject": f"Email {i}", "body": "test", "from": f"u{i}@t.com", "sender": {"email": f"u{i}@t.com"}}
            for i in range(3)
        ]

        mock_agent = MagicMock()
        mock_agent.process_email = AsyncMock(return_value={
            "action": "LABEL_ARCHIVE",
            "ai_response": "Archived.",
            "provider": "claude",
            "model": "claude-sonnet-4-5-20251022",
            "category": "newsletter",
        })

        with patch.object(p, "_build_service", return_value=MagicMock()), \
             patch("agent.email_processor.standalone_read_emails", return_value=emails), \
             patch.object(p, "_get_agent", return_value=mock_agent), \
             patch.object(p, "_execute", new_callable=AsyncMock, return_value={"status": "archived", "action": "labeled_archived"}), \
             patch.object(p, "_log"), \
             patch.object(p, "_update_status"), \
             patch.object(p, "_get_daily_usage", return_value=0), \
             patch.object(p, "_get_daily_limit", return_value=500):
            result = _run(p.process_inbox())

        assert result["processed"] == 3
        assert result["total"] == 3
        assert len(result["results"]) == 3

    def test_daily_limit_reached(self):
        p = _make_processor("user_limited")

        with patch.object(p, "_build_service", return_value=MagicMock()), \
             patch("agent.email_processor.standalone_read_emails", return_value=[{"id": "m1"}]), \
             patch.object(p, "_get_daily_usage", return_value=100), \
             patch.object(p, "_get_daily_limit", return_value=100):
            result = _run(p.process_inbox())

        assert result["processed"] == 0
        assert result.get("daily_limit_reached") is True
