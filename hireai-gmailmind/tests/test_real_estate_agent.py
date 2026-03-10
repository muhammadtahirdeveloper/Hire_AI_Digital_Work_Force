"""Tests for Real Estate Agent and Skills."""

import pytest
from agents.real_estate.real_estate_agent import RealEstateAgent
from skills.real_estate_skills import RealEstateSkills


class TestRealEstateAgent:
    """Test suite for RealEstateAgent."""

    def test_agent_name(self):
        """Test agent name is set correctly."""
        agent = RealEstateAgent()
        assert agent.agent_name == "GmailMind Real Estate Agent"

    def test_industry(self):
        """Test industry is set to real_estate."""
        agent = RealEstateAgent()
        assert agent.industry == "real_estate"

    def test_supported_tiers(self):
        """Test supported tiers include tier2 but not tier1."""
        agent = RealEstateAgent()
        assert "tier2" in agent.supported_tiers
        assert "tier3" in agent.supported_tiers
        assert "tier1" not in agent.supported_tiers

    def test_classify_property_inquiry(self):
        """Test classification of property inquiry emails."""
        agent = RealEstateAgent()
        email = {
            "subject": "Interested in your property listing",
            "body": "I would like to know more about the apartment"
        }
        assert agent.classify_email(email) == "property_inquiry"

    def test_classify_viewing_request(self):
        """Test classification of viewing request emails."""
        agent = RealEstateAgent()
        email = {
            "subject": "Schedule a viewing",
            "body": "Can I arrange a visit to see the property?"
        }
        assert agent.classify_email(email) == "viewing_request"

    def test_classify_maintenance(self):
        """Test classification of maintenance request emails."""
        agent = RealEstateAgent()
        email = {
            "subject": "Maintenance Required",
            "body": "The heating is broken in my apartment"
        }
        assert agent.classify_email(email) == "maintenance_request"

    def test_classify_other(self):
        """Test classification of unrelated emails."""
        agent = RealEstateAgent()
        email = {
            "subject": "Hello",
            "body": "Just saying hi"
        }
        assert agent.classify_email(email) == "other"


class TestRealEstateSkills:
    """Test suite for RealEstateSkills."""

    def test_critical_maintenance(self):
        """Test detection of critical maintenance issues."""
        skills = RealEstateSkills()
        assert skills.detect_maintenance_priority("gas leak in kitchen") == "critical"
        assert skills.detect_maintenance_priority("flood in basement") == "critical"
        assert skills.detect_maintenance_priority("fire in the building") == "critical"
        assert skills.detect_maintenance_priority("no water supply") == "critical"

    def test_high_maintenance(self):
        """Test detection of high priority maintenance issues."""
        skills = RealEstateSkills()
        assert skills.detect_maintenance_priority("no hot water") == "high"
        assert skills.detect_maintenance_priority("heating not working") == "high"
        assert skills.detect_maintenance_priority("roof leak") == "high"

    def test_medium_maintenance(self):
        """Test detection of medium priority maintenance issues."""
        skills = RealEstateSkills()
        assert skills.detect_maintenance_priority("pest problem") == "medium"
        assert skills.detect_maintenance_priority("plumbing issue") == "medium"
        assert skills.detect_maintenance_priority("appliance broken") == "medium"

    def test_low_maintenance(self):
        """Test detection of low priority maintenance issues."""
        skills = RealEstateSkills()
        assert skills.detect_maintenance_priority("paint is peeling") == "low"
        assert skills.detect_maintenance_priority("door squeaks") == "low"

    def test_format_property_listing(self):
        """Test property listing formatting."""
        skills = RealEstateSkills()
        property_data = {
            "address": "123 Main St",
            "price": 450000,
            "bedrooms": 3,
            "bathrooms": 2,
            "size_sqft": 2000,
            "location": "Downtown"
        }
        formatted = skills.format_property_listing(property_data)
        assert "🏠" in formatted
        assert "123 Main St" in formatted
        assert "450,000" in formatted or "450000" in formatted
        assert "3" in formatted  # bedrooms
        assert "2000" in formatted  # size

    def test_format_whatsapp_report(self):
        """Test WhatsApp report formatting."""
        skills = RealEstateSkills()
        report = {
            "new_inquiries": 5,
            "viewings_scheduled": 3,
            "maintenance_requests": 2,
            "resolved": 1,
            "active_listings": 10,
            "period": "Last 7 days"
        }
        formatted = skills.format_report_for_whatsapp(report)
        assert "🏠 Weekly Property Report" in formatted
        assert "📧 New Inquiries: 5" in formatted
        assert "👁 Viewings Scheduled: 3" in formatted
        assert "🔧 Maintenance Requests: 2" in formatted
