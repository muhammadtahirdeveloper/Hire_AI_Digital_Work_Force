"""Health monitoring for the GmailMind platform.

Tracks user activity, detects inactive users, and provides
a health snapshot for the /platform/health API endpoint.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from config.database import SessionLocal

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors platform health and user activity."""

    def check_all_users(self) -> dict[str, str]:
        """Check last activity timestamp for all active users.

        Returns:
            Dict mapping user_id to last_active ISO timestamp string.
        """
        db = SessionLocal()
        try:
            rows = db.execute(
                text("""
                    SELECT us.user_id,
                           COALESCE(
                               (SELECT MAX(al.timestamp)
                                FROM action_logs al
                                WHERE al.user_id = us.user_id),
                               us.created_at
                           ) AS last_active
                    FROM user_subscriptions us
                    WHERE us.status = 'active'
                """),
            ).fetchall()

            result = {}
            for row in rows:
                user_id = row[0]
                last_active = row[1]
                result[user_id] = (
                    last_active.isoformat() if last_active else None
                )

            logger.info("HealthMonitor: Checked %d active users.", len(result))
            return result

        except Exception as exc:
            logger.error("HealthMonitor: Error checking users: %s", exc)
            return {}
        finally:
            db.close()

    def get_inactive_users(self, hours: int = 2) -> list[dict[str, Any]]:
        """Get users with no activity in the last N hours.

        Args:
            hours: Inactivity threshold in hours.

        Returns:
            List of dicts with user_id and last_active timestamp.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        db = SessionLocal()
        try:
            rows = db.execute(
                text("""
                    SELECT us.user_id,
                           (SELECT MAX(al.timestamp)
                            FROM action_logs al
                            WHERE al.user_id = us.user_id) AS last_active
                    FROM user_subscriptions us
                    WHERE us.status = 'active'
                """),
            ).fetchall()

            inactive = []
            for row in rows:
                user_id = row[0]
                last_active = row[1]

                if last_active is None or last_active < cutoff:
                    inactive.append({
                        "user_id": user_id,
                        "last_active": (
                            last_active.isoformat() if last_active else None
                        ),
                    })

            logger.info(
                "HealthMonitor: Found %d inactive users (>%dh).",
                len(inactive), hours,
            )
            return inactive

        except Exception as exc:
            logger.error("HealthMonitor: Error getting inactive users: %s", exc)
            return []
        finally:
            db.close()
