"""Web Push Notification routes.

Handles:
  - Push subscription management (save/delete browser push subscriptions)
  - Sending push notifications for urgent events
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import text

from config.database import SessionLocal
from security.middleware import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


# ============================================================================
# Models
# ============================================================================


class PushSubscription(BaseModel):
    endpoint: str
    keys: dict  # {p256dh, auth}


# ============================================================================
# Routes
# ============================================================================


@router.post("/subscribe")
async def subscribe_push(sub: PushSubscription, request: Request):
    """Save a browser push subscription for the authenticated user."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return {"success": False, "error": "Not authenticated"}

    db = SessionLocal()
    try:
        # Ensure table exists
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                endpoint TEXT NOT NULL,
                keys_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, endpoint)
            )
        """))

        # Upsert subscription
        db.execute(
            text("""
                INSERT INTO push_subscriptions (user_id, endpoint, keys_json, created_at)
                VALUES (:uid, :endpoint, :keys, :now)
                ON CONFLICT (user_id, endpoint) DO UPDATE
                SET keys_json = :keys, created_at = :now
            """),
            {
                "uid": user_id,
                "endpoint": sub.endpoint,
                "keys": json.dumps(sub.keys),
                "now": datetime.now(timezone.utc),
            },
        )
        db.commit()

        logger.info("[push] Subscription saved for user %s", user_id)
        return {"success": True, "data": {"message": "Subscription saved"}, "error": None}

    except Exception as exc:
        db.rollback()
        logger.error("[push] Failed to save subscription: %s", exc)
        return {"success": False, "error": str(exc)}
    finally:
        db.close()


@router.delete("/subscribe")
async def unsubscribe_push(request: Request):
    """Remove push subscriptions for the authenticated user."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return {"success": False, "error": "Not authenticated"}

    db = SessionLocal()
    try:
        db.execute(
            text("DELETE FROM push_subscriptions WHERE user_id = :uid"),
            {"uid": user_id},
        )
        db.commit()
        return {"success": True, "data": {"message": "Unsubscribed"}, "error": None}
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}
    finally:
        db.close()


# ============================================================================
# Helper: send push to a user (called from agent/tasks)
# ============================================================================


def send_push_to_user(user_id: str, title: str, body: str, url: str = "/dashboard") -> int:
    """Send a web push notification to all subscribed devices for a user.

    Returns the number of notifications sent.
    """
    try:
        from pywebpush import webpush, WebPushException
        import os

        vapid_private = os.environ.get("VAPID_PRIVATE_KEY")
        vapid_email = os.environ.get("VAPID_EMAIL", "mailto:hireaidigitalemployee@gmail.com")

        if not vapid_private:
            logger.debug("[push] VAPID_PRIVATE_KEY not set, skipping push")
            return 0

        db = SessionLocal()
        try:
            rows = db.execute(
                text("SELECT endpoint, keys_json FROM push_subscriptions WHERE user_id = :uid"),
                {"uid": user_id},
            ).fetchall()
        finally:
            db.close()

        if not rows:
            return 0

        payload = json.dumps({"title": title, "body": body, "url": url})
        sent = 0

        for row in rows:
            endpoint = row[0]
            keys = json.loads(row[1])

            try:
                webpush(
                    subscription_info={"endpoint": endpoint, "keys": keys},
                    data=payload,
                    vapid_private_key=vapid_private,
                    vapid_claims={"sub": vapid_email},
                )
                sent += 1
            except WebPushException as exc:
                # 410 Gone means subscription expired — clean up
                if "410" in str(exc):
                    db2 = SessionLocal()
                    try:
                        db2.execute(
                            text("DELETE FROM push_subscriptions WHERE endpoint = :ep"),
                            {"ep": endpoint},
                        )
                        db2.commit()
                    finally:
                        db2.close()
                logger.warning("[push] WebPush error for %s: %s", user_id, exc)
            except Exception as exc:
                logger.warning("[push] Unexpected push error: %s", exc)

        return sent

    except ImportError:
        logger.debug("[push] pywebpush not installed, skipping push notifications")
        return 0
    except Exception as exc:
        logger.error("[push] send_push_to_user error: %s", exc)
        return 0
