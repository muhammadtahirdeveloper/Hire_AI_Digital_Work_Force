"""API Key authentication for GmailMind.

Provides secure API key generation, validation, and management.
"""

import hashlib
import logging
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import text

from config.database import engine

logger = logging.getLogger(__name__)


def generate_api_key() -> str:
    """Generate a secure random API key.

    Returns:
        str: API key with prefix 'gmsk_' (GmailMind Secret Key)
        Example: 'gmsk_xK9mP2nL8qR5vT3wY7zA4bC6dE0fG1hJ'
    """
    random_part = secrets.token_urlsafe(32)
    return f"gmsk_{random_part}"


class APIKeyManager:
    """Manages API key creation, validation, and revocation."""

    @staticmethod
    def _hash_key(api_key: str) -> str:
        """Hash an API key using SHA-256.

        Args:
            api_key: Plain text API key

        Returns:
            str: SHA-256 hash of the key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    def create_api_key(self, user_id: str, name: str) -> dict:
        """Create a new API key for a user.

        Args:
            user_id: User identifier
            name: Descriptive name for the key

        Returns:
            dict: {api_key: str, key_id: int, name: str}
            Note: The plain api_key is returned ONLY ONCE
        """
        api_key = generate_api_key()
        key_hash = self._hash_key(api_key)

        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO api_keys (user_id, name, key_hash)
                    VALUES (:user_id, :name, :key_hash)
                    RETURNING id
                """),
                {"user_id": user_id, "name": name, "key_hash": key_hash}
            )
            conn.commit()
            key_id = result.fetchone()[0]

        logger.info(f"[APIKeyManager] Created API key id={key_id} for user={user_id} name={name}")

        return {
            "api_key": api_key,
            "key_id": key_id,
            "name": name
        }

    def validate_api_key(self, api_key: str) -> Optional[dict]:
        """Validate an API key and return user info.

        Args:
            api_key: Plain text API key to validate

        Returns:
            dict: User info if valid {user_id, key_id, name}
            None: If key is invalid or inactive
        """
        key_hash = self._hash_key(api_key)

        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT id, user_id, name, is_active
                    FROM api_keys
                    WHERE key_hash = :key_hash
                """),
                {"key_hash": key_hash}
            ).fetchone()

            if not result:
                logger.warning("[APIKeyManager] Invalid API key attempt")
                return None

            key_id, user_id, name, is_active = result

            if not is_active:
                logger.warning(f"[APIKeyManager] Inactive API key used: key_id={key_id}")
                return None

            # Update last_used timestamp
            conn.execute(
                text("""
                    UPDATE api_keys
                    SET last_used = NOW()
                    WHERE id = :key_id
                """),
                {"key_id": key_id}
            )
            conn.commit()

        logger.debug(f"[APIKeyManager] Valid API key: key_id={key_id} user={user_id}")

        return {
            "user_id": user_id,
            "key_id": key_id,
            "name": name
        }

    def revoke_api_key(self, key_id: int, user_id: str) -> bool:
        """Revoke (deactivate) an API key.

        Args:
            key_id: Key ID to revoke
            user_id: User ID (must match key owner)

        Returns:
            bool: True if revoked, False if not found or permission denied
        """
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    UPDATE api_keys
                    SET is_active = FALSE
                    WHERE id = :key_id AND user_id = :user_id
                    RETURNING id
                """),
                {"key_id": key_id, "user_id": user_id}
            )
            conn.commit()

            if result.fetchone():
                logger.info(f"[APIKeyManager] Revoked API key id={key_id} for user={user_id}")
                return True

            logger.warning(f"[APIKeyManager] Failed to revoke key id={key_id} for user={user_id}")
            return False

    def list_api_keys(self, user_id: str) -> list[dict]:
        """List all API keys for a user.

        Args:
            user_id: User identifier

        Returns:
            list: List of keys (never includes plain key)
                  [{key_id, name, created_at, is_active, last_used}]
        """
        with engine.connect() as conn:
            results = conn.execute(
                text("""
                    SELECT id, name, created_at, is_active, last_used
                    FROM api_keys
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                """),
                {"user_id": user_id}
            ).fetchall()

        keys = []
        for row in results:
            keys.append({
                "key_id": row[0],
                "name": row[1],
                "created_at": row[2].isoformat() if row[2] else None,
                "is_active": row[3],
                "last_used": row[4].isoformat() if row[4] else None
            })

        logger.debug(f"[APIKeyManager] Listed {len(keys)} keys for user={user_id}")
        return keys
