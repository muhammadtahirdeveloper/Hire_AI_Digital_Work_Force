"""Order tracking and customer support management for E-commerce Agent."""

import logging
import re
from typing import Optional

from sqlalchemy import text

from config.database import SessionLocal

logger = logging.getLogger(__name__)


class OrderTracker:
    """Track orders, refunds, complaints, and customer inquiries."""

    def log_order_inquiry(
        self,
        user_id: str,
        customer_email: str,
        order_id: str,
        inquiry_type: str = "general"
    ) -> int:
        """Log an order inquiry.

        Args:
            user_id: User identifier
            customer_email: Customer's email address
            order_id: Order ID
            inquiry_type: Type of inquiry (tracking, status, general, etc.)

        Returns:
            Inquiry ID
        """
        db = SessionLocal()
        try:
            result = db.execute(
                text("""
                    INSERT INTO order_inquiries
                    (user_id, customer_email, order_id, inquiry_type, status)
                    VALUES (:user_id, :customer_email, :order_id, :inquiry_type, 'open')
                    RETURNING id
                """),
                {
                    "user_id": user_id,
                    "customer_email": customer_email,
                    "order_id": order_id,
                    "inquiry_type": inquiry_type,
                }
            )
            inquiry_id = result.fetchone()[0]
            db.commit()
            logger.info(
                f"[OrderTracker] Logged inquiry {inquiry_id} for order {order_id}"
            )
            return inquiry_id

        except Exception as e:
            logger.error(f"[OrderTracker] Error logging inquiry: {e}")
            db.rollback()
            return 0
        finally:
            db.close()

    def log_refund_request(
        self,
        user_id: str,
        customer_email: str,
        order_id: str,
        reason: str
    ) -> int:
        """Log a refund request.

        Args:
            user_id: User identifier
            customer_email: Customer's email address
            order_id: Order ID
            reason: Reason for refund

        Returns:
            Refund ID
        """
        db = SessionLocal()
        try:
            result = db.execute(
                text("""
                    INSERT INTO refund_requests
                    (user_id, customer_email, order_id, reason, status)
                    VALUES (:user_id, :customer_email, :order_id, :reason, 'pending')
                    RETURNING id
                """),
                {
                    "user_id": user_id,
                    "customer_email": customer_email,
                    "order_id": order_id,
                    "reason": reason,
                }
            )
            refund_id = result.fetchone()[0]
            db.commit()
            logger.info(
                f"[OrderTracker] Logged refund request {refund_id} for order {order_id}"
            )
            return refund_id

        except Exception as e:
            logger.error(f"[OrderTracker] Error logging refund request: {e}")
            db.rollback()
            return 0
        finally:
            db.close()

    def log_complaint(
        self,
        user_id: str,
        customer_email: str,
        description: str,
        priority: str = "medium"
    ) -> int:
        """Log a customer complaint.

        Args:
            user_id: User identifier
            customer_email: Customer's email address
            description: Complaint description
            priority: Priority level (low, medium, high, critical)

        Returns:
            Complaint ID
        """
        db = SessionLocal()
        try:
            result = db.execute(
                text("""
                    INSERT INTO customer_complaints
                    (user_id, customer_email, description, priority, status)
                    VALUES (:user_id, :customer_email, :description, :priority, 'open')
                    RETURNING id
                """),
                {
                    "user_id": user_id,
                    "customer_email": customer_email,
                    "description": description,
                    "priority": priority,
                }
            )
            complaint_id = result.fetchone()[0]
            db.commit()
            logger.info(
                f"[OrderTracker] Logged complaint {complaint_id} with priority {priority}"
            )
            return complaint_id

        except Exception as e:
            logger.error(f"[OrderTracker] Error logging complaint: {e}")
            db.rollback()
            return 0
        finally:
            db.close()

    def get_support_summary(self, user_id: str) -> dict:
        """Get summary of customer support activities.

        Args:
            user_id: User identifier

        Returns:
            Summary dict with counts
        """
        db = SessionLocal()
        try:
            # Total inquiries
            inquiries_result = db.execute(
                text("SELECT COUNT(*) FROM order_inquiries WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            total_inquiries = inquiries_result[0] if inquiries_result else 0

            # Pending refunds
            refunds_result = db.execute(
                text("""
                    SELECT COUNT(*) FROM refund_requests
                    WHERE user_id = :user_id AND status = 'pending'
                """),
                {"user_id": user_id}
            ).fetchone()
            pending_refunds = refunds_result[0] if refunds_result else 0

            # Open complaints
            complaints_result = db.execute(
                text("""
                    SELECT COUNT(*) FROM customer_complaints
                    WHERE user_id = :user_id AND status = 'open'
                """),
                {"user_id": user_id}
            ).fetchone()
            open_complaints = complaints_result[0] if complaints_result else 0

            # Resolved today (simplified - counts all resolved)
            resolved_result = db.execute(
                text("""
                    SELECT COUNT(*) FROM customer_complaints
                    WHERE user_id = :user_id AND status = 'resolved'
                """),
                {"user_id": user_id}
            ).fetchone()
            resolved_today = resolved_result[0] if resolved_result else 0

            return {
                "total_inquiries": total_inquiries,
                "pending_refunds": pending_refunds,
                "open_complaints": open_complaints,
                "resolved_today": resolved_today,
            }

        except Exception as e:
            logger.error(f"[OrderTracker] Error getting support summary: {e}")
            return {
                "total_inquiries": 0,
                "pending_refunds": 0,
                "open_complaints": 0,
                "resolved_today": 0,
            }
        finally:
            db.close()

    def extract_order_id(self, text: str) -> Optional[str]:
        """Extract order ID from email text.

        Args:
            text: Email subject or body text

        Returns:
            Order ID string or None if not found
        """
        # Pattern 1: #12345
        match = re.search(r'#(\d{4,10})', text)
        if match:
            return match.group(1)

        # Pattern 2: ORDER-12345 or ORD-12345
        match = re.search(r'(?:ORDER|ORD)[-_](\w+)', text, re.IGNORECASE)
        if match:
            return match.group(1)

        # Pattern 3: Order number: 12345
        match = re.search(r'order\s+(?:number|id|#)?\s*:?\s*(\w+)', text, re.IGNORECASE)
        if match:
            return match.group(1)

        return None
