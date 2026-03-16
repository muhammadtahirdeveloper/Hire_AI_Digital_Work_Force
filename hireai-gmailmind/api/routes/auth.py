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
import json
import logging
import os
import base64
import uuid
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import bcrypt
import jwt
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
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

# In-memory store: state -> setup metadata (setup=true, email)
_setup_store: dict[str, dict] = {}


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


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class SendVerificationRequest(BaseModel):
    email: str


class CompleteSetupRequest(BaseModel):
    email: str


class SetupRequest(BaseModel):
    email: str
    gmail_address: str = ""
    agent_type: str = "general"
    ai_model: str = "gemini"
    ai_api_key: Optional[str] = None
    business_name: str = ""
    user_name: str = ""
    reply_tone: str = "friendly"
    working_hours_from: str = "09:00"
    working_hours_to: str = "17:00"
    whatsapp_number: Optional[str] = None
    custom_db_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers — users table auto-creation + JWT
# ---------------------------------------------------------------------------


SMTP_EMAIL = os.getenv("SMTP_EMAIL", "hireaidigitalemployee@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://hireai-frontend.vercel.app")


def _send_email(to_email: str, subject: str, html_body: str):
    """Send an email via Gmail SMTP. Fails silently if not configured."""
    if not SMTP_PASSWORD:
        logger.warning("SMTP_PASSWORD not set — skipping email send to %s", to_email)
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"HireAI <{SMTP_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        logger.info("Email sent to %s: %s", to_email, subject)
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)


def _build_verification_email(name: str, token: str) -> str:
    link = f"{FRONTEND_URL}/verify-email?token={token}"
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;padding:32px;border:1px solid #e5e7eb;border-radius:12px;">
      <h2 style="color:#1D4ED8;margin:0 0 8px;">HireAI</h2>
      <p>Hi {name},</p>
      <p>Thanks for signing up! Please verify your email address to get started.</p>
      <a href="{link}" style="display:inline-block;margin:24px 0;padding:12px 28px;background:#1D4ED8;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">Verify Email</a>
      <p style="font-size:13px;color:#6b7280;">This link expires in 24 hours.</p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
      <p style="font-size:12px;color:#9ca3af;">If you didn't create an account, you can ignore this email.</p>
    </div>"""


def _build_reset_email(name: str, token: str) -> str:
    link = f"{FRONTEND_URL}/reset-password?token={token}"
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;padding:32px;border:1px solid #e5e7eb;border-radius:12px;">
      <h2 style="color:#1D4ED8;margin:0 0 8px;">HireAI</h2>
      <p>Hi {name},</p>
      <p>We received a request to reset your password. Click the button below to set a new password.</p>
      <a href="{link}" style="display:inline-block;margin:24px 0;padding:12px 28px;background:#1D4ED8;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">Reset Password</a>
      <p style="font-size:13px;color:#6b7280;">This link expires in 1 hour.</p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
      <p style="font-size:12px;color:#9ca3af;">If you didn't request a password reset, you can ignore this email.</p>
    </div>"""


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
            created_at TIMESTAMP DEFAULT NOW(),
            email_verified BOOLEAN DEFAULT false,
            verification_token TEXT,
            verification_token_expires TIMESTAMP,
            reset_token TEXT,
            reset_token_expires TIMESTAMP
        )
    """))
    # Add columns for existing tables
    for col in [
        "email_verified BOOLEAN DEFAULT false",
        "verification_token TEXT",
        "verification_token_expires TIMESTAMP",
        "reset_token TEXT",
        "reset_token_expires TIMESTAMP",
    ]:
        try:
            db.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col}"))
        except Exception:
            pass
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
            verification_token = str(uuid.uuid4())
            verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)

            db.execute(
                text("""
                    INSERT INTO users (id, email, name, password_hash, provider, tier, trial_end_date,
                                       email_verified, verification_token, verification_token_expires)
                    VALUES (:id, :email, :name, :password_hash, 'credentials', 'trial', :trial_end,
                            false, :vtoken, :vexpires)
                """),
                {
                    "id": user_id,
                    "email": body.email.lower(),
                    "name": body.name or body.email.split("@")[0],
                    "password_hash": _hash_password(body.password),
                    "trial_end": trial_end,
                    "vtoken": verification_token,
                    "vexpires": verification_expires,
                },
            )
            db.commit()

            user_name = body.name or body.email.split("@")[0]
            html = _build_verification_email(user_name, verification_token)
            _send_email(body.email.lower(), "Verify your HireAI email address", html)

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
                           is_active, setup_complete, trial_end_date, email_verified
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

            email_verified = row[10] if len(row) > 10 and row[10] is not None else False
            if not email_verified:
                raise HTTPException(
                    status_code=403,
                    detail="Please verify your email first",
                )

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
                    "setup_complete": True,
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
            "setup_complete": True,
            "trial_end_date": None,
        }


# ============================================================================
# GET /auth/google — Redirect to Google consent screen
# ============================================================================


@router.get("/google")
async def google_auth_redirect(
    setup: str = Query("", description="Set to 'true' if called from setup wizard"),
    email: str = Query("", description="User email for setup context"),
):
    """Redirect the user to the Google OAuth2 consent screen.

    The user will be asked to grant Gmail access permissions defined
    in GMAIL_SCOPES. After consent, Google redirects back to
    /auth/google/callback with an authorization code.

    If setup=true, the callback will return an HTML page that posts
    a message to the parent window (for popup OAuth flow).
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

    # Store setup metadata if this is from the setup wizard
    if setup.lower() == "true":
        _setup_store[state] = {"setup": True, "email": email}

    logger.info("Redirecting to Google OAuth consent screen (PKCE enabled, setup=%s).", setup)
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

    # Validate that required Gmail scopes are present (subset check).
    # Google may return extra scopes (openid, userinfo.email, userinfo.profile)
    # which is fine — we only require our Gmail scopes.
    required_scopes = {
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
    }
    token_scopes = set(credentials.scopes or [])
    if token_scopes and not required_scopes.issubset(token_scopes):
        missing = required_scopes - token_scopes
        logger.warning("OAuth callback: missing required scopes: %s (got: %s)", missing, token_scopes)
        # Don't fail — user may have partially granted. Log and continue.

    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes or GMAIL_SCOPES),
        "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
    }

    # Check if this was a setup wizard OAuth flow
    setup_meta = _setup_store.pop(state, None)
    setup_email = (setup_meta or {}).get("email", "")
    is_setup = bool(setup_meta and setup_meta.get("setup"))

    # Determine user_id — use email if available, else "default"
    user_id = setup_email or "default"

    # If we have a setup email, try to find the actual user ID
    if setup_email:
        try:
            db = SessionLocal()
            try:
                row = db.execute(
                    text("SELECT id FROM users WHERE email = :email"),
                    {"email": setup_email.lower()},
                ).fetchone()
                if row:
                    user_id = str(row[0])
            finally:
                db.close()
        except Exception:
            pass

    try:
        save_user_credentials(user_id, token_data)
        logger.info("OAuth tokens saved for user_id=%s", user_id)
    except Exception as exc:
        logger.error("Failed to save credentials to database: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save credentials: {exc}",
        )

    # Update gmail_token_valid in user_agents
    if user_id != "default":
        try:
            db = SessionLocal()
            try:
                db.execute(
                    text("""
                        UPDATE user_agents
                        SET gmail_token_valid = true, updated_at = NOW()
                        WHERE user_id = :uid
                    """),
                    {"uid": user_id},
                )
                db.commit()
            finally:
                db.close()
        except Exception:
            pass

    # If setup wizard flow, return HTML that posts message to parent window
    if is_setup:
        return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head><title>Gmail Connected</title></head>
<body>
<p>Gmail connected successfully! This window will close automatically.</p>
<script>
  if (window.opener) {
    window.opener.postMessage({ type: "gmail-connected" }, "*");
  }
  setTimeout(function() { window.close(); }, 1500);
</script>
</body>
</html>
""")

    return _ok({
        "message": "Gmail OAuth authentication successful! Tokens saved.",
        "user_id": user_id,
        "scopes": token_data["scopes"],
    })


# ============================================================================
# POST /auth/send-verification-email — Resend verification email
# ============================================================================


@router.post("/send-verification-email")
async def send_verification_email(body: SendVerificationRequest):
    """Resend the email verification link."""
    if not body.email:
        raise HTTPException(status_code=400, detail="Email is required")
    try:
        db = SessionLocal()
        try:
            _ensure_users_table(db)
            row = db.execute(
                text("SELECT id, name, email_verified FROM users WHERE email = :email"),
                {"email": body.email.lower()},
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            if row[2]:
                return _ok({"message": "Email is already verified"})
            verification_token = str(uuid.uuid4())
            verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)
            db.execute(
                text("""
                    UPDATE users SET verification_token = :token, verification_token_expires = :expires
                    WHERE email = :email
                """),
                {"token": verification_token, "expires": verification_expires, "email": body.email.lower()},
            )
            db.commit()
            user_name = row[1] or body.email.split("@")[0]
            html = _build_verification_email(user_name, verification_token)
            _send_email(body.email.lower(), "Verify your HireAI email address", html)
            return _ok({"message": "Verification email sent"})
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Send verification email failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# GET /auth/verify-email — Verify email with token
# ============================================================================


@router.get("/verify-email")
async def verify_email(token: str = Query(...)):
    """Verify a user's email address using the token."""
    try:
        db = SessionLocal()
        try:
            _ensure_users_table(db)
            row = db.execute(
                text("SELECT id, email, verification_token_expires, email_verified FROM users WHERE verification_token = :token"),
                {"token": token},
            ).fetchone()
            if not row:
                raise HTTPException(status_code=400, detail="Invalid verification token")
            if row[3]:
                return _ok({"message": "Email is already verified"})
            if row[2] and datetime.now(timezone.utc) > row[2].replace(tzinfo=timezone.utc):
                raise HTTPException(status_code=400, detail="Token expired. Please request a new one.")
            db.execute(
                text("UPDATE users SET email_verified = true, verification_token = NULL, verification_token_expires = NULL WHERE id = :uid"),
                {"uid": row[0]},
            )
            db.commit()
            logger.info("Email verified for: %s", row[1])
            return _ok({"message": "Email verified successfully"})
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Verify email failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# POST /auth/forgot-password — Send password reset email
# ============================================================================


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    """Send a password reset email."""
    if not body.email:
        raise HTTPException(status_code=400, detail="Email is required")
    try:
        db = SessionLocal()
        try:
            _ensure_users_table(db)
            row = db.execute(
                text("SELECT id, name, provider FROM users WHERE email = :email"),
                {"email": body.email.lower()},
            ).fetchone()
            if not row:
                return _ok({"message": "If an account exists, a reset link has been sent."})
            if row[2] == "google":
                return _ok({"message": "This account uses Google sign-in. Please log in with Google."})
            reset_token = str(uuid.uuid4())
            reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
            db.execute(
                text("UPDATE users SET reset_token = :token, reset_token_expires = :expires WHERE email = :email"),
                {"token": reset_token, "expires": reset_expires, "email": body.email.lower()},
            )
            db.commit()
            html = _build_reset_email(row[1] or body.email.split("@")[0], reset_token)
            _send_email(body.email.lower(), "Reset your HireAI password", html)
            return _ok({"message": "If an account exists, a reset link has been sent."})
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Forgot password failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# POST /auth/reset-password — Reset password with token
# ============================================================================


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    """Reset password using token from email."""
    if not body.token or not body.new_password:
        raise HTTPException(status_code=400, detail="Token and new password required")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    try:
        db = SessionLocal()
        try:
            _ensure_users_table(db)
            row = db.execute(
                text("SELECT id, email, reset_token_expires FROM users WHERE reset_token = :token"),
                {"token": body.token},
            ).fetchone()
            if not row:
                raise HTTPException(status_code=400, detail="Invalid or expired reset token")
            if row[2] and datetime.now(timezone.utc) > row[2].replace(tzinfo=timezone.utc):
                raise HTTPException(status_code=400, detail="Reset token expired. Please request a new one.")
            db.execute(
                text("UPDATE users SET password_hash = :pw, reset_token = NULL, reset_token_expires = NULL WHERE id = :uid"),
                {"pw": _hash_password(body.new_password), "uid": row[0]},
            )
            db.commit()
            logger.info("Password reset for: %s", row[1])
            return _ok({"message": "Password reset successfully"})
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Reset password failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# POST /auth/setup — Save setup data + mark complete + create agent record
# ============================================================================


def _ensure_user_agents_table(db):
    """Create user_agents table if it doesn't exist."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS user_agents (
            id SERIAL PRIMARY KEY,
            user_id TEXT UNIQUE NOT NULL,
            agent_type TEXT DEFAULT 'general',
            tier TEXT DEFAULT 'trial',
            model TEXT DEFAULT 'gemini',
            ai_provider TEXT DEFAULT 'gemini',
            ai_api_key TEXT,
            gmail_email TEXT,
            gmail_token_valid BOOLEAN DEFAULT false,
            is_paused BOOLEAN DEFAULT false,
            test_mode BOOLEAN DEFAULT false,
            config JSONB DEFAULT '{}',
            last_processed_at TIMESTAMP,
            last_error TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))
    # Add columns for existing tables
    for col in [
        "ai_provider TEXT DEFAULT 'gemini'",
        "ai_api_key TEXT",
    ]:
        try:
            db.execute(text(f"ALTER TABLE user_agents ADD COLUMN IF NOT EXISTS {col}"))
        except Exception:
            pass
    db.commit()


@router.options("/setup")
async def setup_options():
    return {}


@router.options("/mark-complete")
async def mark_complete_options():
    return {}


@router.options("/complete-setup")
async def complete_setup_options():
    return {}


@router.post("/setup")
async def save_setup(body: SetupRequest):
    """Save all setup data, create agent record, and mark setup as complete.

    Never returns an error — the wizard must always be allowed to finish.
    """
    email = (body.email or "").strip().lower() or "unknown@user.com"
    logger.info("POST /auth/setup called for email=%s", email)

    try:
        db = SessionLocal()
        try:
            _ensure_users_table(db)
            _ensure_user_agents_table(db)

            # 1. Update user: mark setup complete + save agent_type and name
            result = db.execute(
                text("""
                    UPDATE users
                    SET setup_complete = true,
                        agent_type = :agent_type,
                        name = COALESCE(NULLIF(:user_name, ''), name)
                    WHERE email = :email
                """),
                {
                    "email": email,
                    "agent_type": body.agent_type,
                    "user_name": body.user_name,
                },
            )
            db.commit()

            if result.rowcount == 0:
                # User not found — still return success so wizard finishes
                logger.warning("Setup: user not found for %s, returning success anyway", email)
                return _ok({"message": "Setup complete", "setup_complete": True})

            # 2. Get user ID for the agents table
            user_row = db.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email},
            ).fetchone()

            if not user_row:
                return _ok({"message": "Setup complete", "setup_complete": True})

            user_id = user_row[0]
            config_json = json.dumps({
                "business_name": body.business_name,
                "user_name": body.user_name,
                "reply_tone": body.reply_tone,
                "working_hours": {
                    "from": body.working_hours_from,
                    "to": body.working_hours_to,
                },
                "whatsapp_number": body.whatsapp_number,
                "custom_db_url": body.custom_db_url,
            })

            # 3. Upsert user_agents record
            db.execute(
                text("""
                    INSERT INTO user_agents
                        (user_id, agent_type, ai_provider, ai_api_key,
                         gmail_email, model, config, is_paused)
                    VALUES
                        (:uid, :agent_type, :ai_provider, :ai_api_key,
                         :gmail, :model, :config::jsonb, false)
                    ON CONFLICT (user_id) DO UPDATE SET
                        agent_type = EXCLUDED.agent_type,
                        ai_provider = EXCLUDED.ai_provider,
                        ai_api_key = COALESCE(EXCLUDED.ai_api_key, user_agents.ai_api_key),
                        gmail_email = EXCLUDED.gmail_email,
                        model = EXCLUDED.model,
                        config = EXCLUDED.config,
                        is_paused = false,
                        updated_at = NOW()
                """),
                {
                    "uid": user_id,
                    "agent_type": body.agent_type,
                    "ai_provider": body.ai_model,
                    "ai_api_key": body.ai_api_key,
                    "gmail": body.gmail_address,
                    "model": body.ai_model,
                    "config": config_json,
                },
            )
            db.commit()

            logger.info("Setup complete for user: %s", email)

            # Auto-start the agent via Celery task
            try:
                from scheduler.tasks import run_gmailmind_for_user
                run_gmailmind_for_user.delay(str(user_id))
                logger.info("Auto-started agent for user: %s (id=%s)", email, user_id)
            except Exception as auto_exc:
                logger.warning("Could not auto-start agent: %s", auto_exc)
                # Non-fatal — user can start manually

        finally:
            db.close()
    except Exception as exc:
        logger.error("Setup failed (non-fatal): %s", exc)

    return _ok({"message": "Setup complete", "setup_complete": True})


# ============================================================================
# POST /auth/mark-complete — Bullet-proof setup completion (never fails)
# ============================================================================


class MarkCompleteRequest(BaseModel):
    email: str


@router.post("/mark-complete")
async def mark_complete(body: MarkCompleteRequest):
    """Mark setup as complete — NEVER returns an error.

    This is the last-resort endpoint called by the frontend setup wizard.
    Even if the database is down, it returns success so the user is never
    stuck in the wizard loop.
    """
    email = (body.email or "").strip().lower()
    try:
        db = SessionLocal()
        try:
            _ensure_users_table(db)
            db.execute(
                text("UPDATE users SET setup_complete = true WHERE email = :email"),
                {"email": email},
            )
            db.commit()
            logger.info("mark-complete: setup_complete=true for %s", email)
        finally:
            db.close()
    except Exception as exc:
        logger.error("mark-complete failed (non-fatal): %s", exc)

    # Always return success
    return _ok({"message": "Setup marked complete", "setup_complete": True})


# ============================================================================
# POST /auth/complete-setup — Mark setup as complete
# ============================================================================


@router.post("/complete-setup")
async def complete_setup(body: CompleteSetupRequest):
    """Mark a user's setup as complete."""
    if not body.email:
        raise HTTPException(status_code=400, detail="Email is required")
    try:
        db = SessionLocal()
        try:
            _ensure_users_table(db)
            result = db.execute(
                text("UPDATE users SET setup_complete = true WHERE email = :email"),
                {"email": body.email.lower()},
            )
            db.commit()
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found")
            return _ok({"message": "Setup complete", "setup_complete": True})
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Complete setup failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# GET /auth/setup-status/{email} — Get setup completion status
# ============================================================================


@router.get("/setup-status/{email}")
async def get_setup_status(email: str):
    """Get setup completion status."""
    try:
        db = SessionLocal()
        try:
            _ensure_users_table(db)
            row = db.execute(
                text("SELECT setup_complete FROM users WHERE email = :email"),
                {"email": email.lower()},
            ).fetchone()
            return _ok({"setup_complete": row[0] if row and row[0] else False})
        finally:
            db.close()
    except Exception as exc:
        logger.error("Get setup status failed: %s", exc)
        return _ok({"setup_complete": False})


# ============================================================================
# GET /auth/debug/{email} — Debug user state (for troubleshooting)
# ============================================================================


@router.get("/debug/{email}")
async def debug_user(email: str):
    """Return full user state for debugging the setup loop issue."""
    try:
        db = SessionLocal()
        try:
            _ensure_users_table(db)
            row = db.execute(
                text("""
                    SELECT id, email, name, provider, tier, agent_type,
                           is_active, setup_complete, email_verified, created_at
                    FROM users WHERE email = :email
                """),
                {"email": email.lower()},
            ).fetchone()

            if not row:
                return {
                    "found": False,
                    "email": email.lower(),
                    "message": "User not found in database",
                }

            # Also check user_agents table
            agent_row = None
            try:
                agent_row = db.execute(
                    text("""
                        SELECT user_id, agent_type, ai_provider, gmail_email,
                               gmail_token_valid, is_paused, created_at
                        FROM user_agents WHERE user_id = :uid
                    """),
                    {"uid": row[0]},
                ).fetchone()
            except Exception:
                pass

            return {
                "found": True,
                "user": {
                    "id": row[0],
                    "email": row[1],
                    "name": row[2],
                    "provider": row[3],
                    "tier": row[4],
                    "agent_type": row[5],
                    "is_active": row[6],
                    "setup_complete": row[7],
                    "email_verified": row[8],
                    "created_at": str(row[9]) if row[9] else None,
                },
                "agent": {
                    "user_id": agent_row[0],
                    "agent_type": agent_row[1],
                    "ai_provider": agent_row[2],
                    "gmail_email": agent_row[3],
                    "gmail_token_valid": agent_row[4],
                    "is_paused": agent_row[5],
                    "created_at": str(agent_row[6]) if agent_row[6] else None,
                } if agent_row else None,
            }
        finally:
            db.close()
    except Exception as exc:
        logger.error("Debug user failed: %s", exc)
        return {"found": False, "error": str(exc)}
