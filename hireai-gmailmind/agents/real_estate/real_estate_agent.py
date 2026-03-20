"""Real Estate Agent for GmailMind.

Handles property inquiries, viewing scheduling, rental applications,
maintenance requests, and real estate communications.
"""

import logging
import re
from typing import Optional

from agents.base_agent import BaseAgent
from agents.real_estate.property_tracker import PropertyTracker
from agents.real_estate.real_estate_templates import REAL_ESTATE_TEMPLATES

logger = logging.getLogger(__name__)


class RealEstateAgent(BaseAgent):
    """Real Estate specialist agent for property management and inquiries."""

    agent_name = "GmailMind Real Estate Agent"
    industry = "real_estate"
    supported_tiers = ["tier2", "tier3"]

    # Email classification patterns for real estate
    # NOTE: Order matters! More specific patterns should come first.
    _REAL_ESTATE_CATEGORIES = {
        "viewing_request": [
            r"schedule.*viewing",
            r"book.*viewing",
            r"arrange.*visit",
            r"can i see",
            r"want to view",
            r"viewing.*available",
            r"show.*property",
            r"visit.*property",
        ],
        "maintenance_request": [
            r"repair",
            r"broken",
            r"not working",
            r"maintenance",
            r"leak",
            r"damage",
            r"fix",
            r"issue with",
            r"problem with",
            r"heating",
            r"plumbing",
            r"electrical",
        ],
        "rental_application": [
            r"rental application",
            r"apply.*rent",
            r"tenant application",
            r"application form",
            r"documents.*rent",
            r"references",
        ],
        "offer_submission": [
            r"offer",
            r"willing to pay",
            r"bid",
            r"purchase price",
            r"offer.*property",
            r"make an offer",
        ],
        "lease_inquiry": [
            r"lease",
            r"contract",
            r"tenancy",
            r"agreement",
            r"renew",
            r"renewal",
            r"end of lease",
        ],
        "landlord_message": [
            r"landlord",
            r"owner",
            r"property manager",
            r"rent.*increase",
            r"notice",
            r"eviction",
        ],
        "property_inquiry": [
            r"interested in",
            r"property",
            r"viewing",
            r"visit",
            r"available",
            r"for sale",
            r"for rent",
            r"listing",
            r"how much",
            r"price",
            r"bedroom",
            r"apartment",
            r"house",
        ],
    }

    def __init__(self):
        """Initialize Real Estate Agent with property tracking."""
        super().__init__()
        self.property_tracker = PropertyTracker()
        logger.info("[RealEstateAgent] Initialized")

    def get_system_prompt(self, tier: str) -> str:
        """Get system prompt for the Real Estate Agent.

        Args:
            tier: User's subscription tier

        Returns:
            System prompt string
        """
        return """You are an expert real estate email assistant.
You help real estate agents and property managers handle
property inquiries, schedule viewings, process rental applications,
and manage tenant communications professionally.
Always be helpful, responsive, and professional.
For property inquiries, highlight key features and suggest viewings.
For maintenance requests, acknowledge urgency and set clear timelines."""

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
            'create_calendar_event',
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
        """Classify real estate email by content.

        Args:
            email: Email dict with 'subject' and 'body'

        Returns:
            Category string (property_inquiry, viewing_request, etc.) or 'other'
        """
        subject = email.get("subject", "").lower()
        body = email.get("body", "").lower()
        combined_text = f"{subject} {body}"

        # Check each category
        for category, patterns in self._REAL_ESTATE_CATEGORIES.items():
            for pattern in patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    logger.debug(
                        f"[RealEstateAgent] Classified as {category} (matched: {pattern})"
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
        """Process a real estate email and take appropriate action.

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

        logger.info(
            f"[RealEstateAgent] Processing {category} email from {sender_email}"
        )

        # Property inquiry
        if category == "property_inquiry":
            return self._handle_property_inquiry(
                email, user_id, sender_email, user_config
            )

        # Viewing request
        elif category == "viewing_request":
            return self._handle_viewing_request(
                email, user_id, sender_email, user_config
            )

        # Rental application
        elif category == "rental_application":
            return self._handle_rental_application(
                email, user_id, sender_email, user_config
            )

        # Maintenance request
        elif category == "maintenance_request":
            return self._handle_maintenance_request(
                email, user_id, sender_email, user_config
            )

        # Offer submission
        elif category == "offer_submission":
            return self._handle_offer_submission(
                email, user_id, sender_email, user_config
            )

        # Default: label and archive
        else:
            self.log_action(
                user_id,
                "label_email",
                {"email": subject, "label": "RealEstate/Other"},
                outcome="success"
            )
            return {
                "action": "labeled",
                "category": category,
                "label": "RealEstate/Other",
            }

    def _handle_property_inquiry(
        self,
        email: dict,
        user_id: str,
        sender_email: str,
        user_config: dict
    ) -> dict:
        """Handle property inquiry emails."""
        # Extract property address from email (simplified)
        body = email.get("body", "")
        property_address = "Property [Address from listing]"

        # Log inquiry
        inquiry_id = self.property_tracker.log_inquiry(
            user_id, sender_email, property_address, "general"
        )

        # Log action
        self.log_action(
            user_id,
            "property_inquiry_received",
            {
                "inquiry_id": inquiry_id,
                "client_email": sender_email,
                "property": property_address,
            },
            outcome="success"
        )

        return {
            "action": "property_inquiry_logged",
            "inquiry_id": inquiry_id,
            "property_address": property_address,
            "suggested_reply": "property_inquiry_reply template",
        }

    def _handle_viewing_request(
        self,
        email: dict,
        user_id: str,
        sender_email: str,
        user_config: dict
    ) -> dict:
        """Handle viewing request emails.

        1. Log the inquiry
        2. Find available calendar slots
        3. Create a 30-minute viewing event
        4. Return confirmation with calendar link
        """
        property_address = "Property [Address from context]"

        # Log inquiry
        inquiry_id = self.property_tracker.log_inquiry(
            user_id, sender_email, property_address, "viewing"
        )

        # Try to schedule a viewing via calendar
        calendar_event = None
        scheduled_slot = None
        try:
            from tools.calendar_tools import build_calendar_service, get_available_slots, create_calendar_event
            from datetime import datetime, timedelta, timezone as tz

            cal_service = build_calendar_service(user_id)
            if cal_service:
                now = datetime.now(tz.utc)
                slots = get_available_slots(
                    service=cal_service,
                    date_range_start=now,
                    date_range_end=now + timedelta(days=7),
                    duration_minutes=30,
                )

                if slots:
                    scheduled_slot = slots[0]["start"]
                    slot_dt = datetime.fromisoformat(scheduled_slot)
                    if slot_dt.tzinfo is None:
                        slot_dt = slot_dt.replace(tzinfo=tz.utc)
                    end_dt = slot_dt + timedelta(minutes=30)

                    calendar_event = create_calendar_event(
                        service=cal_service,
                        title=f"Property Viewing: {property_address}",
                        start_time=slot_dt,
                        end_time=end_dt,
                        attendees=[sender_email],
                        description=f"Property viewing at {property_address}.\nClient: {sender_email}",
                    )
                    logger.info(
                        "[RealEstateAgent] Created viewing event for %s at %s",
                        sender_email, scheduled_slot,
                    )
        except Exception as exc:
            logger.warning("[RealEstateAgent] Calendar booking failed: %s", exc)

        # Log action
        self.log_action(
            user_id,
            "viewing_scheduled" if calendar_event else "viewing_request_received",
            {
                "inquiry_id": inquiry_id,
                "client_email": sender_email,
                "scheduled_slot": scheduled_slot,
            },
            outcome="success"
        )

        result = {
            "action": "viewing_scheduled" if calendar_event else "viewing_request_logged",
            "inquiry_id": inquiry_id,
            "suggested_reply": "viewing_confirmation template",
        }
        if calendar_event:
            result["scheduled_slot"] = scheduled_slot
            result["calendar_event_id"] = calendar_event.event_id
            result["calendar_link"] = calendar_event.html_link
        else:
            result["note"] = "Calendar not available — schedule viewing manually"

        return result

    def _handle_rental_application(
        self,
        email: dict,
        user_id: str,
        sender_email: str,
        user_config: dict
    ) -> dict:
        """Handle rental application emails."""
        property_address = "Property [Address from application]"

        # Log inquiry
        inquiry_id = self.property_tracker.log_inquiry(
            user_id, sender_email, property_address, "rental_application"
        )

        # Log action
        self.log_action(
            user_id,
            "rental_application_received",
            {
                "inquiry_id": inquiry_id,
                "applicant_email": sender_email,
                "property": property_address,
            },
            outcome="success"
        )

        return {
            "action": "rental_application_logged",
            "inquiry_id": inquiry_id,
            "suggested_reply": "rental_application_received template",
        }

    def _handle_maintenance_request(
        self,
        email: dict,
        user_id: str,
        sender_email: str,
        user_config: dict
    ) -> dict:
        """Handle maintenance request emails."""
        body = email.get("body", "")

        # Detect urgency (simplified for now)
        urgency = "medium"
        if any(word in body.lower() for word in ["urgent", "emergency", "leak", "flood"]):
            urgency = "high"

        # Log action
        self.log_action(
            user_id,
            "maintenance_request_received",
            {
                "tenant_email": sender_email,
                "urgency": urgency,
            },
            outcome="success"
        )

        return {
            "action": "maintenance_request_logged",
            "urgency": urgency,
            "suggested_reply": "maintenance_request_received template",
            "escalate": urgency == "high",
        }

    def _handle_offer_submission(
        self,
        email: dict,
        user_id: str,
        sender_email: str,
        user_config: dict
    ) -> dict:
        """Handle offer submission emails."""
        # Log action
        self.log_action(
            user_id,
            "offer_submission_received",
            {
                "buyer_email": sender_email,
            },
            outcome="success"
        )

        return {
            "action": "offer_logged",
            "suggested_reply": "offer_received template",
            "note": "Review offer details and forward to seller",
        }
