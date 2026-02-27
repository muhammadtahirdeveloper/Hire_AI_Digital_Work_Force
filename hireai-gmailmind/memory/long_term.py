"""Long-term memory backed by PostgreSQL + pgvector.

Provides persistent storage and retrieval of:
- Sender profiles (interaction history, tags, company info)
- Action logs (audit trail of every agent action)
- Follow-up reminders
- Semantic search over past emails via pgvector embeddings
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from config.database import SessionLocal
from memory.schemas import (
    ActionLogCreate,
    ActionLogRead,
    EmailEmbeddingCreate,
    EmailEmbeddingRead,
    FollowUpCreate,
    FollowUpRead,
    FollowUpUpdate,
    SemanticSearchResult,
    SenderProfileRead,
    SenderProfileUpdate,
)
from models.schemas import ActionLog, EmailEmbedding, FollowUp, SenderProfile

logger = logging.getLogger(__name__)


# ===========================================================================
# Sender Profile Operations
# ===========================================================================


def get_sender_memory(email: str, db: Optional[Session] = None) -> Optional[SenderProfileRead]:
    """Retrieve the full profile for a sender by email address.

    Args:
        email: The sender's email address.
        db: Optional existing session. A new session is created if None.

    Returns:
        A SenderProfileRead if found, otherwise None.
    """
    logger.info("get_sender_memory: Looking up sender %s", email)
    close_db = db is None
    if db is None:
        db = SessionLocal()

    try:
        stmt = select(SenderProfile).where(SenderProfile.email == email)
        profile = db.execute(stmt).scalar_one_or_none()

        if profile is None:
            logger.info("get_sender_memory: No profile found for %s.", email)
            return None

        logger.info("get_sender_memory: Found profile for %s (id=%d).", email, profile.id)
        return SenderProfileRead.model_validate(profile)
    finally:
        if close_db:
            db.close()


def update_sender_memory(
    email: str,
    data: SenderProfileUpdate,
    db: Optional[Session] = None,
) -> SenderProfileRead:
    """Create or update a sender profile.

    If the sender does not exist, a new profile is created. If the sender
    exists, the provided fields are merged. When ``data.history_entry`` is
    set, it is appended to the existing history list.

    Args:
        email: The sender's email address.
        data: Fields to create or update.
        db: Optional existing session.

    Returns:
        The updated (or newly created) SenderProfileRead.
    """
    logger.info("update_sender_memory: Updating sender %s", email)
    close_db = db is None
    if db is None:
        db = SessionLocal()

    try:
        stmt = select(SenderProfile).where(SenderProfile.email == email)
        profile = db.execute(stmt).scalar_one_or_none()

        if profile is None:
            profile = SenderProfile(
                email=email,
                name=data.name,
                company=data.company,
                tags=data.tags or [],
                history=[data.history_entry] if data.history_entry else [],
                last_interaction=datetime.now(timezone.utc),
            )
            db.add(profile)
            logger.info("update_sender_memory: Created new profile for %s.", email)
        else:
            if data.name is not None:
                profile.name = data.name
            if data.company is not None:
                profile.company = data.company
            if data.tags is not None:
                profile.tags = data.tags
            if data.history_entry:
                current_history = profile.history or []
                current_history.append(data.history_entry)
                profile.history = current_history
            profile.last_interaction = datetime.now(timezone.utc)
            logger.info("update_sender_memory: Updated existing profile for %s.", email)

        db.commit()
        db.refresh(profile)
        return SenderProfileRead.model_validate(profile)
    except Exception:
        db.rollback()
        logger.exception("update_sender_memory: Failed for %s.", email)
        raise
    finally:
        if close_db:
            db.close()


# ===========================================================================
# Action Log Operations
# ===========================================================================


def log_action(data: ActionLogCreate, db: Optional[Session] = None) -> ActionLogRead:
    """Record an agent action in the persistent audit log.

    Args:
        data: The action details.
        db: Optional existing session.

    Returns:
        The persisted ActionLogRead.
    """
    logger.info(
        "log_action: %s via %s for %s",
        data.action_taken,
        data.tool_used,
        data.email_from,
    )
    close_db = db is None
    if db is None:
        db = SessionLocal()

    try:
        entry = ActionLog(
            email_from=data.email_from,
            action_taken=data.action_taken,
            tool_used=data.tool_used,
            outcome=data.outcome,
            metadata=data.metadata,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info("log_action: Recorded action id=%d.", entry.id)
        return ActionLogRead.model_validate(entry)
    except Exception:
        db.rollback()
        logger.exception("log_action: Failed to record action.")
        raise
    finally:
        if close_db:
            db.close()


def get_actions_for_sender(
    email: str,
    limit: int = 50,
    db: Optional[Session] = None,
) -> list[ActionLogRead]:
    """Fetch recent actions related to a sender.

    Args:
        email: Sender email address.
        limit: Maximum number of records to return.
        db: Optional existing session.

    Returns:
        List of ActionLogRead, most recent first.
    """
    logger.info("get_actions_for_sender: Querying actions for %s (limit=%d).", email, limit)
    close_db = db is None
    if db is None:
        db = SessionLocal()

    try:
        stmt = (
            select(ActionLog)
            .where(ActionLog.email_from == email)
            .order_by(ActionLog.timestamp.desc())
            .limit(limit)
        )
        rows = db.execute(stmt).scalars().all()
        logger.info("get_actions_for_sender: Found %d actions.", len(rows))
        return [ActionLogRead.model_validate(r) for r in rows]
    finally:
        if close_db:
            db.close()


# ===========================================================================
# Follow-Up Operations
# ===========================================================================


def create_follow_up(
    data: FollowUpCreate,
    db: Optional[Session] = None,
) -> FollowUpRead:
    """Schedule a new follow-up reminder.

    Args:
        data: Follow-up details (email_id, sender, due_time, note).
        db: Optional existing session.

    Returns:
        The created FollowUpRead.
    """
    logger.info(
        "create_follow_up: email_id=%s, sender=%s, due=%s",
        data.email_id,
        data.sender,
        data.due_time,
    )
    close_db = db is None
    if db is None:
        db = SessionLocal()

    try:
        entry = FollowUp(
            email_id=data.email_id,
            sender=data.sender,
            due_time=data.due_time,
            note=data.note,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info("create_follow_up: Created follow-up id=%d.", entry.id)
        return FollowUpRead.model_validate(entry)
    except Exception:
        db.rollback()
        logger.exception("create_follow_up: Failed.")
        raise
    finally:
        if close_db:
            db.close()


def get_pending_follow_ups(db: Optional[Session] = None) -> list[FollowUpRead]:
    """Fetch all pending follow-ups ordered by due time.

    Args:
        db: Optional existing session.

    Returns:
        List of FollowUpRead with status 'pending'.
    """
    logger.info("get_pending_follow_ups: Fetching pending items.")
    close_db = db is None
    if db is None:
        db = SessionLocal()

    try:
        stmt = (
            select(FollowUp)
            .where(FollowUp.status == "pending")
            .order_by(FollowUp.due_time.asc())
        )
        rows = db.execute(stmt).scalars().all()
        logger.info("get_pending_follow_ups: Found %d pending.", len(rows))
        return [FollowUpRead.model_validate(r) for r in rows]
    finally:
        if close_db:
            db.close()


def update_follow_up(
    follow_up_id: int,
    data: FollowUpUpdate,
    db: Optional[Session] = None,
) -> Optional[FollowUpRead]:
    """Update an existing follow-up.

    Args:
        follow_up_id: Primary key of the follow-up record.
        data: Fields to update.
        db: Optional existing session.

    Returns:
        The updated FollowUpRead, or None if not found.
    """
    logger.info("update_follow_up: Updating id=%d.", follow_up_id)
    close_db = db is None
    if db is None:
        db = SessionLocal()

    try:
        entry = db.get(FollowUp, follow_up_id)
        if entry is None:
            logger.warning("update_follow_up: Follow-up id=%d not found.", follow_up_id)
            return None

        if data.due_time is not None:
            entry.due_time = data.due_time
        if data.note is not None:
            entry.note = data.note
        if data.status is not None:
            entry.status = data.status

        db.commit()
        db.refresh(entry)
        logger.info("update_follow_up: Updated id=%d, status=%s.", entry.id, entry.status)
        return FollowUpRead.model_validate(entry)
    except Exception:
        db.rollback()
        logger.exception("update_follow_up: Failed for id=%d.", follow_up_id)
        raise
    finally:
        if close_db:
            db.close()


# ===========================================================================
# Semantic Search (pgvector)
# ===========================================================================


def store_email_embedding(
    data: EmailEmbeddingCreate,
    db: Optional[Session] = None,
) -> EmailEmbeddingRead:
    """Store a vector embedding for an email.

    Args:
        data: Email metadata and 1536-dim embedding vector.
        db: Optional existing session.

    Returns:
        The persisted EmailEmbeddingRead.
    """
    logger.info("store_email_embedding: Storing embedding for email_id=%s.", data.email_id)
    close_db = db is None
    if db is None:
        db = SessionLocal()

    try:
        entry = EmailEmbedding(
            email_id=data.email_id,
            thread_id=data.thread_id,
            sender=data.sender,
            subject=data.subject,
            body_preview=data.body_preview,
            embedding=data.embedding,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info("store_email_embedding: Stored id=%d.", entry.id)
        return EmailEmbeddingRead.model_validate(entry)
    except Exception:
        db.rollback()
        logger.exception("store_email_embedding: Failed for email_id=%s.", data.email_id)
        raise
    finally:
        if close_db:
            db.close()


def semantic_search(
    query_embedding: list[float],
    limit: int = 5,
    db: Optional[Session] = None,
) -> list[SemanticSearchResult]:
    """Find the most semantically similar past emails.

    Uses pgvector's cosine distance operator (<=>) for similarity ranking.

    Args:
        query_embedding: 1536-dim embedding vector for the search query.
        limit: Maximum number of results to return.
        db: Optional existing session.

    Returns:
        List of SemanticSearchResult ordered by descending similarity.
    """
    logger.info("semantic_search: Searching with limit=%d.", limit)
    close_db = db is None
    if db is None:
        db = SessionLocal()

    try:
        stmt = text("""
            SELECT
                email_id,
                sender,
                subject,
                body_preview,
                1 - (embedding <=> :query_vec) AS similarity
            FROM email_embeddings
            ORDER BY embedding <=> :query_vec
            LIMIT :lim
        """)
        rows = db.execute(
            stmt,
            {"query_vec": str(query_embedding), "lim": limit},
        ).fetchall()

        results = [
            SemanticSearchResult(
                email_id=row.email_id,
                sender=row.sender,
                subject=row.subject,
                body_preview=row.body_preview,
                similarity=float(row.similarity),
            )
            for row in rows
        ]
        logger.info("semantic_search: Returning %d results.", len(results))
        return results
    finally:
        if close_db:
            db.close()
