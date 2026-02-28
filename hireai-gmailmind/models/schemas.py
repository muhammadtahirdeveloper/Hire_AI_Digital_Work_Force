"""SQLAlchemy ORM models for the GmailMind memory system.

Tables:
    sender_profiles  — Long-term memory per sender (email, company, history, tags)
    action_logs      — Audit trail of every agent action
    follow_ups       — Scheduled follow-up reminders
    email_embeddings — pgvector storage for semantic search on past emails
"""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from config.database import Base


class SenderProfile(Base):
    """Long-term memory about a specific email sender."""

    __tablename__ = "sender_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(320), nullable=False, unique=True)
    name = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    history = Column(JSONB, nullable=False, default=list, server_default="[]")
    last_interaction = Column(DateTime(timezone=True), nullable=True)
    tags = Column(ARRAY(String), nullable=False, default=list, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_sender_profiles_email", "email"),
        Index("ix_sender_profiles_company", "company"),
        Index("ix_sender_profiles_last_interaction", "last_interaction"),
    )

    def __repr__(self) -> str:
        return f"<SenderProfile(email={self.email!r}, name={self.name!r})>"


class ActionLog(Base):
    """Audit log of every action the agent has taken."""

    __tablename__ = "action_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    email_from = Column(String(320), nullable=False)
    action_taken = Column(String(255), nullable=False)
    tool_used = Column(String(128), nullable=False)
    outcome = Column(Text, nullable=True)
    extra_metadata = Column("metadata", JSONB, nullable=True)

    __table_args__ = (
        Index("ix_action_logs_email_from", "email_from"),
        Index("ix_action_logs_timestamp", "timestamp"),
        Index("ix_action_logs_tool_used", "tool_used"),
    )

    def __repr__(self) -> str:
        return (
            f"<ActionLog(action={self.action_taken!r}, "
            f"tool={self.tool_used!r}, at={self.timestamp})>"
        )


class FollowUp(Base):
    """A scheduled follow-up reminder tied to an email."""

    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(String(128), nullable=False)
    sender = Column(String(320), nullable=False)
    due_time = Column(DateTime(timezone=True), nullable=False)
    note = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="pending", server_default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_follow_ups_email_id", "email_id"),
        Index("ix_follow_ups_sender", "sender"),
        Index("ix_follow_ups_due_time", "due_time"),
        Index("ix_follow_ups_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<FollowUp(email_id={self.email_id!r}, "
            f"sender={self.sender!r}, due={self.due_time}, status={self.status!r})>"
        )


class EmailEmbedding(Base):
    """Stores vector embeddings of emails for semantic search via pgvector."""

    __tablename__ = "email_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(String(128), nullable=False, unique=True)
    thread_id = Column(String(128), nullable=True)
    sender = Column(String(320), nullable=False)
    subject = Column(Text, nullable=True)
    body_preview = Column(Text, nullable=True)
    embedding = Column(Vector(1536), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_email_embeddings_email_id", "email_id"),
        Index("ix_email_embeddings_sender", "sender"),
        Index("ix_email_embeddings_thread_id", "thread_id"),
    )

    def __repr__(self) -> str:
        return f"<EmailEmbedding(email_id={self.email_id!r}, sender={self.sender!r})>"
