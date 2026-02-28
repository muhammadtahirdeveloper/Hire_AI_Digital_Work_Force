"""Configuration management endpoints.

Routes:
  GET  /config/{user_id}               — Get agent configuration.
  POST /config/{user_id}               — Save/update agent configuration.
  POST /config/{user_id}/credentials   — Save encrypted OAuth credentials.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import text

from api.middleware import get_current_user
from config.database import SessionLocal
from config.settings import ENCRYPTION_KEY

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Helpers
# ============================================================================


def _ok(data: Any = None) -> dict:
    return {"success": True, "data": data, "error": None}


def _err(message: str) -> dict:
    return {"success": False, "data": None, "error": message}


def _verify_user_access(user: dict, user_id: str) -> None:
    if user.get("sub", "") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own configuration.",
        )


def _encrypt(plaintext: str) -> str:
    """Encrypt a string using Fernet symmetric encryption."""
    from cryptography.fernet import Fernet

    if not ENCRYPTION_KEY:
        raise RuntimeError("ENCRYPTION_KEY is not set. Cannot encrypt credentials.")

    f = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
    return f.encrypt(plaintext.encode()).decode()


def _decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string."""
    from cryptography.fernet import Fernet

    if not ENCRYPTION_KEY:
        raise RuntimeError("ENCRYPTION_KEY is not set. Cannot decrypt credentials.")

    f = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
    return f.decrypt(ciphertext.encode()).decode()


# ============================================================================
# Ensure user_configs table
# ============================================================================

_CREATE_CONFIG_TABLE = """
CREATE TABLE IF NOT EXISTS user_configs (
    user_id      VARCHAR(128) PRIMARY KEY,
    config_json  JSONB NOT NULL DEFAULT '{}',
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""

_CREATE_CREDS_TABLE = """
CREATE TABLE IF NOT EXISTS user_credentials (
    user_id          VARCHAR(128) PRIMARY KEY,
    encrypted_creds  TEXT NOT NULL,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""


def _ensure_tables() -> None:
    try:
        db = SessionLocal()
        try:
            db.execute(text(_CREATE_CONFIG_TABLE))
            db.execute(text(_CREATE_CREDS_TABLE))
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.debug("Config table check skipped: %s", exc)


# ============================================================================
# GET /config/{user_id}
# ============================================================================


@router.get("/{user_id}")
async def get_config(
    user_id: str,
    user: dict = Depends(get_current_user),
):
    """Get the current agent configuration for a user.

    Returns the full business config JSON (goals, autonomy, rules, etc.).
    Falls back to the default config if no custom config is stored.
    """
    _verify_user_access(user, user_id)

    try:
        from config.business_config import load_business_config

        config = load_business_config(user_id=user_id)

        # Remove sensitive fields before returning
        safe_config = {k: v for k, v in config.items() if k != "oauth_token"}

        return _ok(safe_config)

    except Exception as exc:
        logger.exception("Failed to get config for user %s", user_id)
        return _err(f"Failed to get config: {exc}")


# ============================================================================
# POST /config/{user_id}
# ============================================================================


@router.post("/{user_id}")
async def save_config(
    user_id: str,
    config_data: dict = Body(...),
    user: dict = Depends(get_current_user),
):
    """Save or update the agent configuration for a user.

    The entire config JSON is stored. Pass a complete config object
    (use GET first to retrieve the current one, modify, then POST back).
    """
    _verify_user_access(user, user_id)

    # Strip credentials from config storage (stored separately)
    config_data.pop("oauth_token", None)
    config_data.pop("credentials", None)

    try:
        _ensure_tables()

        db = SessionLocal()
        try:
            db.execute(
                text("""
                    INSERT INTO user_configs (user_id, config_json, updated_at)
                    VALUES (:uid, :config, NOW())
                    ON CONFLICT (user_id) DO UPDATE
                        SET config_json = :config,
                            updated_at  = NOW()
                """),
                {"uid": user_id, "config": json.dumps(config_data)},
            )
            db.commit()
        finally:
            db.close()

        logger.info("Config saved for user %s", user_id)
        return _ok({"message": "Configuration saved.", "user_id": user_id})

    except Exception as exc:
        logger.exception("Failed to save config for user %s", user_id)
        return _err(f"Failed to save config: {exc}")


# ============================================================================
# POST /config/{user_id}/credentials
# ============================================================================


@router.post("/{user_id}/credentials")
async def save_credentials(
    user_id: str,
    creds: dict = Body(...),
    user: dict = Depends(get_current_user),
):
    """Save encrypted OAuth/API credentials for a user.

    Expects a JSON body with credential fields such as::

        {
            "access_token": "ya29...",
            "refresh_token": "1//...",
            "token_uri": "https://oauth2.googleapis.com/token"
        }

    The entire payload is encrypted at rest using Fernet.
    """
    _verify_user_access(user, user_id)

    if not ENCRYPTION_KEY:
        return _err("Server encryption key is not configured. Cannot store credentials.")

    try:
        _ensure_tables()

        encrypted = _encrypt(json.dumps(creds))

        db = SessionLocal()
        try:
            db.execute(
                text("""
                    INSERT INTO user_credentials (user_id, encrypted_creds, updated_at)
                    VALUES (:uid, :enc, NOW())
                    ON CONFLICT (user_id) DO UPDATE
                        SET encrypted_creds = :enc,
                            updated_at      = NOW()
                """),
                {"uid": user_id, "enc": encrypted},
            )
            db.commit()
        finally:
            db.close()

        logger.info("Credentials saved (encrypted) for user %s", user_id)
        return _ok({"message": "Credentials saved securely.", "user_id": user_id})

    except Exception as exc:
        logger.exception("Failed to save credentials for user %s", user_id)
        return _err(f"Failed to save credentials: {exc}")
