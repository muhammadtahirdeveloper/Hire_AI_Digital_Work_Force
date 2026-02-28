"""Report endpoints.

Routes:
  GET /reports/{user_id}/daily    — Today's summary report.
  GET /reports/{user_id}/actions  — Paginated action log.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text

from api.middleware import get_current_user
from config.database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Helpers
# ============================================================================


def _ok(data: Any = None) -> dict:
    return {"success": True, "data": data, "error": None}


def _err(message: str) -> dict:
    return {"success": False, "data": None, "error": message}


def _verify_user_access(user: dict, user_id: str) -> None:
    if user.get("sub", "") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own reports.",
        )


# ============================================================================
# GET /reports/{user_id}/daily
# ============================================================================


@router.get("/{user_id}/daily")
async def get_daily_report(
    user_id: str,
    date: str = Query(
        default="",
        description="Date in YYYY-MM-DD format. Defaults to today (UTC).",
    ),
    user: dict = Depends(get_current_user),
):
    """Get the daily summary report for a user.

    Returns aggregate counts and breakdown of all agent actions taken
    on the given date.
    """
    _verify_user_access(user, user_id)

    # Determine target date
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return _err("Invalid date format. Use YYYY-MM-DD.")
    else:
        target_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )

    next_date = target_date.replace(hour=23, minute=59, second=59)

    try:
        db = SessionLocal()
        try:
            # Total actions
            total_row = db.execute(
                text("""
                    SELECT COUNT(*) FROM action_logs
                    WHERE timestamp >= :start AND timestamp <= :end
                """),
                {"start": target_date, "end": next_date},
            ).fetchone()
            total_actions = total_row[0] if total_row else 0

            # Unique senders
            senders_row = db.execute(
                text("""
                    SELECT COUNT(DISTINCT email_from) FROM action_logs
                    WHERE timestamp >= :start AND timestamp <= :end
                """),
                {"start": target_date, "end": next_date},
            ).fetchone()
            unique_senders = senders_row[0] if senders_row else 0

            # Tools breakdown
            tools_rows = db.execute(
                text("""
                    SELECT tool_used, COUNT(*) as cnt FROM action_logs
                    WHERE timestamp >= :start AND timestamp <= :end
                    GROUP BY tool_used
                    ORDER BY cnt DESC
                """),
                {"start": target_date, "end": next_date},
            ).fetchall()
            tools_breakdown = {row[0]: row[1] for row in tools_rows}

            # Actions breakdown
            actions_rows = db.execute(
                text("""
                    SELECT action_taken, COUNT(*) as cnt FROM action_logs
                    WHERE timestamp >= :start AND timestamp <= :end
                    GROUP BY action_taken
                    ORDER BY cnt DESC
                """),
                {"start": target_date, "end": next_date},
            ).fetchall()
            actions_breakdown = {row[0]: row[1] for row in actions_rows}

            # Pending follow-ups
            followups_row = db.execute(
                text("""
                    SELECT COUNT(*) FROM follow_ups
                    WHERE status = 'pending'
                """),
            ).fetchone()
            pending_followups = followups_row[0] if followups_row else 0

            # Escalations today (from action_logs)
            esc_row = db.execute(
                text("""
                    SELECT COUNT(*) FROM action_logs
                    WHERE timestamp >= :start AND timestamp <= :end
                      AND (action_taken ILIKE '%%escalat%%'
                           OR tool_used = 'send_escalation_alert')
                """),
                {"start": target_date, "end": next_date},
            ).fetchone()
            escalations = esc_row[0] if esc_row else 0

        finally:
            db.close()

        report = {
            "date": target_date.strftime("%Y-%m-%d"),
            "total_actions": total_actions,
            "unique_senders": unique_senders,
            "escalations": escalations,
            "pending_followups": pending_followups,
            "tools_breakdown": tools_breakdown,
            "actions_breakdown": actions_breakdown,
        }

        return _ok(report)

    except Exception as exc:
        logger.exception("Failed to get daily report for user %s", user_id)
        return _err(f"Failed to generate report: {exc}")


# ============================================================================
# GET /reports/{user_id}/actions
# ============================================================================


@router.get("/{user_id}/actions")
async def get_action_log(
    user_id: str,
    page: int = Query(default=1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(default=50, ge=1, le=200, description="Items per page."),
    tool: str = Query(default="", description="Filter by tool name."),
    sender: str = Query(default="", description="Filter by sender email."),
    user: dict = Depends(get_current_user),
):
    """Get a paginated list of agent action log entries.

    Supports optional filtering by tool name or sender email.
    """
    _verify_user_access(user, user_id)

    offset = (page - 1) * page_size

    try:
        db = SessionLocal()
        try:
            # Build dynamic WHERE clause
            conditions = []
            params: dict[str, Any] = {"lim": page_size, "off": offset}

            if tool:
                conditions.append("tool_used = :tool")
                params["tool"] = tool
            if sender:
                conditions.append("email_from = :sender")
                params["sender"] = sender

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            # Get total count
            count_row = db.execute(
                text(f"SELECT COUNT(*) FROM action_logs {where_clause}"),
                params,
            ).fetchone()
            total = count_row[0] if count_row else 0

            # Get page of results
            rows = db.execute(
                text(f"""
                    SELECT id, timestamp, email_from, action_taken,
                           tool_used, outcome, metadata
                    FROM action_logs
                    {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT :lim OFFSET :off
                """),
                params,
            ).fetchall()

        finally:
            db.close()

        actions = [
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

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return _ok({
            "actions": actions,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
        })

    except Exception as exc:
        logger.exception("Failed to get action log for user %s", user_id)
        return _err(f"Failed to get actions: {exc}")
