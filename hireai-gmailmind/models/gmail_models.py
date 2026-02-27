"""Pydantic models for Gmail tool inputs and outputs."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class EmailAddress(BaseModel):
    """Represents an email address with optional display name."""

    email: str
    name: Optional[str] = None


class Email(BaseModel):
    """Represents a single Gmail message."""

    id: str = Field(..., description="Gmail message ID")
    thread_id: str = Field(..., description="Gmail thread ID")
    subject: str = Field(default="", description="Email subject line")
    sender: EmailAddress = Field(..., description="Sender address")
    to: list[EmailAddress] = Field(default_factory=list, description="Recipient list")
    date: Optional[datetime] = Field(None, description="Date the email was sent")
    snippet: str = Field(default="", description="Short preview of the email body")
    body: str = Field(default="", description="Full email body text")
    labels: list[str] = Field(default_factory=list, description="Gmail label IDs")
    is_read: bool = Field(default=False, description="Whether the email has been read")


class SendEmailResponse(BaseModel):
    """Response after sending an email."""

    message_id: str = Field(..., description="ID of the sent message")
    thread_id: str = Field(..., description="Thread ID of the sent message")
    status: str = Field(default="sent", description="Status of the operation")


class DraftResponse(BaseModel):
    """Response after creating a draft."""

    draft_id: str = Field(..., description="ID of the created draft")
    message_id: str = Field(..., description="ID of the draft message")
    status: str = Field(default="created", description="Status of the operation")


class LabelResult(BaseModel):
    """Result of a label operation."""

    email_id: str = Field(..., description="ID of the labeled email")
    labels_added: list[str] = Field(default_factory=list)
    labels_removed: list[str] = Field(default_factory=list)
    archived: bool = Field(default=False)
    success: bool = Field(default=True)
