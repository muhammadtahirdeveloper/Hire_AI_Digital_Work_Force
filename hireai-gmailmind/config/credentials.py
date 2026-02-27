"""Google OAuth2 credential management for Gmail API access."""

import logging
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
) -> Credentials:
    """Build Google OAuth2 Credentials from stored token data.

    Args:
        token: The OAuth2 access token.
        refresh_token: The OAuth2 refresh token for token renewal.
        token_uri: The token endpoint URI.

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
    logger.info("Built OAuth2 credentials (token present: %s)", bool(token))
    return creds


def refresh_credentials(credentials: Credentials) -> Credentials:
    """Refresh expired OAuth2 credentials.

    Args:
        credentials: The expired Credentials object with a valid refresh_token.

    Returns:
        The refreshed Credentials object.

    Raises:
        google.auth.exceptions.RefreshError: If the refresh token is invalid.
    """
    if credentials.expired and credentials.refresh_token:
        logger.info("Access token expired, refreshing...")
        credentials.refresh(Request())
        logger.info("Access token refreshed successfully.")
    return credentials
