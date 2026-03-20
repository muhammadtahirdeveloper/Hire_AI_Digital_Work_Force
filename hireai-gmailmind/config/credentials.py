"""Google OAuth2 credential management for Gmail API access."""

import logging
from datetime import datetime, timezone
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from config.settings import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GMAIL_SCOPES,
)

logger = logging.getLogger(__name__)


def get_oauth2_flow() -> InstalledAppFlow:
    """Create and return a Google OAuth2 flow for user authorization.

    Returns:
        InstalledAppFlow configured with client credentials and Gmail scopes.
    """
    client_config = {
        "installed": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [GOOGLE_REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, scopes=GMAIL_SCOPES)
    logger.info("OAuth2 flow created for Gmail scopes: %s", GMAIL_SCOPES)
    return flow


def build_credentials(
    token: str,
    refresh_token: str,
    token_uri: str = "https://oauth2.googleapis.com/token",
    expiry: Optional[datetime] = None,
) -> Credentials:
    """Build Google OAuth2 Credentials from stored token data.

    Args:
        token: The OAuth2 access token.
        refresh_token: The OAuth2 refresh token for token renewal.
        token_uri: The token endpoint URI.
        expiry: Token expiration datetime (timezone-aware or naive UTC).

    Returns:
        A google.oauth2.credentials.Credentials instance.
    """
    creds = Credentials(
        token=token,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=GMAIL_SCOPES,
    )

    # Set expiry so credentials.expired can detect stale tokens.
    # Google's auth library compares expiry with datetime.utcnow() which
    # returns a NAIVE datetime.  We must store expiry as naive UTC,
    # otherwise Python raises:
    #   "can't compare offset-naive and offset-aware datetimes"
    if expiry is not None:
        if expiry.tzinfo is not None:
            # Convert to UTC first, then strip tzinfo → naive UTC
            expiry = expiry.astimezone(timezone.utc).replace(tzinfo=None)
        creds.expiry = expiry
        creds.token = token  # ensure token is set even with expiry

    logger.info(
        "Built OAuth2 credentials (token present: %s, expiry: %s)",
        bool(token), expiry,
    )
    return creds


def refresh_credentials(
    credentials: Credentials,
    user_id: Optional[str] = None,
) -> Credentials:
    """Refresh expired OAuth2 credentials.

    Args:
        credentials: The expired Credentials object with a valid refresh_token.
        user_id: Optional user ID for updating gmail_connected on failure.

    Returns:
        The refreshed Credentials object.

    Raises:
        google.auth.exceptions.RefreshError: If the refresh token is invalid
            and cannot be recovered.
    """
    if credentials.expired and credentials.refresh_token:
        logger.info("Access token expired, refreshing...")
        try:
            credentials.refresh(Request())
            logger.info("Access token refreshed successfully.")
        except Exception as exc:
            logger.error("Token refresh failed for user=%s: %s", user_id, exc)
            # Mark gmail as disconnected in DB
            if user_id:
                _mark_gmail_disconnected(user_id, str(exc))
            raise
    return credentials


def _mark_gmail_disconnected(user_id: str, error_msg: str) -> None:
    """Mark user's Gmail as disconnected when token refresh fails."""
    try:
        from config.database import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()
        try:
            db.execute(
                text("""
                    UPDATE user_agents
                    SET gmail_valid = false,
                        last_error = :err,
                        updated_at = NOW()
                    WHERE user_id = :uid
                """),
                {"uid": user_id, "err": f"Gmail token refresh failed: {error_msg}"},
            )
            db.commit()
            logger.warning("Marked Gmail as disconnected for user=%s", user_id)
        finally:
            db.close()
    except Exception as db_exc:
        logger.error("Could not mark Gmail disconnected for user=%s: %s", user_id, db_exc)
