"""Google OAuth2 authentication endpoints.

Routes:
  GET /auth/google          — Redirect to Google OAuth consent screen.
  GET /auth/google/callback — Handle OAuth callback, save token to database.
"""

import hashlib
import json
import logging
import os
import base64

from cryptography.fernet import Fernet
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from sqlalchemy import text

from config.database import SessionLocal
from config.settings import (
    ENCRYPTION_KEY,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GMAIL_SCOPES,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# OAuth2 client config (matches config/credentials.json structure)
# ---------------------------------------------------------------------------

_CLIENT_CONFIG = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uris": [GOOGLE_REDIRECT_URI],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(data=None) -> dict:
    return {"success": True, "data": data, "error": None}


def _err(message: str) -> dict:
    return {"success": False, "data": None, "error": message}


def _build_flow() -> Flow:
    """Create a Google OAuth2 web-server flow."""
    flow = Flow.from_client_config(
        _CLIENT_CONFIG,
        scopes=GMAIL_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )
    return flow


# In-memory store: state -> code_verifier (cleared after use)
_pkce_store: dict[str, str] = {}


def _generate_pkce() -> tuple[str, str]:
    """Generate a PKCE code_verifier and code_challenge (S256)."""
    code_verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b"=").decode()
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


def _encrypt_token(token_data: dict) -> str:
    """Encrypt token JSON with Fernet. Falls back to plain JSON if no key."""
    raw = json.dumps(token_data)
    if ENCRYPTION_KEY:
        fernet = Fernet(ENCRYPTION_KEY.encode())
        return fernet.encrypt(raw.encode()).decode()
    return raw


# ============================================================================
# GET /auth/google — Redirect to Google consent screen
# ============================================================================


@router.get("/google")
async def google_auth_redirect():
    """Redirect the user to the Google OAuth2 consent screen.

    The user will be asked to grant Gmail access permissions defined
    in GMAIL_SCOPES. After consent, Google redirects back to
    /auth/google/callback with an authorization code.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth credentials are not configured. "
                   "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env",
        )

    flow = _build_flow()
    code_verifier, code_challenge = _generate_pkce()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )

    # Store code_verifier keyed by state so the callback can retrieve it.
    _pkce_store[state] = code_verifier

    logger.info("Redirecting to Google OAuth consent screen (PKCE enabled).")
    return RedirectResponse(url=authorization_url)


# ============================================================================
# GET /auth/google/callback — Handle OAuth callback
# ============================================================================


@router.get("/google/callback")
async def google_auth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(None),
):
    """Handle the Google OAuth2 callback.

    Exchanges the authorization code for access + refresh tokens using
    the PKCE code_verifier, encrypts the token data, and saves it to
    the user_credentials table.
    """
    # Retrieve and consume the code_verifier for this state.
    code_verifier = _pkce_store.pop(state, None)
    if not code_verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please restart the flow at /auth/google",
        )

    flow = _build_flow()

    try:
        flow.fetch_token(code=code, code_verifier=code_verifier)
    except Exception as exc:
        logger.error("Failed to exchange authorization code: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange authorization code: {exc}",
        )

    credentials = flow.credentials

    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes or GMAIL_SCOPES),
        "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
    }

    # Encrypt and save to database
    encrypted_creds = _encrypt_token(token_data)

    # Use "default" as user_id for now (single-user setup).
    # In multi-user mode, extract user_id from the OAuth state parameter.
    user_id = "default"

    db = SessionLocal()
    try:
        # Upsert into user_credentials
        db.execute(
            text("""
                INSERT INTO user_credentials (user_id, encrypted_creds, updated_at)
                VALUES (:uid, :creds, NOW())
                ON CONFLICT (user_id)
                DO UPDATE SET encrypted_creds = :creds, updated_at = NOW()
            """),
            {"uid": user_id, "creds": encrypted_creds},
        )
        db.commit()
        logger.info("OAuth tokens saved for user_id=%s", user_id)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to save credentials to database: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save credentials: {exc}",
        )
    finally:
        db.close()

    return _ok({
        "message": "Gmail OAuth authentication successful! Tokens saved.",
        "user_id": user_id,
        "scopes": token_data["scopes"],
    })
