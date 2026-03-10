"""Real Estate specific skills for property management and reporting."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text

from config.database import SessionLocal
from skills.base_skills import BaseSkills

logger = logging.getLogger(__name__)


class RealEstateSkills(BaseSkills):
    """Specialized skills for Real Estate agents."""

    def format_property_listing(self, property: dict) -> str:
        """Format a property listing for email communication.

        Args:
            property: Dict with property details (address, price, bedrooms, etc.)

        Returns:
            Formatted property description string.
        """
        address = property.get("address", "N/A")
        price = property.get("price", "Contact for price")
        bedrooms = property.get("bedrooms", 0)
        bathrooms = property.get("bathrooms", 0)
        size_sqft = property.get("size_sqft", 0)
        location = property.get("location", "N/A")

        # Format price if numeric
        if isinstance(price, (int, float)):
            price = f"${price:,.0f}"

        formatted = f"""🏠 {address}
💰 Price: {price}
🛏 Bedrooms: {bedrooms} | 🚿 Bathrooms: {bathrooms}
📐 Size: {size_sqft} sqft
📍 Location: {location}"""

        return formatted

    def detect_maintenance_priority(self, description: str) -> str:
        """Detect priority level of maintenance request based on description.

        Args:
            description: Maintenance issue description text.

        Returns:
            Priority level: 'critical', 'high', 'medium', or 'low'.
        """
        desc_lower = description.lower()

        # Critical issues - immediate safety hazards
        critical_keywords = [
            'flood', 'fire', 'gas leak', 'no electricity',
            'no water', 'break-in', 'broken window', 'security',
            'emergency', 'danger', 'carbon monoxide'
        ]

        for keyword in critical_keywords:
            if keyword in desc_lower:
                logger.info(
                    "RealEstateSkills: Critical priority detected (keyword: %s)",
                    keyword
                )
                return 'critical'

        # High priority - major functionality issues
        high_keywords = [
            'heating', 'no hot water', 'roof leak', 'broken lock',
            'ac not working', 'air conditioning', 'sewage', 'major leak',
            'electrical issue', 'power outage'
        ]

        for keyword in high_keywords:
            if keyword in desc_lower:
                logger.info(
                    "RealEstateSkills: High priority detected (keyword: %s)",
                    keyword
                )
                return 'high'

        # Medium priority - functional issues
        medium_keywords = [
            'appliance', 'plumbing', 'pest', 'leak', 'faucet',
            'toilet', 'sink', 'dishwasher', 'refrigerator', 'rodent',
            'insect', 'mold', 'noise'
        ]

        for keyword in medium_keywords:
            if keyword in desc_lower:
                logger.info(
                    "RealEstateSkills: Medium priority detected (keyword: %s)",
                    keyword
                )
                return 'medium'

        # Default to low priority
        logger.info("RealEstateSkills: Low priority (no urgent keywords found)")
        return 'low'

    def generate_weekly_property_report(self, user_id: str) -> dict:
        """Generate weekly property management report.

        Queries the last 7 days of property activity.

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

            # New inquiries in last 7 days
            inquiries_result = db.execute(
                text("""
                    SELECT COUNT(*) FROM property_inquiries
                    WHERE user_id = :user_id
                      AND created_at >= :since
                """),
                {"user_id": user_id, "since": seven_days_ago}
            ).fetchone()
            new_inquiries = inquiries_result[0] if inquiries_result else 0

            # Viewings scheduled in last 7 days
            viewings_result = db.execute(
                text("""
                    SELECT COUNT(*) FROM property_viewings
                    WHERE user_id = :user_id
                      AND created_at >= :since
                      AND status = 'scheduled'
                """),
                {"user_id": user_id, "since": seven_days_ago}
            ).fetchone()
            viewings_scheduled = viewings_result[0] if viewings_result else 0

            # Maintenance requests in last 7 days
            maintenance_result = db.execute(
                text("""
                    SELECT COUNT(*) FROM maintenance_requests
                    WHERE user_id = :user_id
                      AND created_at >= :since
                """),
                {"user_id": user_id, "since": seven_days_ago}
            ).fetchone()
            maintenance_requests = maintenance_result[0] if maintenance_result else 0

            # Resolved maintenance in last 7 days
            resolved_result = db.execute(
                text("""
                    SELECT COUNT(*) FROM maintenance_requests
                    WHERE user_id = :user_id
                      AND status = 'resolved'
                      AND updated_at >= :since
                """),
                {"user_id": user_id, "since": seven_days_ago}
            ).fetchone()
            resolved = resolved_result[0] if resolved_result else 0

            # Active property listings
            active_result = db.execute(
                text("""
                    SELECT COUNT(*) FROM properties
                    WHERE user_id = :user_id
                      AND status = 'available'
                """),
                {"user_id": user_id}
            ).fetchone()
            active_listings = active_result[0] if active_result else 0

            report = {
                "new_inquiries": new_inquiries,
                "viewings_scheduled": viewings_scheduled,
                "maintenance_requests": maintenance_requests,
                "resolved": resolved,
                "active_listings": active_listings,
                "period": "Last 7 days",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(
                "RealEstateSkills: Generated weekly report for user=%s: %s",
                user_id, report
            )

            return report

        except Exception as exc:
            logger.exception("RealEstateSkills: Error generating weekly report")
            return {
                "new_inquiries": 0,
                "viewings_scheduled": 0,
                "maintenance_requests": 0,
                "resolved": 0,
                "active_listings": 0,
                "error": str(exc),
            }
        finally:
            db.close()

    def format_report_for_whatsapp(self, report: dict) -> str:
        """Format weekly report for WhatsApp delivery.

        Args:
            report: Report dict from generate_weekly_property_report().

        Returns:
            Formatted WhatsApp message string.
        """
        new_inquiries = report.get("new_inquiries", 0)
        viewings = report.get("viewings_scheduled", 0)
        maintenance = report.get("maintenance_requests", 0)
        resolved = report.get("resolved", 0)
        active = report.get("active_listings", 0)

        message = f"""🏠 Weekly Property Report
========================
📧 New Inquiries: {new_inquiries}
👁 Viewings Scheduled: {viewings}
🔧 Maintenance Requests: {maintenance}
✅ Resolved: {resolved}
🏡 Active Listings: {active}

Period: {report.get("period", "Last 7 days")}"""

        return message
