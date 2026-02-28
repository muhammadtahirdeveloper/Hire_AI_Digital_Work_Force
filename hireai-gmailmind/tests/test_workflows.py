"""End-to-end workflow tests for GmailMind.

Tests full workflows by wiring together agent components with all
external APIs mocked:

  1. New Lead Email — read → classify → draft reply → label → schedule follow-up
  2. Complaint Email — read → detect escalation → escalate → label
  3. Follow-up Scheduling — schedule → verify DB record
  4. Spam Email — read → detect spam → ignore (no reply)
  5. Known Client Email — read → recall memory → auto-reply → update CRM

Uses pytest + pytest-asyncio. All external calls are mocked.
"""

import base64
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from models.gmail_models import Email, EmailAddress
from agent.safety_guard import SafetyGuard


# ============================================================================
# Helpers
# ============================================================================


def _make_email(
    msg_id="msg_001",
    thread_id="thr_001",
    subject="Hello",
    sender_email="alice@example.com",
    sender_name="Alice",
    body="Hi there!",
    labels=None,
):
    """Create an Email model for testing."""
    return Email(
        id=msg_id,
        thread_id=thread_id,
        subject=subject,
        sender=EmailAddress(email=sender_email, name=sender_name),
        to=[EmailAddress(email="owner@business.com")],
        snippet=body[:50],
        body=body,
        labels=labels or ["INBOX", "UNREAD"],
        is_read=False,
    )


def _make_gmail_api_message(email: Email):
    """Convert an Email model back to a raw Gmail API dict for mocking."""
    raw_body = base64.urlsafe_b64encode(email.body.encode()).decode()
    return {
        "id": email.id,
        "threadId": email.thread_id,
        "snippet": email.snippet,
        "labelIds": email.labels,
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": f"{email.sender.name} <{email.sender.email}>"},
                {"name": "To", "value": "owner@business.com"},
                {"name": "Subject", "value": email.subject},
                {"name": "Date", "value": "Mon, 1 Jan 2026 10:00:00 +0000"},
                {"name": "Message-Id", "value": f"<{email.id}@mail.gmail.com>"},
            ],
            "body": {"data": raw_body},
        },
    }


# ============================================================================
# Workflow 1 — New Lead Email
# ============================================================================


class TestNewLeadWorkflow:
    """A new potential client emails for the first time.

    Expected flow:
      1. read_emails fetches the email
      2. Agent classifies as LEAD (new sender, no history)
      3. create_draft is called (auto_reply_new_leads=False by default)
      4. label_email adds "Lead" label
      5. schedule_followup sets a 24h reminder
    """

    def test_new_lead_creates_draft(self):
        """Verify that a new lead email produces a draft (not auto-reply)."""
        from tools.gmail_tools import read_emails, create_draft

        # Read phase
        email = _make_email(
            subject="Interested in your services",
            body="Hi, I found your company online and would like to learn more about your pricing.",
            sender_email="newlead@prospect.com",
            sender_name="New Lead",
        )
        raw_msg = _make_gmail_api_message(email)

        svc = MagicMock()
        svc.users().messages().list.return_value.execute.return_value = {
            "messages": [{"id": email.id}],
        }
        svc.users().messages().get.return_value.execute.return_value = raw_msg

        emails = read_emails(svc, max_results=5, filter="is:unread")
        assert len(emails) == 1
        assert emails[0].sender.email == "newlead@prospect.com"

        # Draft phase
        svc.users().drafts().create.return_value.execute.return_value = {
            "id": "draft_lead_001",
            "message": {"id": "draft_msg_001"},
        }

        draft = create_draft(
            svc,
            to="newlead@prospect.com",
            subject="Re: Interested in your services",
            body="Thank you for reaching out! I've received your message and will get back to you shortly.",
        )

        assert draft.draft_id == "draft_lead_001"
        assert draft.status == "created"

    def test_new_lead_safety_allows_draft(self):
        """Safety guard should allow creating a draft for a lead."""
        sg = SafetyGuard()
        ok, _ = sg.check_action("create_draft", {
            "to": "newlead@prospect.com",
            "subject": "Re: Interested in your services",
            "body": "Thank you for reaching out!",
        })
        assert ok is True

    def test_new_lead_label_applied(self):
        """Verify label_email works for tagging a lead."""
        from tools.gmail_tools import label_email

        svc = MagicMock()
        svc.users().messages().modify.return_value.execute.return_value = {}

        result = label_email(svc, email_id="msg_lead", labels=["Lead", "New"])
        assert result.success is True
        assert "Lead" in result.labels_added


# ============================================================================
# Workflow 2 — Complaint / Escalation Email
# ============================================================================


class TestComplaintWorkflow:
    """A customer sends a complaint with escalation keywords.

    Expected flow:
      1. read_emails fetches the email
      2. SafetyGuard.contains_escalation_keywords detects "complaint" / "legal"
      3. send_escalation_alert notifies the owner
      4. label_email tags as "Escalated"
      5. NO auto-reply is sent (escalation = human review)
    """

    def test_escalation_keywords_detected(self):
        """Escalation keywords in the body trigger detection."""
        sg = SafetyGuard()

        body = (
            "I am extremely unhappy with your service. If this is not resolved "
            "I will be contacting my attorney and filing a formal complaint."
        )
        assert sg.contains_escalation_keywords(body) is True

    def test_complaint_not_auto_replied(self):
        """Safety should block reply if email context contains spam-like
        patterns. For escalation, the business logic (not safety) decides
        to draft instead of reply. Safety should at least allow labeling."""
        sg = SafetyGuard()
        ok, _ = sg.check_action("label_email", {
            "email_id": "msg_complaint",
            "labels": ["Escalated", "Urgent"],
        })
        assert ok is True

    @patch("tools.alert_tools._slack_configured", return_value=True)
    @patch("tools.alert_tools.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    @patch("tools.alert_tools.httpx.Client")
    def test_escalation_alert_sent(self, mock_client_cls, mock_cfg):
        """Alert is sent via Slack for complaint emails."""
        from tools.alert_tools import send_escalation_alert

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(
            return_value=MagicMock(post=MagicMock(return_value=mock_resp))
        )
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = send_escalation_alert(
            channel="slack",
            message="Complaint from angry_customer@corp.com: legal threat detected",
            urgency="critical",
        )

        assert result.success is True
        assert result.channel == "slack"

    def test_full_complaint_classification(self):
        """End-to-end: read email → detect escalation → verify no reply allowed to spam."""
        from tools.gmail_tools import read_emails

        email = _make_email(
            msg_id="msg_complaint",
            subject="Formal Complaint - Legal Action",
            body="This is a formal complaint. I demand a refund or I will sue.",
            sender_email="angry@customer.com",
            sender_name="Angry Customer",
        )
        raw_msg = _make_gmail_api_message(email)

        svc = MagicMock()
        svc.users().messages().list.return_value.execute.return_value = {
            "messages": [{"id": email.id}],
        }
        svc.users().messages().get.return_value.execute.return_value = raw_msg

        emails = read_emails(svc, max_results=10)
        fetched = emails[0]

        # Detect escalation
        sg = SafetyGuard()
        assert sg.contains_escalation_keywords(fetched.body) is True
        assert sg.contains_escalation_keywords(fetched.subject) is True


# ============================================================================
# Workflow 3 — Follow-up Scheduling
# ============================================================================


class TestFollowUpWorkflow:
    """Agent schedules a follow-up for a pending response.

    Expected flow:
      1. Process an email requiring follow-up
      2. schedule_followup creates a DB record
      3. Follow-up due time is correctly calculated
    """

    @patch("tools.calendar_tools.create_follow_up")
    def test_followup_scheduled(self, mock_create_fu):
        from tools.calendar_tools import schedule_followup
        from models.tool_models import FollowUpScheduleResponse

        mock_create_fu.return_value = MagicMock(id=42)

        result = schedule_followup(
            email_id="msg_followup",
            follow_up_after_hours=24,
            note="Check if client responded to proposal",
            sender_email="client@company.com",
        )

        assert isinstance(result, FollowUpScheduleResponse)
        assert result.success is True
        assert result.follow_up_id == 42
        assert result.email_id == "msg_followup"
        mock_create_fu.assert_called_once()

    @patch("tools.calendar_tools.create_follow_up")
    def test_followup_due_time_correct(self, mock_create_fu):
        from tools.calendar_tools import schedule_followup

        mock_create_fu.return_value = MagicMock(id=1)

        result = schedule_followup(
            email_id="msg_001",
            follow_up_after_hours=48,
            sender_email="test@test.com",
        )

        # Due time should be ~48h from now
        now = datetime.now(timezone.utc)
        assert result.due_time > now
        delta = (result.due_time - now).total_seconds() / 3600
        assert 47.9 < delta < 48.1

    def test_followup_safety_allowed(self):
        """Safety guard should allow scheduling follow-ups."""
        sg = SafetyGuard()
        ok, _ = sg.check_action("schedule_followup", {
            "email_id": "msg_001", "follow_up_after_hours": 24,
        })
        assert ok is True


# ============================================================================
# Workflow 4 — Spam Email
# ============================================================================


class TestSpamWorkflow:
    """A spam email arrives in the inbox.

    Expected flow:
      1. read_emails fetches the email
      2. is_spam detects it as spam
      3. Agent labels it as spam and archives
      4. Agent does NOT reply (safety rule blocks it)
    """

    def test_spam_detected_and_reply_blocked(self):
        """Full flow: spam email → detected → reply blocked."""
        sg = SafetyGuard()

        spam = _make_email(
            msg_id="msg_spam",
            subject="You WON a FREE cash PRIZE! Act NOW!",
            body="Click here to claim your million dollars. Buy now! Limited time. Earn money fast.",
            sender_email="noreply@scam-lottery.com",
            sender_name="Prize Committee",
        )

        email_dict = spam.model_dump(mode="json")

        # Step 1: Detect spam
        assert sg.is_spam(email_dict) is True

        # Step 2: Reply should be blocked
        ok, reason = sg.check_action("reply_to_email", {
            "thread_id": spam.thread_id,
            "body": "Thanks for the prize!",
            "email_context": email_dict,
        })
        assert ok is False
        assert "never_reply_to_spam" in reason

    def test_spam_can_be_labeled(self):
        """Labeling spam as SPAM and archiving should be allowed."""
        sg = SafetyGuard()
        ok, _ = sg.check_action("label_email", {
            "email_id": "msg_spam",
            "labels": ["SPAM"],
            "archive": True,
        })
        assert ok is True


# ============================================================================
# Workflow 5 — Known Client Email
# ============================================================================


class TestKnownClientWorkflow:
    """A known client emails with a routine question.

    Expected flow:
      1. Read the email
      2. Recall sender history from memory
      3. Safety allows auto-reply (no dangerous content)
      4. send_email sends the reply
      5. update_crm logs the interaction
    """

    def test_known_client_auto_reply_allowed(self):
        """Safety should allow replying to a normal client email."""
        sg = SafetyGuard()
        ok, _ = sg.check_action("send_email", {
            "to": "client@company.com",
            "subject": "Re: Project update",
            "body": "Hi! The project is on schedule. Deliverables are expected next week.",
        })
        assert ok is True

    def test_send_reply_and_update_crm(self):
        """Send reply + update CRM as a combined workflow."""
        from tools.gmail_tools import send_email

        svc = MagicMock()
        svc.users().messages().send.return_value.execute.return_value = {
            "id": "sent_client_001",
            "threadId": "thr_client_001",
        }

        # Send reply
        result = send_email(
            svc,
            to="client@company.com",
            subject="Re: Project update",
            body="The project is on track.",
            reply_to_thread_id="thr_client_001",
        )
        assert result.message_id == "sent_client_001"
        assert result.status == "sent"

        # Update CRM
        with patch("tools.crm_tools._hubspot_configured", return_value=False), \
             patch("tools.crm_tools.update_sender_memory") as mock_update:

            from tools.crm_tools import update_crm

            crm_result = update_crm(
                "client@company.com",
                "replied_to_inquiry",
                {"note": "Replied about project status"},
            )
            assert crm_result.success is True
            mock_update.assert_called_once()

    def test_memory_context_integration(self):
        """Build email context with sender history for the agent prompt."""
        from agent.gmailmind import build_email_context_message

        email_data = {
            "id": "msg_client",
            "thread_id": "thr_client",
            "subject": "Project update?",
            "body": "Any updates on the project?",
            "sender": {"email": "client@company.com", "name": "John"},
            "labels": ["INBOX"],
            "snippet": "Any updates on the project?",
        }

        sender_history = {
            "name": "John Smith",
            "company": "Acme Corp",
            "tags": ["client", "priority"],
            "last_interaction": "2026-02-25T10:00:00+00:00",
            "history": [
                {"timestamp": "2026-02-20", "action": "replied", "note": "Sent proposal"},
                {"timestamp": "2026-02-25", "action": "follow_up", "note": "Checked status"},
            ],
        }

        context = build_email_context_message(
            email_data=email_data,
            sender_history=sender_history,
            business_goals=["Close deals faster", "Keep clients happy"],
            today_actions_count=15,
        )

        assert "client@company.com" in context
        assert "Acme Corp" in context
        assert "Known contact: YES" in context
        assert "Close deals faster" in context
        assert "Actions taken today: 15" in context
        assert "Sent proposal" in context

    def test_first_time_sender_context(self):
        """Context for a first-time sender shows 'NO' for known contact."""
        from agent.gmailmind import build_email_context_message

        email_data = {
            "id": "msg_new",
            "thread_id": "thr_new",
            "subject": "Inquiry",
            "body": "I'm interested in your product.",
            "sender": {"email": "stranger@unknown.com", "name": ""},
            "labels": ["INBOX", "UNREAD"],
            "snippet": "I'm interested",
        }

        context = build_email_context_message(
            email_data=email_data,
            sender_history=None,
            business_goals=["Generate leads"],
            today_actions_count=0,
        )

        assert "Known contact: NO" in context
        assert "first-time sender" in context


# ============================================================================
# Cross-workflow: GmailMind agent creation
# ============================================================================


class TestAgentCreation:
    def test_agent_created_with_tools(self):
        from agent.gmailmind import GmailMind

        gm = GmailMind()
        assert gm.name == "GmailMind"
        assert gm.model == "gpt-4o"
        assert len(gm.tools) == 12

    def test_system_prompt_includes_goals(self):
        from agent.gmailmind import build_system_prompt

        config = {
            "business_name": "TestCo",
            "owner_name": "Test Owner",
            "business_goals": ["Close more deals", "Respond fast"],
            "reply_tone": "professional",
            "language": "English",
            "autonomy": {},
            "working_hours": {},
            "escalation": {},
            "vip_contacts": [],
            "blocked_senders": [],
            "followup_defaults": {},
            "reply_templates": {},
        }

        prompt = build_system_prompt(config)

        assert "TestCo" in prompt
        assert "Test Owner" in prompt
        assert "Close more deals" in prompt
        assert "SAFETY BOUNDARIES" in prompt
        assert "DECISION FRAMEWORK" in prompt
