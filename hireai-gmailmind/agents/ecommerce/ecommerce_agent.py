"""E-commerce Agent for GmailMind.

Handles customer orders, refunds, complaints, shipping inquiries,
and supplier communications for online businesses.
"""

import logging
import re
from typing import Optional

from agents.base_agent import BaseAgent
from agents.ecommerce.order_tracker import OrderTracker
from agents.ecommerce.ecommerce_templates import ECOMMERCE_TEMPLATES

logger = logging.getLogger(__name__)


class EcommerceAgent(BaseAgent):
    """E-commerce specialist agent for customer support and order management."""

    agent_name = "GmailMind E-commerce Agent"
    industry = "ecommerce"
    supported_tiers = ["tier2", "tier3"]

    # Email classification patterns for e-commerce
    _ECOMMERCE_CATEGORIES = {
        "order_inquiry": [
            r"order",
            r"order.*status",
            r"where.*order",
            r"track.*order",
            r"order.*number",
            r"purchase",
            r"order.*confirmation",
            r"when.*arrive",
            r"delivery",
        ],
        "refund_request": [
            r"refund",
            r"return",
            r"money back",
            r"cancel.*order",
            r"want.*refund",
            r"charge.*wrong",
            r"incorrect.*charge",
            r"not.*received",
            r"damaged",
            r"defective",
        ],
        "complaint": [
            r"complaint",
            r"unhappy",
            r"disappointed",
            r"terrible",
            r"worst",
            r"problem with",
            r"issue with",
            r"not working",
            r"broken",
            r"wrong.*item",
            r"missing.*item",
        ],
        "shipping_inquiry": [
            r"shipping",
            r"delivery",
            r"tracking",
            r"dispatch",
            r"shipped",
            r"courier",
            r"package",
            r"parcel",
            r"when.*deliver",
            r"track.*package",
        ],
        "supplier_email": [
            r"invoice",
            r"stock",
            r"inventory",
            r"supply",
            r"wholesale",
            r"bulk order",
            r"restock",
            r"purchase order",
            r"payment.*due",
            r"outstanding.*payment",
        ],
        "product_inquiry": [
            r"product",
            r"item",
            r"available",
            r"in stock",
            r"price",
            r"discount",
            r"offer",
            r"specifications",
            r"size",
            r"color",
            r"variant",
        ],
        "review_feedback": [
            r"review",
            r"feedback",
            r"rating",
            r"experience",
            r"recommend",
            r"happy.*with",
            r"satisfied",
        ],
    }

    def __init__(self):
        """Initialize E-commerce Agent with order tracking."""
        super().__init__()
        self.order_tracker = OrderTracker()
        logger.info("[EcommerceAgent] Initialized")

    def get_system_prompt(self, tier: str) -> str:
        """Get system prompt for the E-commerce Agent.

        Args:
            tier: User's subscription tier

        Returns:
            System prompt string
        """
        return """You are an expert e-commerce customer support email assistant.
You help online businesses handle customer inquiries, process
refund requests, resolve complaints, and manage supplier emails.
Always be empathetic, solution-focused, and professional.
For complaints: acknowledge first, then solve.
For refunds: be clear about the process and timeline.
For order inquiries: provide accurate and helpful information."""

    def get_available_tools(self, tier: str) -> list:
        """Get available tools based on subscription tier.

        Args:
            tier: User's subscription tier

        Returns:
            List of available tool names
        """
        tier2_tools = [
            'read_emails',
            'label_email',
            'search_emails',
            'reply_to_email',
            'create_draft',
            'send_escalation_alert',
            'schedule_followup',
        ]

        tier3_tools = tier2_tools + [
            'send_email',
            'get_crm_contact',
            'update_crm',
        ]

        if tier == "tier3":
            return tier3_tools
        else:
            return tier2_tools

    def classify_email(self, email: dict) -> str:
        """Classify e-commerce email by content.

        Args:
            email: Email dict with 'subject' and 'body'

        Returns:
            Category string (order_inquiry, refund_request, etc.) or 'other'
        """
        subject = email.get("subject", "").lower()
        body = email.get("body", "").lower()
        combined_text = f"{subject} {body}"

        # Check each category
        for category, patterns in self._ECOMMERCE_CATEGORIES.items():
            for pattern in patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    logger.debug(
                        f"[EcommerceAgent] Classified as {category} (matched: {pattern})"
                    )
                    return category

        return "other"

    def process_email(
        self,
        email: dict,
        user_config: dict,
        tier: str,
        user_id: str
    ) -> dict:
        """Process an e-commerce email and take appropriate action.

        Args:
            email: Email dict
            user_config: User configuration
            tier: Subscription tier
            user_id: User identifier

        Returns:
            Action dict describing what was done
        """
        category = self.classify_email(email)
        sender_email = email.get("from", "unknown@example.com")
        subject = email.get("subject", "No subject")
        body = email.get("body", "")

        logger.info(
            f"[EcommerceAgent] Processing {category} email from {sender_email}"
        )

        # Order inquiry
        if category == "order_inquiry":
            return self._handle_order_inquiry(
                email, user_id, sender_email, user_config
            )

        # Refund request
        elif category == "refund_request":
            return self._handle_refund_request(
                email, user_id, sender_email, user_config
            )

        # Complaint
        elif category == "complaint":
            return self._handle_complaint(
                email, user_id, sender_email, user_config
            )

        # Shipping inquiry
        elif category == "shipping_inquiry":
            return self._handle_shipping_inquiry(
                email, user_id, sender_email, user_config
            )

        # Supplier email
        elif category == "supplier_email":
            return self._handle_supplier_email(
                email, user_id, sender_email, user_config
            )

        # Review feedback
        elif category == "review_feedback":
            return self._handle_review_feedback(
                email, user_id, sender_email, user_config
            )

        # Default: label and archive
        else:
            self.log_action(
                user_id,
                "label_email",
                {"email": subject, "label": "Ecommerce/Other"},
                outcome="success"
            )
            return {
                "action": "labeled",
                "category": category,
                "label": "Ecommerce/Other",
            }

    def _handle_order_inquiry(
        self,
        email: dict,
        user_id: str,
        sender_email: str,
        user_config: dict
    ) -> dict:
        """Handle order inquiry emails."""
        body = email.get("body", "")
        subject = email.get("subject", "")

        # Extract order ID
        order_id = self.order_tracker.extract_order_id(f"{subject} {body}")
        if not order_id:
            order_id = "UNKNOWN"

        # Log inquiry
        inquiry_id = self.order_tracker.log_order_inquiry(
            user_id, sender_email, order_id, "status"
        )

        # Log action
        self.log_action(
            user_id,
            "order_inquiry_received",
            {
                "inquiry_id": inquiry_id,
                "customer_email": sender_email,
                "order_id": order_id,
            },
            outcome="success"
        )

        return {
            "action": "order_inquiry_logged",
            "inquiry_id": inquiry_id,
            "order_id": order_id,
            "suggested_reply": "order_confirmation template",
        }

    def _handle_refund_request(
        self,
        email: dict,
        user_id: str,
        sender_email: str,
        user_config: dict
    ) -> dict:
        """Handle refund request emails."""
        body = email.get("body", "")
        subject = email.get("subject", "")

        # Extract order ID
        order_id = self.order_tracker.extract_order_id(f"{subject} {body}")
        if not order_id:
            order_id = "UNKNOWN"

        # Extract reason (simplified)
        reason = "Customer requested refund"

        # Log refund request
        refund_id = self.order_tracker.log_refund_request(
            user_id, sender_email, order_id, reason
        )

        # Log action
        self.log_action(
            user_id,
            "refund_request_received",
            {
                "refund_id": refund_id,
                "customer_email": sender_email,
                "order_id": order_id,
                "reason": reason,
            },
            outcome="success"
        )

        return {
            "action": "refund_request_logged",
            "refund_id": refund_id,
            "order_id": order_id,
            "suggested_reply": "refund_initiated template",
        }

    def _handle_complaint(
        self,
        email: dict,
        user_id: str,
        sender_email: str,
        user_config: dict
    ) -> dict:
        """Handle customer complaint emails."""
        body = email.get("body", "")
        subject = email.get("subject", "")

        # Detect priority (simplified)
        priority = "medium"
        critical_keywords = ["furious", "outraged", "legal", "lawsuit", "scam", "fraud"]
        high_keywords = ["disappointed", "unhappy", "terrible", "worst", "angry"]

        body_lower = body.lower()
        if any(word in body_lower for word in critical_keywords):
            priority = "critical"
        elif any(word in body_lower for word in high_keywords):
            priority = "high"

        # Log complaint
        complaint_id = self.order_tracker.log_complaint(
            user_id, sender_email, f"{subject}: {body[:200]}", priority
        )

        # Log action
        self.log_action(
            user_id,
            "complaint_received",
            {
                "complaint_id": complaint_id,
                "customer_email": sender_email,
                "priority": priority,
            },
            outcome="success"
        )

        return {
            "action": "complaint_logged",
            "complaint_id": complaint_id,
            "priority": priority,
            "suggested_reply": "complaint_acknowledged template",
            "escalate": priority in ["critical", "high"],
        }

    def _handle_shipping_inquiry(
        self,
        email: dict,
        user_id: str,
        sender_email: str,
        user_config: dict
    ) -> dict:
        """Handle shipping inquiry emails."""
        body = email.get("body", "")
        subject = email.get("subject", "")

        # Extract order ID
        order_id = self.order_tracker.extract_order_id(f"{subject} {body}")
        if not order_id:
            order_id = "UNKNOWN"

        # Log inquiry
        inquiry_id = self.order_tracker.log_order_inquiry(
            user_id, sender_email, order_id, "shipping"
        )

        # Log action
        self.log_action(
            user_id,
            "shipping_inquiry_received",
            {
                "inquiry_id": inquiry_id,
                "customer_email": sender_email,
                "order_id": order_id,
            },
            outcome="success"
        )

        return {
            "action": "shipping_inquiry_logged",
            "inquiry_id": inquiry_id,
            "order_id": order_id,
            "suggested_reply": "shipping_update template",
        }

    def _handle_supplier_email(
        self,
        email: dict,
        user_id: str,
        sender_email: str,
        user_config: dict
    ) -> dict:
        """Handle supplier email communications."""
        subject = email.get("subject", "")

        # Log action
        self.log_action(
            user_id,
            "supplier_email_received",
            {
                "supplier_email": sender_email,
                "subject": subject,
            },
            outcome="success"
        )

        return {
            "action": "supplier_email_logged",
            "label": "Ecommerce/Supplier",
            "suggested_reply": "supplier_acknowledgment template",
        }

    def _handle_review_feedback(
        self,
        email: dict,
        user_id: str,
        sender_email: str,
        user_config: dict
    ) -> dict:
        """Handle customer review and feedback emails."""
        body = email.get("body", "").lower()

        # Detect sentiment (simplified)
        positive_keywords = ["happy", "love", "amazing", "excellent", "great", "satisfied"]
        negative_keywords = ["disappointed", "unhappy", "terrible", "worst", "bad"]

        is_positive = any(word in body for word in positive_keywords)
        is_negative = any(word in body for word in negative_keywords)

        sentiment = "positive" if is_positive else ("negative" if is_negative else "neutral")

        # Log action
        self.log_action(
            user_id,
            "review_received",
            {
                "customer_email": sender_email,
                "sentiment": sentiment,
            },
            outcome="success"
        )

        return {
            "action": "review_logged",
            "sentiment": sentiment,
            "label": f"Ecommerce/Reviews/{sentiment.title()}",
            "escalate": is_negative,
        }
