"""Security audit logging for GmailMind.

Tracks security-related events for compliance and monitoring.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import text

from config.database import engine

logger = logging.getLogger(__name__)


class AuditLogger:
    """Log security events to database and Python logger."""

    # Valid event types
    EVENT_TYPES = {
        'api_key_created',
        'api_key_used',
        'api_key_invalid',
        'rate_limit_exceeded',
        'unauthorized_access',
        'login_success',
        'login_failed',
        'password_reset',
        'permission_denied',
        'suspicious_activity',
        'data_export',
        'data_deletion',
        'config_changed',
    }

    @staticmethod
    def log_security_event(
        event_type: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[dict] = None,
        success: bool = True
    ) -> None:
        """Log a security event to database and Python logger.

        Args:
            event_type: Type of security event (see EVENT_TYPES)
            user_id: User identifier (if applicable)
            ip_address: Client IP address
            details: Additional event details (stored as JSON)
            success: Whether the event succeeded or failed
        """
        # Validate event type
        if event_type not in AuditLogger.EVENT_TYPES:
            logger.warning(
                "[AuditLogger] Unknown event type: %s. Logging anyway.",
                event_type
            )

        # Prepare details
        if details is None:
            details = {}

        # Log to Python logger (WARNING level for security events)
        log_level = logging.WARNING if not success else logging.INFO
        logger.log(
            log_level,
            "[AuditLogger] Security Event: %s | user=%s | ip=%s | success=%s | details=%s",
            event_type,
            user_id or "anonymous",
            ip_address or "unknown",
            success,
            json.dumps(details) if details else "{}"
        )

        # Log to database
        try:
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO security_audit_logs
                            (event_type, user_id, ip_address, details, success, created_at)
                        VALUES
                            (:event_type, :user_id, :ip_address, :details, :success, NOW())
                    """),
                    {
                        "event_type": event_type,
                        "user_id": user_id,
                        "ip_address": ip_address,
                        "details": json.dumps(details),
                        "success": success
                    }
                )
                conn.commit()
        except Exception as exc:
            # Don't fail the application if audit logging fails
            logger.error(
                "[AuditLogger] Failed to write to database: %s",
                exc,
                exc_info=True
            )

    @staticmethod
    def get_recent_events(
        limit: int = 100,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> list[dict]:
        """Retrieve recent security events.

        Args:
            limit: Maximum number of events to return
            event_type: Filter by event type (optional)
            user_id: Filter by user ID (optional)

        Returns:
            list: Recent security events
        """
        try:
            with engine.connect() as conn:
                # Build query with optional filters
                query = """
                    SELECT id, event_type, user_id, ip_address, details, success, created_at
                    FROM security_audit_logs
                    WHERE 1=1
                """
                params = {"limit": limit}

                if event_type:
                    query += " AND event_type = :event_type"
                    params["event_type"] = event_type

                if user_id:
                    query += " AND user_id = :user_id"
                    params["user_id"] = user_id

                query += " ORDER BY created_at DESC LIMIT :limit"

                results = conn.execute(text(query), params).fetchall()

                events = []
                for row in results:
                    events.append({
                        "id": row[0],
                        "event_type": row[1],
                        "user_id": row[2],
                        "ip_address": row[3],
                        "details": json.loads(row[4]) if row[4] else {},
                        "success": row[5],
                        "created_at": row[6].isoformat() if row[6] else None
                    })

                return events

        except Exception as exc:
            logger.error("[AuditLogger] Failed to retrieve events: %s", exc)
            return []

    @staticmethod
    def get_failed_login_attempts(
        user_id: str,
        hours: int = 24
    ) -> int:
        """Count failed login attempts for a user in the last N hours.

        Useful for detecting brute force attacks.

        Args:
            user_id: User identifier
            hours: Time window in hours

        Returns:
            int: Number of failed login attempts
        """
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM security_audit_logs
                        WHERE user_id = :user_id
                          AND event_type = 'login_failed'
                          AND success = FALSE
                          AND created_at > NOW() - INTERVAL ':hours hours'
                    """),
                    {"user_id": user_id, "hours": hours}
                ).scalar()

                return result or 0

        except Exception as exc:
            logger.error(
                "[AuditLogger] Failed to count login attempts: %s",
                exc
            )
            return 0

    @staticmethod
    def get_security_summary(days: int = 7) -> dict:
        """Get summary of security events over the last N days.

        Args:
            days: Number of days to include

        Returns:
            dict: Summary statistics
        """
        try:
            with engine.connect() as conn:
                # Count events by type
                results = conn.execute(
                    text("""
                        SELECT event_type, success, COUNT(*) as count
                        FROM security_audit_logs
                        WHERE created_at > NOW() - INTERVAL ':days days'
                        GROUP BY event_type, success
                        ORDER BY count DESC
                    """),
                    {"days": days}
                ).fetchall()

                summary = {
                    "period_days": days,
                    "total_events": 0,
                    "failed_events": 0,
                    "events_by_type": {}
                }

                for row in results:
                    event_type, success, count = row
                    summary["total_events"] += count

                    if not success:
                        summary["failed_events"] += count

                    if event_type not in summary["events_by_type"]:
                        summary["events_by_type"][event_type] = {
                            "success": 0,
                            "failed": 0
                        }

                    if success:
                        summary["events_by_type"][event_type]["success"] = count
                    else:
                        summary["events_by_type"][event_type]["failed"] = count

                return summary

        except Exception as exc:
            logger.error("[AuditLogger] Failed to get security summary: %s", exc)
            return {"error": str(exc)}
