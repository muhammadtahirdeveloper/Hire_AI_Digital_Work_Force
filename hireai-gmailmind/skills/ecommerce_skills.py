"""E-commerce specific skills for customer support and reporting."""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text

from config.database import SessionLocal
from skills.base_skills import BaseSkills

logger = logging.getLogger(__name__)


class EcommerceSkills(BaseSkills):
    """Specialized skills for E-commerce agents."""

    def extract_order_id(self, text: str) -> Optional[str]:
        """Extract order ID from email text using multiple regex patterns.

        Args:
            text: Email subject or body text.

        Returns:
            Order ID string or None if not found.
        """
        # Pattern 1: #12345 (hash followed by 4-10 digits)
        match = re.search(r'#(\d{4,10})', text)
        if match:
            order_id = match.group(1)
            logger.info("EcommerceSkills: Extracted order ID: %s (pattern: #)", order_id)
            return order_id

        # Pattern 2: ORDER-12345 or ORDER_ABC123
        match = re.search(r'ORDER[-_](\w+)', text, re.IGNORECASE)
        if match:
            order_id = match.group(1)
            logger.info("EcommerceSkills: Extracted order ID: %s (pattern: ORDER-)", order_id)
            return order_id

        # Pattern 3: ORD-12345 or ORD_ABC123
        match = re.search(r'ORD[-_](\w+)', text, re.IGNORECASE)
        if match:
            order_id = match.group(1)
            logger.info("EcommerceSkills: Extracted order ID: %s (pattern: ORD-)", order_id)
            return order_id

        # Pattern 4: Order number: 12345 or Order ID: ABC123
        # Require "number", "id", or "#" to be present and followed by colon or space
        match = re.search(
            r'order\s+(?:number|id|#)\s*[:]\s*(\w{3,})',
            text,
            re.IGNORECASE
        )
        if match:
            order_id = match.group(1)
            logger.info("EcommerceSkills: Extracted order ID: %s (pattern: order number)", order_id)
            return order_id

        logger.info("EcommerceSkills: No order ID found in text")
        return None

    def detect_customer_sentiment(self, email_body: str) -> str:
        """Detect customer sentiment from email body.

        Args:
            email_body: Email body text.

        Returns:
            Sentiment level: 'very_negative', 'negative', 'neutral', or 'positive'.
        """
        body_lower = email_body.lower()

        # Very negative - extreme dissatisfaction or threats
        very_negative_keywords = [
            'furious', 'outraged', 'legal', 'lawsuit', 'scam',
            'fraud', 'attorney', 'lawyer', 'sue', 'report you',
            'better business bureau', 'consumer protection', 'disgusting'
        ]

        for keyword in very_negative_keywords:
            if keyword in body_lower:
                logger.info(
                    "EcommerceSkills: Very negative sentiment detected (keyword: %s)",
                    keyword
                )
                return 'very_negative'

        # Negative - dissatisfaction and complaints
        negative_keywords = [
            'disappointed', 'unhappy', 'terrible', 'worst', 'angry',
            'frustrated', 'upset', 'unacceptable', 'horrible', 'awful',
            'poor quality', 'never again', 'waste of money', 'regret'
        ]

        for keyword in negative_keywords:
            if keyword in body_lower:
                logger.info(
                    "EcommerceSkills: Negative sentiment detected (keyword: %s)",
                    keyword
                )
                return 'negative'

        # Positive - satisfaction and praise
        positive_keywords = [
            'happy', 'love', 'amazing', 'excellent', 'great',
            'fantastic', 'wonderful', 'perfect', 'impressed', 'thrilled',
            'thank you', 'appreciate', 'satisfied', 'recommend'
        ]

        for keyword in positive_keywords:
            if keyword in body_lower:
                logger.info(
                    "EcommerceSkills: Positive sentiment detected (keyword: %s)",
                    keyword
                )
                return 'positive'

        # Default to neutral
        logger.info("EcommerceSkills: Neutral sentiment (no strong indicators)")
        return 'neutral'

    def generate_weekly_ecommerce_report(self, user_id: str) -> dict:
        """Generate weekly e-commerce activity report.

        Queries the last 7 days of e-commerce activity.

        Args:
            user_id: User ID to generate report for.

        Returns:
            Dict with report statistics.
        """
        db = SessionLocal()
        try:
            seven_days_ago = (
                datetime.now(timezone.utc) - timedelta(days=7)
            ).strftime("%Y-%m-%d")

            # Order inquiries in last 7 days
            inquiries_result = db.execute(
                text("""
                    SELECT COUNT(*) FROM order_inquiries
                    WHERE user_id = :user_id
                      AND created_at >= :since
                """),
                {"user_id": user_id, "since": seven_days_ago}
            ).fetchone()
            order_inquiries = inquiries_result[0] if inquiries_result else 0

            # Refund requests in last 7 days
            refunds_result = db.execute(
                text("""
                    SELECT COUNT(*) FROM refund_requests
                    WHERE user_id = :user_id
                      AND created_at >= :since
                """),
                {"user_id": user_id, "since": seven_days_ago}
            ).fetchone()
            refund_requests = refunds_result[0] if refunds_result else 0

            # Complaints in last 7 days
            complaints_result = db.execute(
                text("""
                    SELECT COUNT(*) FROM customer_complaints
                    WHERE user_id = :user_id
                      AND created_at >= :since
                """),
                {"user_id": user_id, "since": seven_days_ago}
            ).fetchone()
            complaints = complaints_result[0] if complaints_result else 0

            # Resolved complaints in last 7 days
            resolved_result = db.execute(
                text("""
                    SELECT COUNT(*) FROM customer_complaints
                    WHERE user_id = :user_id
                      AND status = 'resolved'
                      AND updated_at >= :since
                """),
                {"user_id": user_id, "since": seven_days_ago}
            ).fetchone()
            resolved = resolved_result[0] if resolved_result else 0

            # Positive reviews (simplified - count from existing data)
            # In a real system, this would query a reviews table
            positive_reviews = 0  # Placeholder

            report = {
                "order_inquiries": order_inquiries,
                "refund_requests": refund_requests,
                "complaints": complaints,
                "resolved": resolved,
                "positive_reviews": positive_reviews,
                "period": "Last 7 days",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(
                "EcommerceSkills: Generated weekly report for user=%s: %s",
                user_id, report
            )

            return report

        except Exception as exc:
            logger.exception("EcommerceSkills: Error generating weekly report")
            return {
                "order_inquiries": 0,
                "refund_requests": 0,
                "complaints": 0,
                "resolved": 0,
                "positive_reviews": 0,
                "error": str(exc),
            }
        finally:
            db.close()

    def format_report_for_whatsapp(self, report: dict) -> str:
        """Format weekly report for WhatsApp delivery.

        Args:
            report: Report dict from generate_weekly_ecommerce_report().

        Returns:
            Formatted WhatsApp message string.
        """
        inquiries = report.get("order_inquiries", 0)
        refunds = report.get("refund_requests", 0)
        complaints = report.get("complaints", 0)
        resolved = report.get("resolved", 0)
        reviews = report.get("positive_reviews", 0)

        message = f"""🛒 Weekly E-commerce Report
===========================
📧 Order Inquiries: {inquiries}
💸 Refund Requests: {refunds}
😤 Complaints: {complaints}
✅ Resolved: {resolved}
⭐ Positive Reviews: {reviews}

Period: {report.get("period", "Last 7 days")}"""

        return message
