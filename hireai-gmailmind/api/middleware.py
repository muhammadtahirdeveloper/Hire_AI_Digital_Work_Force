"""Authentication and authorisation middleware for the GmailMind API.

Provides:
  - ``get_current_user`` — FastAPI dependency that extracts and validates
    a JWT bearer token from the ``Authorization`` header.
  - ``require_active_subscription`` — Dependency that checks whether the
    authenticated user has an active subscription before allowing
    agent-related operations.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from config.database import SessionLocal
from config.settings import JWT_ALGORITHM, JWT_SECRET

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer()


# ============================================================================
# JWT token verification
# ============================================================================


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict[str, Any]:
    """Decode and validate the JWT bearer token.

    The token payload is expected to contain at least:
      - ``sub``  — user ID
      - ``exp``  — expiration timestamp

    Returns:
        The decoded token payload as a dict.

    Raises:
        HTTPException 401: If the token is missing, expired, or invalid.
    """
    token = credentials.credentials

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim (user ID).",
        )

    logger.debug("Authenticated user: %s", user_id)
    return payload


# ============================================================================
# Subscription check
# ============================================================================


def require_active_subscription(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Verify that the authenticated user has an active subscription.

    Checks the ``user_subscriptions`` table in the database.  If the table
    doesn't exist or has no row for the user, the check is skipped in
    development mode to ease local testing.

    Returns:
        The user payload (pass-through) if the subscription is valid.

    Raises:
        HTTPException 403: If the subscription is expired or inactive.
    """
    user_id = user.get("sub", "")

    try:
        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT status, expires_at
                    FROM user_subscriptions
                    WHERE user_id = :uid
                    LIMIT 1
                """),
                {"uid": user_id},
            ).fetchone()
        finally:
            db.close()

        if row is None:
            # No subscription record — allow in dev, block in prod.
            from config.settings import APP_ENV

            if APP_ENV == "production":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No active subscription found. Please subscribe first.",
                )
            logger.debug("No subscription record for %s — allowed (dev mode).", user_id)
            return user

        sub_status = row[0]
        expires_at = row[1]

        if sub_status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Subscription is '{sub_status}'. An active subscription is required.",
            )

        if expires_at and expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subscription has expired. Please renew.",
            )

    except HTTPException:
        raise
    except Exception as exc:
        # Table may not exist yet — allow in development.
        from config.settings import APP_ENV

        if APP_ENV == "production":
            logger.error("Subscription check failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Subscription verification failed.",
            )
        logger.debug("Subscription check skipped (table may not exist): %s", exc)

    return user
