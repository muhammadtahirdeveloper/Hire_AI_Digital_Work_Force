"""Tests for E-commerce Agent and Skills."""

import pytest
from agents.ecommerce.ecommerce_agent import EcommerceAgent
from skills.ecommerce_skills import EcommerceSkills


class TestEcommerceAgent:
    """Test suite for EcommerceAgent."""

    def test_agent_name(self):
        """Test agent name is set correctly."""
        agent = EcommerceAgent()
        assert agent.agent_name == "GmailMind E-commerce Agent"

    def test_industry(self):
        """Test industry is set to ecommerce."""
        agent = EcommerceAgent()
        assert agent.industry == "ecommerce"

    def test_supported_tiers(self):
        """Test supported tiers include tier2 and tier3."""
        agent = EcommerceAgent()
        assert "tier2" in agent.supported_tiers
        assert "tier3" in agent.supported_tiers
        assert "tier1" not in agent.supported_tiers

    def test_classify_order_inquiry(self):
        """Test classification of order inquiry emails."""
        agent = EcommerceAgent()
        email = {
            "subject": "Where is my order?",
            "body": "I placed order #12345 last week and have not received it"
        }
        assert agent.classify_email(email) == "order_inquiry"

    def test_classify_refund(self):
        """Test classification of refund request emails."""
        agent = EcommerceAgent()
        email = {
            "subject": "Refund Request",
            "body": "I want a refund for my damaged item"
        }
        assert agent.classify_email(email) == "refund_request"

    def test_classify_complaint(self):
        """Test classification of complaint emails."""
        agent = EcommerceAgent()
        email = {
            "subject": "Complaint about service",
            "body": "I am very disappointed with my experience"
        }
        assert agent.classify_email(email) == "complaint"

    def test_classify_supplier(self):
        """Test classification of supplier emails."""
        agent = EcommerceAgent()
        email = {
            "subject": "Invoice for bulk order",
            "body": "Please find attached our invoice for the wholesale order"
        }
        assert agent.classify_email(email) == "supplier_email"

    def test_classify_shipping(self):
        """Test classification of shipping inquiry emails."""
        agent = EcommerceAgent()
        email = {
            "subject": "Tracking information",
            "body": "When will my package be delivered?"
        }
        assert agent.classify_email(email) == "shipping_inquiry"

    def test_classify_other(self):
        """Test classification of unrelated emails."""
        agent = EcommerceAgent()
        email = {
            "subject": "Hello",
            "body": "Just checking in"
        }
        assert agent.classify_email(email) == "other"


class TestEcommerceSkills:
    """Test suite for EcommerceSkills."""

    def test_extract_order_id_hash_pattern(self):
        """Test order ID extraction with # pattern."""
        skills = EcommerceSkills()
        assert skills.extract_order_id("My order #12345 is missing") == "12345"
        assert skills.extract_order_id("Order #987654 not delivered") == "987654"

    def test_extract_order_id_order_pattern(self):
        """Test order ID extraction with ORDER- pattern."""
        skills = EcommerceSkills()
        result = skills.extract_order_id("ORDER-ABC123 not delivered")
        assert result is not None
        assert result == "ABC123"

    def test_extract_order_id_ord_pattern(self):
        """Test order ID extraction with ORD- pattern."""
        skills = EcommerceSkills()
        result = skills.extract_order_id("ORD-456 is late")
        assert result is not None
        assert result == "456"

    def test_extract_order_id_none(self):
        """Test order ID extraction returns None when no ID found."""
        skills = EcommerceSkills()
        assert skills.extract_order_id("No order number here") is None
        assert skills.extract_order_id("I want to place an order") is None

    def test_sentiment_very_negative(self):
        """Test detection of very negative sentiment."""
        skills = EcommerceSkills()
        assert skills.detect_customer_sentiment(
            "This is a scam! I will take legal action"
        ) == "very_negative"
        assert skills.detect_customer_sentiment(
            "I am furious and outraged"
        ) == "very_negative"
        assert skills.detect_customer_sentiment(
            "This is fraud, calling my lawyer"
        ) == "very_negative"

    def test_sentiment_negative(self):
        """Test detection of negative sentiment."""
        skills = EcommerceSkills()
        assert skills.detect_customer_sentiment(
            "I am disappointed with this purchase"
        ) == "negative"
        assert skills.detect_customer_sentiment(
            "This is terrible and the worst experience"
        ) == "negative"
        assert skills.detect_customer_sentiment(
            "Very unhappy with the product quality"
        ) == "negative"

    def test_sentiment_positive(self):
        """Test detection of positive sentiment."""
        skills = EcommerceSkills()
        assert skills.detect_customer_sentiment(
            "I love this product, amazing quality!"
        ) == "positive"
        assert skills.detect_customer_sentiment(
            "Great service, very happy with my purchase"
        ) == "positive"
        assert skills.detect_customer_sentiment(
            "Excellent product, thank you!"
        ) == "positive"

    def test_sentiment_neutral(self):
        """Test detection of neutral sentiment."""
        skills = EcommerceSkills()
        assert skills.detect_customer_sentiment(
            "I received the package today"
        ) == "neutral"
        assert skills.detect_customer_sentiment(
            "Order confirmation needed"
        ) == "neutral"

    def test_format_whatsapp_report(self):
        """Test WhatsApp report formatting."""
        skills = EcommerceSkills()
        report = {
            "order_inquiries": 15,
            "refund_requests": 3,
            "complaints": 2,
            "resolved": 4,
            "positive_reviews": 8,
            "period": "Last 7 days"
        }
        formatted = skills.format_report_for_whatsapp(report)
        assert "🛒 Weekly E-commerce Report" in formatted
        assert "📧 Order Inquiries: 15" in formatted
        assert "💸 Refund Requests: 3" in formatted
        assert "😤 Complaints: 2" in formatted
        assert "✅ Resolved: 4" in formatted
