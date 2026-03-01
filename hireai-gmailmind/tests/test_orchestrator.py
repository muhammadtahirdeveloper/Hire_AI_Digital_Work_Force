"""Tests for the Phase 2 Orchestrator system.

Covers:
  - AgentRegistry registration and lookup
  - FeatureGate tier definitions and upgrade messages
  - GeneralAgent tool sets and classification
  - HRAgent industry, tiers, and classification
  - GmailMindOrchestrator initialisation
"""

import pytest

from agents.general.general_agent import GeneralAgent
from agents.hr.hr_agent import HRAgent
from orchestrator.agent_registry import AgentRegistry
from orchestrator.feature_gates import FeatureGate
from orchestrator.orchestrator import GmailMindOrchestrator


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


class TestFeatureGatesTier1:
    def test_tier1_features(self):
        fg = FeatureGate()
        features = fg.TIER_FEATURES["tier1"]["features"]
        assert "read" in features
        assert "auto_reply" not in features
        assert "cv_processing" not in features

    def test_tier1_price(self):
        fg = FeatureGate()
        assert fg.TIER_FEATURES["tier1"]["price"] == 19

    def test_tier1_max_emails(self):
        fg = FeatureGate()
        assert fg.TIER_FEATURES["tier1"]["max_emails_per_day"] == 200


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
        assert fg.TIER_FEATURES["tier2"]["price"] == 49

    def test_tier2_max_emails(self):
        fg = FeatureGate()
        assert fg.TIER_FEATURES["tier2"]["max_emails_per_day"] == 500


class TestFeatureGatesTier3:
    def test_tier3_features(self):
        fg = FeatureGate()
        features = fg.TIER_FEATURES["tier3"]["features"]
        assert "all" in features

    def test_tier3_price(self):
        fg = FeatureGate()
        assert fg.TIER_FEATURES["tier3"]["price"] == 99

    def test_tier3_unlimited_emails(self):
        fg = FeatureGate()
        assert fg.TIER_FEATURES["tier3"]["max_emails_per_day"] == 999999


class TestUpgradeMessage:
    def test_upgrade_from_tier1(self):
        fg = FeatureGate()
        msg = fg.get_upgrade_message("tier1", "auto_reply")
        assert "tier2" in msg.lower() or "upgrade" in msg.lower()

    def test_upgrade_message_contains_price(self):
        fg = FeatureGate()
        msg = fg.get_upgrade_message("tier1", "auto_reply")
        assert "$49" in msg or "49" in msg

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
