"""Agent management endpoints.

Routes:
  POST /agents/{user_id}/start  — Start the agent for a user.
  POST /agents/{user_id}/stop   — Stop the agent for a user.
  GET  /agents/{user_id}/status — Get current agent status.
  GET  /agents/{user_id}/logs   — Get last 100 agent actions.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from api.middleware import get_current_user, require_active_subscription
from config.database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Helpers
# ============================================================================


def _ok(data: Any = None) -> dict:
    """Consistent success response."""
    return {"success": True, "data": data, "error": None}


def _err(message: str, status_code: int = 400) -> dict:
    """Consistent error response (returned, NOT raised)."""
    return {"success": False, "data": None, "error": message}


def _verify_user_access(user: dict, user_id: str) -> None:
    """Ensure the authenticated user matches the requested user_id."""
    token_uid = user.get("sub", "")
    if token_uid != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own agent.",
        )


# ============================================================================
# POST /agents/{user_id}/start
# ============================================================================


@router.post("/{user_id}/start")
async def start_agent(
    user_id: str,
    user: dict = Depends(require_active_subscription),
):
    """Start the GmailMind agent for a user.

    Dispatches a Celery task to begin the agent loop. Requires an active
    subscription.
    """
    _verify_user_access(user, user_id)

    try:
        from scheduler.tasks import run_gmailmind_for_user

        # Check if already running
        db = SessionLocal()
        try:
            row = db.execute(
                text("SELECT status FROM agent_status WHERE user_id = :uid"),
                {"uid": user_id},
            ).fetchone()

            if row and row[0] == "running":
                return _ok({"message": "Agent is already running.", "status": "running"})
        except Exception:
            pass  # Table may not exist yet — proceed anyway.
        finally:
            db.close()

        # Dispatch Celery task
        task = run_gmailmind_for_user.delay(user_id)
        logger.info("Agent started for user %s — task_id=%s", user_id, task.id)

        return _ok({
            "message": "Agent started successfully.",
            "task_id": task.id,
            "status": "running",
        })

    except Exception as exc:
        logger.exception("Failed to start agent for user %s", user_id)
        return _err(f"Failed to start agent: {exc}")


# ============================================================================
# POST /agents/{user_id}/stop
# ============================================================================


@router.post("/{user_id}/stop")
async def stop_agent(
    user_id: str,
    user: dict = Depends(get_current_user),
):
    """Stop the GmailMind agent for a user.

    Sets the agent status to 'idle' and revokes any running Celery tasks.
    """
    _verify_user_access(user, user_id)

    try:
        from scheduler.celery_app import app as celery_app

        # Revoke active tasks for this user
        inspector = celery_app.control.inspect()
        active = inspector.active() or {}

        revoked = 0
        for worker_tasks in active.values():
            for task_info in worker_tasks:
                task_args = task_info.get("args", [])
                if task_args and task_args[0] == user_id:
                    celery_app.control.revoke(task_info["id"], terminate=True)
                    revoked += 1

        # Update status to idle
        db = SessionLocal()
        try:
            db.execute(
                text("""
                    UPDATE agent_status
                    SET status = 'idle', error_msg = '', updated_at = NOW()
                    WHERE user_id = :uid
                """),
                {"uid": user_id},
            )
            db.commit()
        except Exception:
            pass  # Table may not exist.
        finally:
            db.close()

        logger.info("Agent stopped for user %s — %d tasks revoked.", user_id, revoked)

        return _ok({
            "message": "Agent stopped.",
            "tasks_revoked": revoked,
            "status": "idle",
        })

    except Exception as exc:
        logger.exception("Failed to stop agent for user %s", user_id)
        return _err(f"Failed to stop agent: {exc}")


# ============================================================================
# GET /agents/{user_id}/status
# ============================================================================


@router.get("/{user_id}/status")
async def get_agent_status(
    user_id: str,
    user: dict = Depends(get_current_user),
):
    """Get the current agent status for a user.

    Returns running/idle/error along with last_run timestamp.
    """
    _verify_user_access(user, user_id)

    try:
        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT status, last_run, error_msg, updated_at
                    FROM agent_status
                    WHERE user_id = :uid
                """),
                {"uid": user_id},
            ).fetchone()
        finally:
            db.close()

        if row is None:
            return _ok({
                "status": "idle",
                "last_run": None,
                "error_msg": None,
                "updated_at": None,
            })

        return _ok({
            "status": row[0],
            "last_run": row[1].isoformat() if row[1] else None,
            "error_msg": row[2] or None,
            "updated_at": row[3].isoformat() if row[3] else None,
        })

    except Exception as exc:
        logger.exception("Failed to get agent status for user %s", user_id)
        return _err(f"Failed to get status: {exc}")


# ============================================================================
# GET /agents/{user_id}/logs
# ============================================================================


@router.get("/{user_id}/logs")
async def get_agent_logs(
    user_id: str,
    limit: int = 100,
    user: dict = Depends(get_current_user),
):
    """Get the last N agent action log entries.

    Args:
        limit: Maximum number of log entries to return (default 100, max 500).
    """
    _verify_user_access(user, user_id)
    limit = min(limit, 500)

    try:
        db = SessionLocal()
        try:
            rows = db.execute(
                text("""
                    SELECT id, timestamp, email_from, action_taken,
                           tool_used, outcome, metadata
                    FROM action_logs
                    ORDER BY timestamp DESC
                    LIMIT :lim
                """),
                {"lim": limit},
            ).fetchall()
        finally:
            db.close()

        logs = [
            {
                "id": row[0],
                "timestamp": row[1].isoformat() if row[1] else None,
                "email_from": row[2],
                "action_taken": row[3],
                "tool_used": row[4],
                "outcome": row[5],
                "metadata": row[6],
            }
            for row in rows
        ]

        return _ok({"logs": logs, "count": len(logs)})

    except Exception as exc:
        logger.exception("Failed to get logs for user %s", user_id)
        return _err(f"Failed to get logs: {exc}")
