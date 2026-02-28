"""Unit tests for all GmailMind tools.

Covers:
  - 6 Gmail tools (read, send, reply, label, search, draft)
  - 2 Calendar tools (availability, create event)
  - 2 CRM tools (get contact, update)
  - 1 Alert tool (escalation)
  - Memory read/write operations

All external APIs are mocked — no network calls are made.
"""

import base64
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from models.gmail_models import Email, EmailAddress, SendEmailResponse, DraftResponse, LabelResult
from models.tool_models import (
    CalendarEventResponse,
    ContactProfile,
    CrmUpdateResponse,
    EscalationAlertResponse,
    FreeSlot,
    FollowUpScheduleResponse,
)


# ============================================================================
# Fixtures
# ============================================================================

def _make_gmail_message(
    msg_id="msg_001",
    thread_id="thr_001",
    subject="Hello",
    from_addr="alice@example.com",
    from_name="Alice",
    body_text="Hi there!",
    labels=None,
):
    """Build a fake Gmail API message resource."""
    raw_body = base64.urlsafe_b64encode(body_text.encode()).decode()
    return {
        "id": msg_id,
        "threadId": thread_id,
        "snippet": body_text[:50],
        "labelIds": labels or ["INBOX", "UNREAD"],
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": f"{from_name} <{from_addr}>"},
                {"name": "To", "value": "owner@business.com"},
                {"name": "Subject", "value": subject},
                {"name": "Date", "value": "Mon, 1 Jan 2026 10:00:00 +0000"},
                {"name": "Message-Id", "value": f"<{msg_id}@mail.gmail.com>"},
            ],
            "body": {"data": raw_body},
        },
    }


def _mock_gmail_service(messages=None, thread_messages=None):
    """Create a mock Gmail service with chained method calls."""
    svc = MagicMock()

    # messages().list()
    list_response = {"messages": [{"id": m["id"]} for m in (messages or [])]}
    svc.users().messages().list.return_value.execute.return_value = list_response

    # messages().get() — return the right message by id
    msg_map = {m["id"]: m for m in (messages or [])}

    def get_message(userId, id, format="full"):
        mock = MagicMock()
        mock.execute.return_value = msg_map.get(id, messages[0] if messages else {})
        return mock

    svc.users().messages().get = get_message

    # messages().send()
    svc.users().messages().send.return_value.execute.return_value = {
        "id": "sent_001",
        "threadId": "thr_001",
    }

    # messages().modify()
    svc.users().messages().modify.return_value.execute.return_value = {}

    # drafts().create()
    svc.users().drafts().create.return_value.execute.return_value = {
        "id": "draft_001",
        "message": {"id": "draft_msg_001"},
    }

    # threads().get()
    svc.users().threads().get.return_value.execute.return_value = {
        "messages": thread_messages or messages or [],
    }

    return svc


def _mock_calendar_service(busy_periods=None):
    """Create a mock Calendar service."""
    svc = MagicMock()

    freebusy_result = {
        "calendars": {
            "primary": {
                "busy": busy_periods or [],
            }
        }
    }
    svc.freebusy().query.return_value.execute.return_value = freebusy_result

    svc.events().insert.return_value.execute.return_value = {
        "id": "evt_001",
        "htmlLink": "https://calendar.google.com/event?id=evt_001",
        "status": "confirmed",
    }

    return svc


# ============================================================================
# Gmail Tools Tests
# ============================================================================


class TestReadEmails:
    def test_returns_email_list(self):
        from tools.gmail_tools import read_emails

        msg = _make_gmail_message()
        svc = _mock_gmail_service(messages=[msg])

        result = read_emails(svc, max_results=5)

        assert len(result) == 1
        assert isinstance(result[0], Email)
        assert result[0].id == "msg_001"
        assert result[0].subject == "Hello"
        assert result[0].sender.email == "alice@example.com"

    def test_empty_inbox(self):
        from tools.gmail_tools import read_emails

        svc = MagicMock()
        svc.users().messages().list.return_value.execute.return_value = {"messages": []}

        result = read_emails(svc)
        assert result == []

    def test_unread_flag(self):
        from tools.gmail_tools import read_emails

        msg = _make_gmail_message(labels=["INBOX", "UNREAD"])
        svc = _mock_gmail_service(messages=[msg])

        result = read_emails(svc)
        assert result[0].is_read is False

    def test_read_flag(self):
        from tools.gmail_tools import read_emails

        msg = _make_gmail_message(labels=["INBOX"])
        svc = _mock_gmail_service(messages=[msg])

        result = read_emails(svc)
        assert result[0].is_read is True


class TestSendEmail:
    def test_sends_successfully(self):
        from tools.gmail_tools import send_email

        svc = _mock_gmail_service()

        result = send_email(svc, to="bob@example.com", subject="Test", body="Hello Bob")

        assert isinstance(result, SendEmailResponse)
        assert result.message_id == "sent_001"
        assert result.status == "sent"

    def test_with_thread_id(self):
        from tools.gmail_tools import send_email

        svc = _mock_gmail_service()

        result = send_email(
            svc, to="bob@example.com", subject="Re: Test",
            body="Follow-up", reply_to_thread_id="thr_001",
        )

        assert result.thread_id == "thr_001"


class TestReplyToEmail:
    def test_replies_to_thread(self):
        from tools.gmail_tools import reply_to_email

        msg = _make_gmail_message()
        svc = _mock_gmail_service(messages=[msg])

        result = reply_to_email(svc, thread_id="thr_001", body="Thanks!")

        assert isinstance(result, SendEmailResponse)
        assert result.message_id == "sent_001"

    def test_empty_thread_raises(self):
        from tools.gmail_tools import reply_to_email

        svc = MagicMock()
        svc.users().threads().get.return_value.execute.return_value = {"messages": []}

        with pytest.raises(ValueError, match="contains no messages"):
            reply_to_email(svc, thread_id="thr_empty", body="Hello?")


class TestLabelEmail:
    def test_labels_added(self):
        from tools.gmail_tools import label_email

        svc = _mock_gmail_service()

        result = label_email(svc, email_id="msg_001", labels=["IMPORTANT", "Lead"])

        assert isinstance(result, LabelResult)
        assert result.success is True
        assert result.labels_added == ["IMPORTANT", "Lead"]
        assert result.archived is False

    def test_archive(self):
        from tools.gmail_tools import label_email

        svc = _mock_gmail_service()

        result = label_email(svc, email_id="msg_001", labels=["Processed"], archive=True)

        assert result.archived is True
        assert result.labels_removed == ["INBOX"]


class TestSearchEmails:
    def test_returns_results(self):
        from tools.gmail_tools import search_emails

        msg = _make_gmail_message(subject="Meeting tomorrow")
        svc = _mock_gmail_service(messages=[msg])

        result = search_emails(svc, query="subject:meeting", max_results=5)

        assert len(result) == 1
        assert result[0].subject == "Meeting tomorrow"

    def test_no_results(self):
        from tools.gmail_tools import search_emails

        svc = MagicMock()
        svc.users().messages().list.return_value.execute.return_value = {"messages": []}

        result = search_emails(svc, query="from:nonexistent")
        assert result == []


class TestCreateDraft:
    def test_creates_draft(self):
        from tools.gmail_tools import create_draft

        svc = _mock_gmail_service()

        result = create_draft(svc, to="bob@example.com", subject="Draft", body="Review this")

        assert isinstance(result, DraftResponse)
        assert result.draft_id == "draft_001"
        assert result.status == "created"


# ============================================================================
# Calendar Tools Tests
# ============================================================================


class TestCheckCalendarAvailability:
    def test_all_free(self):
        from tools.calendar_tools import check_calendar_availability

        svc = _mock_calendar_service(busy_periods=[])
        start = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 1, 17, 0, tzinfo=timezone.utc)

        result = check_calendar_availability(svc, start, end, slot_duration_minutes=30)

        assert len(result) == 1
        assert isinstance(result[0], FreeSlot)
        assert result[0].duration_minutes == 480  # 8 hours

    def test_with_busy_periods(self):
        from tools.calendar_tools import check_calendar_availability

        busy = [
            {"start": "2026-03-01T10:00:00+00:00", "end": "2026-03-01T11:00:00+00:00"},
            {"start": "2026-03-01T14:00:00+00:00", "end": "2026-03-01T15:00:00+00:00"},
        ]
        svc = _mock_calendar_service(busy_periods=busy)
        start = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 1, 17, 0, tzinfo=timezone.utc)

        result = check_calendar_availability(svc, start, end, slot_duration_minutes=30)

        # Expect: 9-10, 11-14, 15-17 = 3 slots
        assert len(result) == 3

    def test_short_gaps_filtered(self):
        from tools.calendar_tools import check_calendar_availability

        busy = [
            {"start": "2026-03-01T09:00:00+00:00", "end": "2026-03-01T09:20:00+00:00"},
        ]
        svc = _mock_calendar_service(busy_periods=busy)
        start = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 1, 9, 30, tzinfo=timezone.utc)

        # Gap is only 10 minutes, min is 30
        result = check_calendar_availability(svc, start, end, slot_duration_minutes=30)
        assert len(result) == 0


class TestCreateCalendarEvent:
    def test_creates_event(self):
        from tools.calendar_tools import create_calendar_event

        svc = _mock_calendar_service()
        start = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 1, 11, 0, tzinfo=timezone.utc)

        result = create_calendar_event(svc, title="Team Standup", start_time=start, end_time=end)

        assert isinstance(result, CalendarEventResponse)
        assert result.event_id == "evt_001"
        assert result.status == "confirmed"

    def test_with_attendees(self):
        from tools.calendar_tools import create_calendar_event

        svc = _mock_calendar_service()
        start = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 1, 11, 0, tzinfo=timezone.utc)

        result = create_calendar_event(
            svc, title="Meeting",
            start_time=start, end_time=end,
            attendees=["alice@example.com", "bob@example.com"],
        )

        assert result.event_id == "evt_001"


# ============================================================================
# CRM Tools Tests
# ============================================================================


class TestGetCrmContact:
    @patch("tools.crm_tools._hubspot_configured", return_value=False)
    @patch("tools.crm_tools.get_sender_memory")
    def test_local_fallback_found(self, mock_memory, mock_hub):
        from tools.crm_tools import get_crm_contact

        profile = MagicMock()
        profile.email = "alice@example.com"
        profile.name = "Alice"
        profile.company = "Acme"
        profile.last_interaction = datetime(2026, 1, 1, tzinfo=timezone.utc)
        profile.tags = ["client"]
        mock_memory.return_value = profile

        result = get_crm_contact("alice@example.com")

        assert isinstance(result, ContactProfile)
        assert result.email == "alice@example.com"
        assert result.source == "local"

    @patch("tools.crm_tools._hubspot_configured", return_value=False)
    @patch("tools.crm_tools.get_sender_memory", return_value=None)
    def test_local_not_found(self, mock_memory, mock_hub):
        from tools.crm_tools import get_crm_contact

        result = get_crm_contact("unknown@example.com")
        assert result is None

    @patch("tools.crm_tools._hubspot_configured", return_value=True)
    @patch("tools.crm_tools.HUBSPOT_API_KEY", "test-key")
    @patch("tools.crm_tools.HUBSPOT_BASE_URL", "https://api.hubapi.com")
    @patch("tools.crm_tools.httpx.Client")
    def test_hubspot_found(self, mock_client_cls, mock_hub):
        from tools.crm_tools import get_crm_contact

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": [{
                "properties": {
                    "email": "bob@corp.com",
                    "firstname": "Bob",
                    "lastname": "Smith",
                    "company": "Corp Inc",
                }
            }]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(
            post=MagicMock(return_value=mock_resp)
        ))
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = get_crm_contact("bob@corp.com")

        assert isinstance(result, ContactProfile)
        assert result.source == "hubspot"


class TestUpdateCrm:
    @patch("tools.crm_tools._hubspot_configured", return_value=False)
    @patch("tools.crm_tools.update_sender_memory")
    def test_local_update(self, mock_update, mock_hub):
        from tools.crm_tools import update_crm

        result = update_crm("alice@example.com", "note_added", {"note": "Called client"})

        assert isinstance(result, CrmUpdateResponse)
        assert result.success is True
        assert result.source == "local"
        mock_update.assert_called_once()


# ============================================================================
# Alert Tools Tests
# ============================================================================


class TestSendEscalationAlert:
    @patch("tools.alert_tools._slack_configured", return_value=False)
    def test_slack_not_configured(self, mock_cfg):
        from tools.alert_tools import send_escalation_alert

        result = send_escalation_alert("slack", "Help!", "high")

        assert isinstance(result, EscalationAlertResponse)
        assert result.success is False
        assert "not configured" in result.reason

    @patch("tools.alert_tools._twilio_configured", return_value=False)
    def test_whatsapp_not_configured(self, mock_cfg):
        from tools.alert_tools import send_escalation_alert

        result = send_escalation_alert("whatsapp", "Help!", "critical")

        assert result.success is False
        assert "not configured" in result.reason

    def test_unsupported_channel(self):
        from tools.alert_tools import send_escalation_alert

        result = send_escalation_alert("telegram", "Hello", "low")

        assert result.success is False
        assert "Unsupported channel" in result.reason

    @patch("tools.alert_tools.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    @patch("tools.alert_tools._slack_configured", return_value=True)
    @patch("tools.alert_tools.httpx.Client")
    def test_slack_success(self, mock_client_cls, mock_cfg):
        from tools.alert_tools import send_escalation_alert

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(
            post=MagicMock(return_value=mock_resp)
        ))
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = send_escalation_alert("slack", "Test alert", "high")

        assert result.success is True
        assert result.channel == "slack"


# ============================================================================
# Memory Operations Tests
# ============================================================================


class TestShortTermMemory:
    def test_add_and_get_email(self):
        from memory.short_term import ShortTermMemory

        mem = ShortTermMemory()
        mem.add_email("msg_001", {"subject": "Hello", "sender": "alice@test.com"})

        got = mem.get_email("msg_001")
        assert got is not None
        assert got["subject"] == "Hello"
        assert "seen_at" in got

    def test_unknown_email_returns_none(self):
        from memory.short_term import ShortTermMemory

        mem = ShortTermMemory()
        assert mem.get_email("nonexistent") is None

    def test_log_action(self):
        from memory.short_term import ShortTermMemory

        mem = ShortTermMemory()
        mem.log_action("send_email", "Sent email to bob")
        mem.log_action("label_email", "Labeled as Lead")

        assert mem.action_count() == 2
        actions = mem.get_actions()
        assert actions[0]["tool_used"] == "send_email"
        assert actions[1]["tool_used"] == "label_email"

    def test_escalation(self):
        from memory.short_term import ShortTermMemory

        mem = ShortTermMemory()
        mem.add_escalation("msg_005", "Legal threat detected", urgency="critical")

        assert mem.escalation_count() == 1
        esc = mem.get_escalations()[0]
        assert esc["email_id"] == "msg_005"
        assert esc["reason"] == "Legal threat detected"

    def test_reset(self):
        from memory.short_term import ShortTermMemory

        mem = ShortTermMemory()
        mem.add_email("msg_001", {"subject": "Test"})
        mem.log_action("read_emails", "Read 1")
        mem.add_escalation("msg_001", "Test")

        mem.reset()

        assert mem.action_count() == 0
        assert mem.escalation_count() == 0
        assert mem.list_session_emails() == []

    def test_summary(self):
        from memory.short_term import ShortTermMemory

        mem = ShortTermMemory()
        mem.add_email("msg_001", {"subject": "A"})
        mem.add_email("msg_002", {"subject": "B"})
        mem.log_action("read_emails", "Read 2")

        s = mem.summary()
        assert s["emails_seen"] == 2
        assert s["actions_taken"] == 1
        assert s["pending_escalations"] == 0


# ============================================================================
# Gmail Helpers Tests
# ============================================================================


class TestGmailHelpers:
    def test_parse_email_address_with_name(self):
        from tools.gmail_tools import _parse_email_address

        result = _parse_email_address('John Doe <john@example.com>')
        assert result.email == "john@example.com"
        assert result.name == "John Doe"

    def test_parse_email_address_plain(self):
        from tools.gmail_tools import _parse_email_address

        result = _parse_email_address("john@example.com")
        assert result.email == "john@example.com"
        assert result.name is None

    def test_decode_body_plain(self):
        from tools.gmail_tools import _decode_body

        raw = base64.urlsafe_b64encode(b"Hello World").decode()
        payload = {"mimeType": "text/plain", "body": {"data": raw}}

        assert _decode_body(payload) == "Hello World"

    def test_decode_body_multipart(self):
        from tools.gmail_tools import _decode_body

        raw = base64.urlsafe_b64encode(b"Inner text").decode()
        payload = {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/plain", "body": {"data": raw}},
                {"mimeType": "text/html", "body": {"data": "ignored"}},
            ],
        }

        assert _decode_body(payload) == "Inner text"

    def test_get_header(self):
        from tools.gmail_tools import _get_header

        headers = [
            {"name": "Subject", "value": "Hello"},
            {"name": "From", "value": "alice@test.com"},
        ]

        assert _get_header(headers, "subject") == "Hello"
        assert _get_header(headers, "FROM") == "alice@test.com"
        assert _get_header(headers, "X-Missing") == ""
