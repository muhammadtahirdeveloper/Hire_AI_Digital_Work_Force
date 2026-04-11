"""Gmail Push Notification Webhook.

Receives real-time notifications from Gmail via Google Pub/Sub
when new emails arrive, triggering immediate processing instead
of waiting for the 5-minute polling interval.

Flow:
  1. User's Gmail is subscribed to a Pub/Sub topic via ``users.watch()``.
  2. When a new email arrives, Google publishes to the topic.
  3. Google's Pub/Sub pushes to this webhook endpoint.
  4. We decode the notification, find the user, and trigger processing.
"""

import base64
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/gmail")
async def gmail_push_notification(request: Request):
    """Receive Gmail Pub/Sub push notification.

    Google sends a POST with a Pub/Sub message containing the
    user's email address and historyId. We use this to trigger
    immediate email processing for that user.

    Returns 200 OK to acknowledge — Google will retry on non-2xx.
    """
    try:
        body = await request.json()
    except Exception:
        logger.warning("Gmail webhook: invalid JSON body")
        return Response(status_code=200)  # Ack to prevent retries

    # Extract the Pub/Sub message
    message = body.get("message", {})
    if not message:
        logger.warning("Gmail webhook: no message in body")
        return Response(status_code=200)

    # Decode the base64 data
    data_b64 = message.get("data", "")
    try:
        data_bytes = base64.b64decode(data_b64)
        data = json.loads(data_bytes)
    except Exception as exc:
        logger.warning("Gmail webhook: failed to decode message data: %s", exc)
        return Response(status_code=200)

    email_address = data.get("emailAddress", "")
    history_id = data.get("historyId", "")

    if not email_address:
        logger.warning("Gmail webhook: no emailAddress in notification")
        return Response(status_code=200)

    logger.info(
        "Gmail webhook: notification for %s (historyId=%s)",
        email_address, history_id,
    )

    # Find user_id by gmail_email
    user_id = _find_user_by_gmail(email_address)
    if not user_id:
        logger.warning("Gmail webhook: no user found for %s", email_address)
        return Response(status_code=200)

    # Trigger immediate processing in background thread
    try:
        from jobs import run_gmailmind_for_user, run_in_background

        run_in_background(run_gmailmind_for_user, user_id)
        logger.info(
            "Gmail webhook: triggered processing for user=%s (%s)",
            user_id, email_address,
        )
    except Exception as exc:
        logger.error("Gmail webhook: failed to dispatch task: %s", exc)

    return Response(status_code=200)


def _find_user_by_gmail(email_address: str) -> str | None:
    """Look up user_id by their connected Gmail address."""
    try:
        from sqlalchemy import text
        from config.database import SessionLocal

        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT user_id FROM user_agents
                    WHERE gmail_email = :email
                      AND is_paused = false
                    LIMIT 1
                """),
                {"email": email_address.lower()},
            ).fetchone()
            return row[0] if row else None
        finally:
            db.close()
    except Exception as exc:
        logger.error("Gmail webhook: DB lookup failed: %s", exc)
        return None
