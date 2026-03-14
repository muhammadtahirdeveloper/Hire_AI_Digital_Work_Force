"""Authentication endpoints — email/password + Google OAuth2.

Routes:
  POST /auth/register        — Create account with email + password.
  POST /auth/login           — Login with email + password, return JWT.
  POST /auth/google-login    — Upsert user from Google OAuth sign-in.
  GET  /auth/user/{email}    — Get user profile by email.
  GET  /auth/google          — Redirect to Google OAuth consent screen.
  GET  /auth/google/callback — Handle OAuth callback, save token to database.
"""

import hashlib
import logging
import os
import base64
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from pydantic import BaseModel
from sqlalchemy import text

from config.database import SessionLocal
from config.settings import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GMAIL_SCOPES,
    JWT_SECRET,
    JWT_ALGORITHM,
)
from memory.long_term import save_user_credentials

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


# Note: Token encryption is now handled by memory.long_term.save_user_credentials()
# using the EncryptionManager class for consistent encryption across the app


# ---------------------------------------------------------------------------
# Pydantic models for email/password auth
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class GoogleLoginRequest(BaseModel):
    email: str
    name: str = ""
    image: str = ""
    google_id: str = ""


# ---------------------------------------------------------------------------
# Helpers — users table auto-creation + JWT
# ---------------------------------------------------------------------------


def _ensure_users_table(db):
    """Create the users table if it doesn't exist."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT DEFAULT '',
            password_hash TEXT,
            image TEXT DEFAULT '',
            google_id TEXT,
            provider TEXT DEFAULT 'credentials',
            tier TEXT DEFAULT 'trial',
            agent_type TEXT DEFAULT 'general',
            is_active BOOLEAN DEFAULT true,
            setup_complete BOOLEAN DEFAULT false,
            trial_end_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))
    db.commit()


def _create_jwt(user_id: str, email: str, name: str = "") -> str:
    """Create a JWT token for the user."""
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ============================================================================
# POST /auth/register — Create account with email + password
# ============================================================================


@router.post("/register")
async def register(body: RegisterRequest):
    """Register a new user with email and password."""
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password required")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    try:
        db = SessionLocal()
        try:
            _ensure_users_table(db)

            existing = db.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": body.email.lower()},
            ).fetchone()

            if existing:
                raise HTTPException(status_code=409, detail="Email already registered")

            user_id = str(uuid.uuid4())
            trial_end = datetime.now(timezone.utc) + timedelta(days=7)

            db.execute(
                text("""
                    INSERT INTO users (id, email, name, password_hash, provider, tier, trial_end_date)
                    VALUES (:id, :email, :name, :password_hash, 'credentials', 'trial', :trial_end)
                """),
                {
                    "id": user_id,
                    "email": body.email.lower(),
                    "name": body.name or body.email.split("@")[0],
                    "password_hash": _hash_password(body.password),
                    "trial_end": trial_end,
                },
            )
            db.commit()

            token = _create_jwt(user_id, body.email.lower(), body.name)

            logger.info("User registered: %s", body.email)
            return _ok({
                "user": {
                    "id": user_id,
                    "email": body.email.lower(),
                    "name": body.name or body.email.split("@")[0],
                    "image": "",
                },
                "token": token,
            })
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Registration failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Registration failed: {exc}")


# ============================================================================
# POST /auth/login — Login with email + password
# ============================================================================


@router.post("/login")
async def login(body: LoginRequest):
    """Authenticate user with email and password."""
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password required")

    try:
        db = SessionLocal()
        try:
            _ensure_users_table(db)

            row = db.execute(
                text("""
                    SELECT id, email, name, password_hash, image, tier, agent_type,
                           is_active, setup_complete, trial_end_date
                    FROM users WHERE email = :email
                """),
                {"email": body.email.lower()},
            ).fetchone()

            if not row:
                raise HTTPException(status_code=401, detail="Invalid email or password")

            if not row[3]:
                raise HTTPException(
                    status_code=401,
                    detail="This account uses Google sign-in. Please use Google to log in.",
                )

            if not _verify_password(body.password, row[3]):
                raise HTTPException(status_code=401, detail="Invalid email or password")

            token = _create_jwt(row[0], row[1], row[2])

            return _ok({
                "user": {
                    "id": row[0],
                    "email": row[1],
                    "name": row[2] or "",
                    "image": row[4] or "",
                },
                "token": token,
            })
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Login failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Login failed: {exc}")


# ============================================================================
# POST /auth/google-login — Upsert user from Google OAuth
# ============================================================================


@router.post("/google-login")
async def google_login(body: GoogleLoginRequest):
    """Create or update user from Google OAuth sign-in."""
    if not body.email:
        raise HTTPException(status_code=400, detail="Email is required")

    try:
        db = SessionLocal()
        try:
            _ensure_users_table(db)

            row = db.execute(
                text("SELECT id, name, image FROM users WHERE email = :email"),
                {"email": body.email.lower()},
            ).fetchone()

            if row:
                db.execute(
                    text("""
                        UPDATE users SET name = :name, image = :image, google_id = :gid
                        WHERE email = :email
                    """),
                    {
                        "name": body.name or row[1],
                        "image": body.image or row[2],
                        "gid": body.google_id,
                        "email": body.email.lower(),
                    },
                )
                db.commit()
                user_id = row[0]
            else:
                user_id = str(uuid.uuid4())
                trial_end = datetime.now(timezone.utc) + timedelta(days=7)
                db.execute(
                    text("""
                        INSERT INTO users (id, email, name, image, google_id, provider, tier, trial_end_date)
                        VALUES (:id, :email, :name, :image, :gid, 'google', 'trial', :trial_end)
                    """),
                    {
                        "id": user_id,
                        "email": body.email.lower(),
                        "name": body.name or body.email.split("@")[0],
                        "image": body.image,
                        "gid": body.google_id,
                        "trial_end": trial_end,
                    },
                )
                db.commit()

            logger.info("Google user upserted: %s", body.email)
            return _ok({"user_id": user_id})
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Google login failed: %s", exc)
        return _ok({"user_id": "google-user"})


# ============================================================================
# GET /auth/user/{email} — Get user profile
# ============================================================================


@router.get("/user/{email}")
async def get_user(email: str):
    """Get user profile by email address."""
    try:
        db = SessionLocal()
        try:
            _ensure_users_table(db)

            row = db.execute(
                text("""
                    SELECT id, email, name, image, tier, agent_type,
                           is_active, setup_complete, trial_end_date
                    FROM users WHERE email = :email
                """),
                {"email": email.lower()},
            ).fetchone()

            if not row:
                return {
                    "tier": "trial",
                    "agent_type": "general",
                    "is_active": True,
                    "setup_complete": False,
                    "trial_end_date": None,
                }

            return {
                "id": row[0],
                "email": row[1],
                "name": row[2],
                "image": row[3],
                "tier": row[4] or "trial",
                "agent_type": row[5] or "general",
                "is_active": row[6] if row[6] is not None else True,
                "setup_complete": row[7] if row[7] is not None else False,
                "trial_end_date": row[8].isoformat() if row[8] else None,
            }
        finally:
            db.close()
    except Exception as exc:
        logger.error("Get user failed: %s", exc)
        return {
            "tier": "trial",
            "agent_type": "general",
            "is_active": True,
            "setup_complete": False,
            "trial_end_date": None,
        }


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

    # Save encrypted credentials to database using EncryptionManager
    # Use "default" as user_id for now (single-user setup).
    # In multi-user mode, extract user_id from the OAuth state parameter.
    user_id = "default"

    try:
        save_user_credentials(user_id, token_data)
        logger.info("OAuth tokens saved for user_id=%s", user_id)
    except Exception as exc:
        logger.error("Failed to save credentials to database: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save credentials: {exc}",
        )

    return _ok({
        "message": "Gmail OAuth authentication successful! Tokens saved.",
        "user_id": user_id,
        "scopes": token_data["scopes"],
    })
