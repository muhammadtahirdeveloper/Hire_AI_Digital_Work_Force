"""Tests for the Phase 2 Orchestrator system + Phase 5 AI Router integration.

Covers:
  - AgentRegistry registration and lookup
  - FeatureGate tier definitions and upgrade messages
  - GeneralAgent tool sets and classification
  - HRAgent industry, tiers, and classification
  - GmailMindOrchestrator initialisation
  - get_agent_for_user (Phase 5)
  - BaseAgent.process_email via mocked AIRouter (Phase 5)
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from agents.general.general_agent import GeneralAgent
from agents.hr.hr_agent import HRAgent
from orchestrator.agent_registry import AgentRegistry
from orchestrator.feature_gates import FeatureGate
from orchestrator.orchestrator import GmailMindOrchestrator


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ============================================================================
# AgentRegistry
# ============================================================================


class TestAgentRegistry:
    def test_register_and_get(self):
        registry = AgentRegistry()
        registry.register("general", GeneralAgent)
        registry.register("hr", HRAgent)
        assert registry.get_agent("general") == GeneralAgent
        assert registry.get_agent("hr") == HRAgent

    def test_unknown_returns_none(self):
        registry = AgentRegistry()
        assert registry.get_agent("unknown") is None

    def test_list_industries(self):
        registry = AgentRegistry()
        registry.register("general", GeneralAgent)
        registry.register("hr", HRAgent)
        industries = registry.list_industries()
        assert "general" in industries
        assert "hr" in industries


# ============================================================================
# FeatureGate — Tier definitions
# ============================================================================


class TestFeatureGatesTrial:
    def test_trial_features(self):
        fg = FeatureGate()
        features = fg.TIER_FEATURES["trial"]["features"]
        assert "read" in features
        assert "auto_reply" not in features

    def test_trial_price(self):
        fg = FeatureGate()
        assert fg.TIER_FEATURES["trial"]["price"] == 0

    def test_trial_max_emails(self):
        fg = FeatureGate()
        assert fg.TIER_FEATURES["trial"]["max_emails_per_day"] == 100


class TestFeatureGatesTier1:
    def test_tier1_features(self):
        fg = FeatureGate()
        features = fg.TIER_FEATURES["tier1"]["features"]
        assert "read" in features
        assert "auto_reply" in features
        assert "cv_processing" not in features

    def test_tier1_price(self):
        fg = FeatureGate()
        assert fg.TIER_FEATURES["tier1"]["price"] == 9

    def test_tier1_max_emails(self):
        fg = FeatureGate()
        assert fg.TIER_FEATURES["tier1"]["max_emails_per_day"] == 500


class TestFeatureGatesTier2:
    def test_tier2_features(self):
        fg = FeatureGate()
        features = fg.TIER_FEATURES["tier2"]["features"]
        assert "auto_reply" in features
        assert "cv_processing" in features
        assert "interview_scheduler" in features
        assert "candidate_tracker" in features

    def test_tier2_price(self):
        fg = FeatureGate()
        assert fg.TIER_FEATURES["tier2"]["price"] == 29

    def test_tier2_max_emails(self):
        fg = FeatureGate()
        assert fg.TIER_FEATURES["tier2"]["max_emails_per_day"] == 2000


class TestFeatureGatesTier3:
    def test_tier3_features(self):
        fg = FeatureGate()
        features = fg.TIER_FEATURES["tier3"]["features"]
        assert "all" in features

    def test_tier3_price(self):
        fg = FeatureGate()
        assert fg.TIER_FEATURES["tier3"]["price"] == 59

    def test_tier3_max_emails(self):
        fg = FeatureGate()
        assert fg.TIER_FEATURES["tier3"]["max_emails_per_day"] == 10000


class TestUpgradeMessage:
    def test_upgrade_from_trial(self):
        fg = FeatureGate()
        msg = fg.get_upgrade_message("trial", "auto_reply")
        assert "tier1" in msg.lower() or "upgrade" in msg.lower()

    def test_upgrade_message_contains_price(self):
        fg = FeatureGate()
        msg = fg.get_upgrade_message("trial", "auto_reply")
        assert "$9" in msg or "9" in msg

    def test_upgrade_for_unknown_feature(self):
        fg = FeatureGate()
        msg = fg.get_upgrade_message("tier1", "nonexistent_feature")
        assert "upgrade" in msg.lower() or "not available" in msg.lower() or "contact" in msg.lower()


# ============================================================================
# GeneralAgent
# ============================================================================


class TestGeneralAgent:
    def test_agent_name(self):
        agent = GeneralAgent()
        assert agent.agent_name == "GmailMind General Agent"

    def test_industry(self):
        agent = GeneralAgent()
        assert agent.industry == "general"

    def test_supported_tiers(self):
        agent = GeneralAgent()
        assert "tier1" in agent.supported_tiers
        assert "tier2" in agent.supported_tiers
        assert "tier3" in agent.supported_tiers

    def test_tier1_tools(self):
        agent = GeneralAgent()
        tier1_tools = agent.get_available_tools("tier1")
        assert "read_emails" in tier1_tools
        assert len(tier1_tools) == 3

    def test_tier2_tools_more_than_tier1(self):
        agent = GeneralAgent()
        tier1_tools = agent.get_available_tools("tier1")
        tier2_tools = agent.get_available_tools("tier2")
        assert len(tier2_tools) > len(tier1_tools)

    def test_tier3_tools_most(self):
        agent = GeneralAgent()
        tier2_tools = agent.get_available_tools("tier2")
        tier3_tools = agent.get_available_tools("tier3")
        assert len(tier3_tools) > len(tier2_tools)

    def test_system_prompt_tier1(self):
        agent = GeneralAgent()
        prompt = agent.get_system_prompt("tier1")
        assert "organization" in prompt.lower() or "organize" in prompt.lower()

    def test_system_prompt_tier3(self):
        agent = GeneralAgent()
        prompt = agent.get_system_prompt("tier3")
        assert "advanced" in prompt.lower() or "full" in prompt.lower()

    def test_classify_newsletter(self):
        agent = GeneralAgent()
        email = {"subject": "Weekly Newsletter", "body": "Unsubscribe to stop receiving"}
        assert agent.classify_email(email) == "newsletter"

    def test_classify_spam(self):
        agent = GeneralAgent()
        email = {"subject": "You are a winner!", "body": "Click here now"}
        assert agent.classify_email(email) == "spam"


# ============================================================================
# HRAgent
# ============================================================================


class TestHRAgent:
    def test_agent_name(self):
        agent = HRAgent()
        assert agent.agent_name == "GmailMind HR Agent"

    def test_industry(self):
        agent = HRAgent()
        assert agent.industry == "hr"

    def test_supported_tiers(self):
        agent = HRAgent()
        assert "tier1" not in agent.supported_tiers
        assert "tier2" in agent.supported_tiers
        assert "tier3" in agent.supported_tiers

    def test_classify_cv_application(self):
        agent = HRAgent()
        email = {
            "subject": "Application for Developer Role",
            "body": "Please find my CV attached",
        }
        assert agent.classify_email(email) == "cv_application"

    def test_classify_interview_request(self):
        agent = HRAgent()
        email = {
            "subject": "Re: Interview Schedule",
            "body": "I am available for interview on Monday",
        }
        assert agent.classify_email(email) == "interview_request"

    def test_classify_followup(self):
        agent = HRAgent()
        email = {
            "subject": "Any news?",
            "body": "Just checking in, have you heard back from the team?",
        }
        assert agent.classify_email(email) == "candidate_followup"

    def test_classify_offer_acceptance(self):
        agent = HRAgent()
        email = {
            "subject": "Re: Offer Letter",
            "body": "I am happy to accept the offer and looking forward to joining",
        }
        assert agent.classify_email(email) == "offer_acceptance"

    def test_classify_other(self):
        agent = HRAgent()
        email = {
            "subject": "Lunch plans",
            "body": "Want to grab lunch tomorrow?",
        }
        assert agent.classify_email(email) == "other"


# ============================================================================
# GmailMindOrchestrator
# ============================================================================


class TestOrchestrator:
    def test_orchestrator_init(self):
        o = GmailMindOrchestrator()
        assert o.registry is not None
        assert o.router is not None
        assert o.gates is not None

    def test_orchestrator_has_general_agent(self):
        o = GmailMindOrchestrator()
        agent_class = o.registry.get_agent("general")
        assert agent_class == GeneralAgent

    def test_orchestrator_has_hr_agent(self):
        o = GmailMindOrchestrator()
        agent_class = o.registry.get_agent("hr")
        assert agent_class == HRAgent

    def test_orchestrator_registered_industries(self):
        o = GmailMindOrchestrator()
        industries = o.registry.list_industries()
        assert "general" in industries
        assert "hr" in industries


# ============================================================================
# Phase 5 — get_agent_for_user
# ============================================================================


class TestGetAgentForUser:
    """Test orchestrator.get_agent_for_user routes users to the correct agent."""

    @patch.object(GmailMindOrchestrator, "__init__", lambda self: None)
    def test_general_user_gets_general_agent(self):
        o = GmailMindOrchestrator()
        o.registry = AgentRegistry()
        o.registry.register("general", GeneralAgent)
        o.registry.register("hr", HRAgent)
        o.router = MagicMock()
        o.router.get_user_industry.return_value = "general"
        o.gates = MagicMock()

        agent = o.get_agent_for_user("user_001")
        assert isinstance(agent, GeneralAgent)

    @patch.object(GmailMindOrchestrator, "__init__", lambda self: None)
    def test_hr_user_gets_hr_agent(self):
        o = GmailMindOrchestrator()
        o.registry = AgentRegistry()
        o.registry.register("general", GeneralAgent)
        o.registry.register("hr", HRAgent)
        o.router = MagicMock()
        o.router.get_user_industry.return_value = "hr"
        o.gates = MagicMock()

        agent = o.get_agent_for_user("user_002")
        assert isinstance(agent, HRAgent)

    @patch.object(GmailMindOrchestrator, "__init__", lambda self: None)
    def test_unknown_industry_falls_back_to_general(self):
        o = GmailMindOrchestrator()
        o.registry = AgentRegistry()
        o.registry.register("general", GeneralAgent)
        o.router = MagicMock()
        o.router.get_user_industry.return_value = "unknown_industry"
        o.gates = MagicMock()

        agent = o.get_agent_for_user("user_003")
        assert isinstance(agent, GeneralAgent)

    def test_full_orchestrator_get_agent(self):
        """Test via the real orchestrator init (uses default routing)."""
        o = GmailMindOrchestrator()
        with patch.object(o.router, "get_user_industry", return_value="general"):
            agent = o.get_agent_for_user("user_test")
            assert isinstance(agent, GeneralAgent)
            assert hasattr(agent, "ai_router")


# ============================================================================
# Phase 5 — BaseAgent.process_email with mocked AIRouter
# ============================================================================


class TestProcessEmail:
    """Test BaseAgent.process_email() with a mocked AIRouter.generate()."""

    def test_process_email_returns_decision(self):
        agent = GeneralAgent()
        mock_result = {
            "content": "ACTION: AUTO_REPLY\nREPLY: Thanks for reaching out!\nREASON: Standard inquiry.",
            "provider": "claude",
            "model": "claude-haiku-4-5-20251001",
        }
        agent.ai_router.generate = AsyncMock(return_value=mock_result)

        email = {"subject": "Inquiry", "body": "Tell me about your services."}
        result = _run(agent.process_email("user_1", email))

        assert result["action"] == "AUTO_REPLY"
        assert result["provider"] == "claude"
        assert result["model"] == "claude-haiku-4-5-20251001"
        assert "category" in result

    def test_process_email_draft_action(self):
        agent = GeneralAgent()
        mock_result = {
            "content": "ACTION: DRAFT_REPLY\nREPLY: I'll look into this and get back to you.",
            "provider": "claude",
            "model": "claude-haiku-4-5-20251001",
        }
        agent.ai_router.generate = AsyncMock(return_value=mock_result)

        email = {"subject": "Complex question", "body": "Can you explain your pricing tiers?"}
        result = _run(agent.process_email("user_2", email))

        assert result["action"] == "DRAFT_REPLY"
        assert result["provider"] == "claude"

    def test_process_email_escalate_action(self):
        agent = GeneralAgent()
        mock_result = {
            "content": "ACTION: ESCALATE\nREASON: Legal threat detected.",
            "provider": "claude",
            "model": "claude-haiku-4-5-20251001",
        }
        agent.ai_router.generate = AsyncMock(return_value=mock_result)

        email = {"subject": "Legal Notice", "body": "I am contacting my attorney."}
        result = _run(agent.process_email("user_3", email))

        assert result["action"] == "ESCALATE"

    def test_process_email_label_archive(self):
        agent = GeneralAgent()
        mock_result = {
            "content": "ACTION: LABEL_ARCHIVE\nREASON: Newsletter, no reply needed.",
            "provider": "claude",
            "model": "claude-haiku-4-5-20251001",
        }
        agent.ai_router.generate = AsyncMock(return_value=mock_result)

        email = {"subject": "Weekly Newsletter", "body": "Unsubscribe to stop."}
        result = _run(agent.process_email("user_4", email))

        assert result["action"] == "LABEL_ARCHIVE"
        assert result["category"] == "newsletter"

    def test_process_email_hr_agent_via_base(self):
        """HRAgent has its own process_email; verify base class version works too."""
        from agents.base_agent import BaseAgent

        agent = HRAgent()
        mock_result = {
            "content": "ACTION: DRAFT_REPLY\nREPLY: We received your application.",
            "provider": "claude",
            "model": "claude-haiku-4-5-20251001",
        }
        agent.ai_router.generate = AsyncMock(return_value=mock_result)

        email = {
            "subject": "Application for Developer Role",
            "body": "Please find my CV attached.",
        }
        # Call the BaseAgent version directly (HR overrides with its own)
        result = _run(BaseAgent.process_email(agent, "user_5", email))

        assert result["action"] == "DRAFT_REPLY"
        assert result["category"] == "cv_application"

    def test_hr_agent_own_process_email(self):
        """HRAgent's own sync pipeline handles CV applications."""
        agent = HRAgent()
        email = {
            "subject": "Application for Developer Role",
            "body": "Please find my CV attached.",
            "sender": {"email": "applicant@test.com", "name": "Test"},
        }
        config = {"business_name": "TestCo"}
        result = agent.process_email(email, config, "tier2", "user_hr")

        assert result["category"] == "cv_application"
        assert "action" in result

    def test_process_email_passes_user_id_to_router(self):
        agent = GeneralAgent()
        mock_result = {
            "content": "ACTION: AUTO_REPLY\nREPLY: Hello!",
            "provider": "claude",
            "model": "claude-haiku-4-5-20251001",
        }
        agent.ai_router.generate = AsyncMock(return_value=mock_result)

        email = {"subject": "Hi", "body": "Hello there."}
        _run(agent.process_email("user_specific_42", email))

        # Verify the router was called with the correct user_id
        call_kwargs = agent.ai_router.generate.call_args
        assert call_kwargs.kwargs.get("user_id") == "user_specific_42"
