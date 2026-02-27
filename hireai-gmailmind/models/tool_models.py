"""Pydantic models for Calendar, CRM, and Alert tool inputs and outputs."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ===========================================================================
# Calendar Models
# ===========================================================================


class FreeSlot(BaseModel):
    """A single available time slot on the calendar."""

    start: datetime = Field(..., description="Slot start time (UTC)")
    end: datetime = Field(..., description="Slot end time (UTC)")
    duration_minutes: int = Field(..., description="Duration in minutes")


class CalendarEventResponse(BaseModel):
    """Response after creating a calendar event."""

    event_id: str = Field(..., description="Google Calendar event ID")
    html_link: str = Field(default="", description="Link to open the event")
    status: str = Field(default="confirmed", description="Event status")


class FollowUpScheduleResponse(BaseModel):
    """Response after scheduling a follow-up."""

    follow_up_id: int = Field(..., description="Database record ID")
    email_id: str = Field(..., description="Gmail message ID this relates to")
    due_time: datetime = Field(..., description="When the follow-up is due")
    success: bool = Field(default=True)
    reason: str = Field(default="", description="Failure reason if not successful")


# ===========================================================================
# CRM Models
# ===========================================================================


class ContactProfile(BaseModel):
    """A contact record from the CRM (HubSpot or local DB)."""

    email: str = Field(..., description="Contact email address")
    name: Optional[str] = Field(None, description="Full name")
    company: Optional[str] = Field(None, description="Company name")
    phone: Optional[str] = Field(None, description="Phone number")
    job_title: Optional[str] = Field(None, description="Job title")
    lifecycle_stage: Optional[str] = Field(None, description="e.g. lead, customer, evangelist")
    last_activity: Optional[datetime] = Field(None, description="Last recorded activity")
    tags: list[str] = Field(default_factory=list, description="Contact tags/labels")
    source: str = Field(default="local", description="Data source: 'hubspot' or 'local'")
    properties: dict = Field(default_factory=dict, description="Additional CRM properties")


class CrmUpdateResponse(BaseModel):
    """Response after a CRM update operation."""

    success: bool = Field(default=True)
    source: str = Field(default="local", description="Which backend was updated")
    action: str = Field(..., description="The action that was performed")
    reason: str = Field(default="", description="Failure reason if not successful")


# ===========================================================================
# Alert / Escalation Models
# ===========================================================================


class EscalationAlertResponse(BaseModel):
    """Response after sending an escalation alert."""

    success: bool = Field(default=True)
    channel: str = Field(..., description="Channel used: 'slack' or 'whatsapp'")
    reason: str = Field(default="", description="Failure reason if not successful")
