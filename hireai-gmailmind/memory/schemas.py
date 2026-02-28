"""Pydantic models for the memory system.

These schemas are used for API serialization and for passing data between
the memory layer and the rest of the application. They mirror (but are
separate from) the SQLAlchemy ORM models in models/schemas.py.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sender Profile
# ---------------------------------------------------------------------------

class SenderProfileBase(BaseModel):
    """Fields common to create and read operations."""

    email: str = Field(..., description="Sender email address")
    name: Optional[str] = Field(None, description="Display name")
    company: Optional[str] = Field(None, description="Company or organization")
    tags: list[str] = Field(default_factory=list, description="Classification tags")


class SenderProfileCreate(SenderProfileBase):
    """Schema for creating a new sender profile."""

    history: list[dict] = Field(default_factory=list, description="Initial history entries")


class SenderProfileUpdate(BaseModel):
    """Schema for partial updates to a sender profile."""

    name: Optional[str] = None
    company: Optional[str] = None
    tags: Optional[list[str]] = None
    history_entry: Optional[dict] = Field(
        None, description="A single new history entry to append"
    )


class SenderProfileRead(SenderProfileBase):
    """Schema returned when reading a sender profile."""

    id: int
    history: list[dict] = Field(default_factory=list)
    last_interaction: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Action Log
# ---------------------------------------------------------------------------

class ActionLogCreate(BaseModel):
    """Schema for recording a new agent action."""

    email_from: str = Field(..., description="Email address that triggered the action")
    action_taken: str = Field(..., description="Description of the action")
    tool_used: str = Field(..., description="Name of the tool invoked")
    outcome: Optional[str] = Field(None, description="Result or error message")
    metadata: Optional[dict] = Field(None, description="Extra context")


class ActionLogRead(ActionLogCreate):
    """Schema returned when reading an action log entry."""

    id: int
    timestamp: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Follow-Up
# ---------------------------------------------------------------------------

class FollowUpCreate(BaseModel):
    """Schema for scheduling a new follow-up."""

    email_id: str = Field(..., description="Gmail message ID")
    sender: str = Field(..., description="Sender email address")
    due_time: datetime = Field(..., description="When the follow-up is due")
    note: Optional[str] = Field(None, description="Reminder note")


class FollowUpUpdate(BaseModel):
    """Schema for updating a follow-up."""

    due_time: Optional[datetime] = None
    note: Optional[str] = None
    status: Optional[str] = Field(None, description="pending | completed | cancelled")


class FollowUpRead(FollowUpCreate):
    """Schema returned when reading a follow-up."""

    id: int
    status: str = "pending"
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Email Embedding
# ---------------------------------------------------------------------------

class EmailEmbeddingCreate(BaseModel):
    """Schema for storing a new email embedding."""

    email_id: str
    thread_id: Optional[str] = None
    sender: str
    subject: Optional[str] = None
    body_preview: Optional[str] = None
    embedding: list[float] = Field(..., description="1536-dim embedding vector")


class EmailEmbeddingRead(BaseModel):
    """Schema returned when reading an email embedding record."""

    id: int
    email_id: str
    thread_id: Optional[str] = None
    sender: str
    subject: Optional[str] = None
    body_preview: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SemanticSearchResult(BaseModel):
    """A single result from a semantic search query."""

    email_id: str
    sender: str
    subject: Optional[str] = None
    body_preview: Optional[str] = None
    similarity: float = Field(..., description="Cosine similarity score (0-1)")


# ---------------------------------------------------------------------------
# Convenience aliases — allow ``from memory.schemas import SenderProfile``
# ---------------------------------------------------------------------------

SenderProfile = SenderProfileBase
ActionLog = ActionLogCreate
FollowUp = FollowUpCreate
EmailEmbedding = EmailEmbeddingCreate
