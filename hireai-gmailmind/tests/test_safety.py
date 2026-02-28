"""Tests for the SafetyGuard — every hard rule, spam detection, escalation keywords.

Covers:
  - All 7 HARD_RULES enforced via check_action()
  - SafetyViolationError raised via guard()
  - Daily limit enforcement
  - Spam detection (is_spam)
  - Escalation keyword detection (contains_escalation_keywords)
"""

import pytest
from unittest.mock import patch, MagicMock

from agent.safety_guard import SafetyGuard, SafetyViolationError


@pytest.fixture
def sg():
    """Fresh SafetyGuard instance for each test."""
    return SafetyGuard()


# ============================================================================
# Hard Rule 1 — never_delete_email_permanently
# ============================================================================


class TestNeverDeletePermanently:
    def test_delete_email_blocked(self, sg):
        ok, reason = sg.check_action("delete_email", {})
        assert ok is False
        assert "never_delete_email_permanently" in reason

    def test_delete_email_permanently_blocked(self, sg):
        ok, reason = sg.check_action("delete_email_permanently", {})
        assert ok is False

    def test_trash_email_permanently_blocked(self, sg):
        ok, reason = sg.check_action("trash_email_permanently", {})
        assert ok is False

    def test_purge_blocked(self, sg):
        ok, reason = sg.check_action("purge", {})
        assert ok is False

    def test_expunge_blocked(self, sg):
        ok, reason = sg.check_action("expunge", {})
        assert ok is False

    def test_read_emails_allowed(self, sg):
        ok, _ = sg.check_action("read_emails", {})
        assert ok is True


# ============================================================================
# Hard Rule 2 — never_send_mass_email_over_50
# ============================================================================


class TestNeverSendMassEmail:
    def test_single_recipient_allowed(self, sg):
        ok, _ = sg.check_action("send_email", {"to": "alice@test.com", "body": "hi", "subject": "hi"})
        assert ok is True

    def test_50_recipients_allowed(self, sg):
        recipients = ",".join(f"user{i}@test.com" for i in range(50))
        ok, _ = sg.check_action("send_email", {"to": recipients, "body": "hi", "subject": "hi"})
        assert ok is True

    def test_51_recipients_blocked(self, sg):
        recipients = ",".join(f"user{i}@test.com" for i in range(51))
        ok, reason = sg.check_action("send_email", {"to": recipients, "body": "hi", "subject": "hi"})
        assert ok is False
        assert "never_send_mass_email_over_50" in reason

    def test_mass_draft_also_blocked(self, sg):
        recipients = ",".join(f"user{i}@test.com" for i in range(51))
        ok, reason = sg.check_action("create_draft", {"to": recipients, "body": "hi", "subject": "hi"})
        assert ok is False

    def test_list_recipients_blocked(self, sg):
        recipients = [f"user{i}@test.com" for i in range(51)]
        ok, _ = sg.check_action("send_email", {"to": recipients, "body": "hi", "subject": "hi"})
        assert ok is False


# ============================================================================
# Hard Rule 3 — never_share_credentials
# ============================================================================


class TestNeverShareCredentials:
    def test_password_in_body_blocked(self, sg):
        ok, reason = sg.check_action("send_email", {
            "to": "bob@test.com", "subject": "Info",
            "body": "Your password: secret123",
        })
        assert ok is False
        assert "never_share_credentials" in reason

    def test_api_key_in_body_blocked(self, sg):
        ok, _ = sg.check_action("send_email", {
            "to": "bob@test.com", "subject": "Keys",
            "body": "api_key=sk_live_abc123xyz",
        })
        assert ok is False

    def test_bearer_token_blocked(self, sg):
        ok, _ = sg.check_action("reply_to_email", {
            "thread_id": "t1", "body": "Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig",
        })
        assert ok is False

    def test_private_key_blocked(self, sg):
        ok, _ = sg.check_action("create_draft", {
            "to": "a@b.com", "subject": "Key",
            "body": "-----BEGIN PRIVATE KEY-----\nMIIE...",
        })
        assert ok is False

    def test_normal_body_allowed(self, sg):
        ok, _ = sg.check_action("send_email", {
            "to": "bob@test.com", "subject": "Hello",
            "body": "Looking forward to our meeting!",
        })
        assert ok is True

    def test_credential_in_subject_blocked(self, sg):
        ok, _ = sg.check_action("send_email", {
            "to": "a@b.com", "subject": "token= abc123", "body": "see subject",
        })
        assert ok is False


# ============================================================================
# Hard Rule 4 — never_reply_to_spam
# ============================================================================


class TestNeverReplyToSpam:
    def test_reply_to_spam_blocked(self, sg):
        spam_email = {
            "subject": "WIN a FREE lottery prize now!",
            "body": "Click here to claim your million dollars inheritance",
            "sender": {"email": "noreply@spam.com"},
        }
        ok, reason = sg.check_action("reply_to_email", {
            "thread_id": "t1", "body": "Thanks!",
            "email_context": spam_email,
        })
        assert ok is False
        assert "never_reply_to_spam" in reason

    def test_reply_to_normal_allowed(self, sg):
        normal = {"subject": "Meeting tomorrow", "body": "Let's discuss the project."}
        ok, _ = sg.check_action("reply_to_email", {
            "thread_id": "t1", "body": "Sure!",
            "email_context": normal,
        })
        assert ok is True

    def test_non_reply_action_not_checked(self, sg):
        ok, _ = sg.check_action("send_email", {
            "to": "a@b.com", "subject": "hi", "body": "hello",
        })
        assert ok is True


# ============================================================================
# Hard Rule 5 — never_take_financial_actions
# ============================================================================


class TestNeverTakeFinancialActions:
    @pytest.mark.parametrize("keyword", [
        "wire transfer", "bank transfer", "send money", "payment",
        "bitcoin", "crypto", "wallet address", "routing number",
    ])
    def test_financial_keyword_blocked(self, sg, keyword):
        ok, reason = sg.check_action("send_email", {
            "to": "a@b.com", "subject": "hi",
            "body": f"Please process the {keyword} immediately.",
        })
        assert ok is False
        assert "never_take_financial_actions" in reason

    def test_financial_in_subject_blocked(self, sg):
        ok, _ = sg.check_action("send_email", {
            "to": "a@b.com", "subject": "Invoice payment due",
            "body": "See attached.",
        })
        assert ok is False

    def test_normal_business_allowed(self, sg):
        ok, _ = sg.check_action("send_email", {
            "to": "a@b.com", "subject": "Project update",
            "body": "The project is on track.",
        })
        assert ok is True


# ============================================================================
# Hard Rule 6 — never_impersonate
# ============================================================================


class TestNeverImpersonate:
    @pytest.mark.parametrize("phrase", [
        "i am the ceo", "i am the owner", "this is the ceo",
        "speaking on behalf of the board", "as the legal representative",
        "i am authorized to sign", "i have authority to",
        "acting as director",
    ])
    def test_impersonation_phrase_blocked(self, sg, phrase):
        ok, reason = sg.check_action("send_email", {
            "to": "a@b.com", "subject": "Re: Contract",
            "body": f"Hello, {phrase} of this company.",
        })
        assert ok is False
        assert "never_impersonate" in reason

    def test_normal_body_allowed(self, sg):
        ok, _ = sg.check_action("send_email", {
            "to": "a@b.com", "subject": "Follow-up",
            "body": "I am writing to follow up on our conversation.",
        })
        assert ok is True


# ============================================================================
# Hard Rule 7 — stop_if_daily_limit_exceeded
# ============================================================================


class TestDailyLimitEnforcement:
    @patch("agent.safety_guard.session_memory")
    def test_under_limit_allowed(self, mock_mem, sg):
        mock_mem.action_count.return_value = 10
        ok, _ = sg.check_action("read_emails", {})
        assert ok is True

    @patch("agent.safety_guard.session_memory")
    def test_at_limit_blocked(self, mock_mem, sg):
        mock_mem.action_count.return_value = 200  # default DAILY_ACTION_LIMIT
        ok, reason = sg.check_action("read_emails", {})
        assert ok is False
        assert "stop_if_daily_limit_exceeded" in reason

    @patch("agent.safety_guard.session_memory")
    def test_over_limit_blocked(self, mock_mem, sg):
        mock_mem.action_count.return_value = 999
        ok, _ = sg.check_action("send_email", {"to": "a@b.com", "body": "hi", "subject": "hi"})
        assert ok is False

    @patch("agent.safety_guard.session_memory")
    def test_is_daily_limit_exceeded_method(self, mock_mem, sg):
        mock_mem.action_count.return_value = 200
        assert sg.is_daily_limit_exceeded() is True

        mock_mem.action_count.return_value = 199
        assert sg.is_daily_limit_exceeded() is False


# ============================================================================
# SafetyViolationError raised via guard()
# ============================================================================


class TestGuardRaises:
    def test_guard_raises_on_violation(self, sg):
        with pytest.raises(SafetyViolationError) as exc_info:
            sg.guard("delete_email", {})

        assert exc_info.value.rule is not None
        assert exc_info.value.reason is not None
        assert "SAFETY VIOLATION" in str(exc_info.value)

    def test_guard_passes_safe_action(self, sg):
        # Should not raise
        sg.guard("read_emails", {"max_results": 10})

    def test_safety_violation_error_attributes(self):
        err = SafetyViolationError(rule="test_rule", reason="test reason")
        assert err.rule == "test_rule"
        assert err.reason == "test reason"
        assert "test_rule" in str(err)


# ============================================================================
# Spam Detection
# ============================================================================


class TestSpamDetection:
    def test_obvious_spam(self, sg):
        email = {
            "subject": "You are a WINNER! Click here now",
            "body": "Earn money fast, buy now! Limited time offer.",
            "sender": {"email": "spam@scam.com"},
        }
        assert sg.is_spam(email) is True

    def test_win_free_money(self, sg):
        email = {"from": "noreply@promo.com", "subject": "WIN FREE MONEY"}
        assert sg.is_spam(email) is True

    def test_noreply_with_spam_subject(self, sg):
        email = {"from": "noreply@offers.com", "subject": "Congratulations! You won a prize"}
        assert sg.is_spam(email) is True

    def test_normal_email_not_spam(self, sg):
        email = {
            "subject": "Meeting tomorrow at 3pm",
            "body": "Hi, can we discuss the project timeline?",
            "sender": {"email": "colleague@company.com"},
        }
        assert sg.is_spam(email) is False

    def test_single_pattern_not_spam(self, sg):
        # Just one pattern match should not flag (threshold is 2)
        email = {"subject": "Please unsubscribe me", "body": "Thanks"}
        assert sg.is_spam(email) is False

    def test_empty_email_not_spam(self, sg):
        assert sg.is_spam({}) is False

    def test_from_key_supported(self, sg):
        """is_spam should check 'from' key as well as 'sender'."""
        email = {"from": "noreply@x.com", "subject": "WIN a FREE cash prize"}
        assert sg.is_spam(email) is True


# ============================================================================
# Escalation Keyword Detection
# ============================================================================


class TestEscalationKeywords:
    @pytest.mark.parametrize("keyword", [
        "legal", "lawsuit", "attorney", "lawyer", "complaint",
        "urgent", "emergency", "fraud", "harassment", "threat",
        "subpoena", "regulatory", "compliance", "data breach",
    ])
    def test_keyword_detected(self, sg, keyword):
        assert sg.contains_escalation_keywords(f"This email is about {keyword} matters.") is True

    def test_case_insensitive(self, sg):
        assert sg.contains_escalation_keywords("URGENT: Legal matter") is True

    def test_no_keywords(self, sg):
        assert sg.contains_escalation_keywords("Hello, how are you? Let's schedule a meeting.") is False

    def test_empty_string(self, sg):
        assert sg.contains_escalation_keywords("") is False

    def test_multi_word_keyword(self, sg):
        assert sg.contains_escalation_keywords("We have a payment dispute to resolve.") is True
        assert sg.contains_escalation_keywords("There was a data breach last night.") is True


# ============================================================================
# Multiple rules checked together
# ============================================================================


class TestMultipleRulesInteraction:
    def test_financial_and_impersonation(self, sg):
        """Both financial and impersonation rules should trigger; first one wins."""
        ok, reason = sg.check_action("send_email", {
            "to": "a@b.com", "subject": "Payment",
            "body": "I am the CEO. Process the wire transfer now.",
        })
        assert ok is False

    def test_safe_action_passes_all_rules(self, sg):
        ok, reason = sg.check_action("label_email", {
            "email_id": "msg_001", "labels": ["Important"],
        })
        assert ok is True
        assert reason == ""
