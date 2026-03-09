"""Data encryption utilities for GmailMind.

Provides Fernet symmetric encryption for sensitive data like OAuth tokens.
"""

import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages encryption and decryption of sensitive data using Fernet."""

    def __init__(self):
        """Initialize encryption manager with key from environment.

        If ENCRYPTION_KEY is not set, generates a new key and logs a warning.
        This is acceptable for development but should be configured in production.
        """
        encryption_key = os.getenv('ENCRYPTION_KEY')

        if not encryption_key:
            # Generate a new key for development
            encryption_key = Fernet.generate_key().decode()
            logger.warning(
                "[EncryptionManager] ENCRYPTION_KEY not set in environment. "
                f"Generated temporary key. For production, set ENCRYPTION_KEY in .env"
            )

        # If key is a string, encode it to bytes
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()

        try:
            self.fernet = Fernet(encryption_key)
            logger.info("[EncryptionManager] Encryption initialized successfully")
        except Exception as exc:
            logger.error(f"[EncryptionManager] Failed to initialize Fernet: {exc}")
            raise

    def encrypt(self, plain_text: str) -> str:
        """Encrypt a plain text string.

        Args:
            plain_text: Plain text to encrypt

        Returns:
            str: Base64 encoded encrypted string
        """
        if not plain_text:
            return plain_text

        try:
            encrypted_bytes = self.fernet.encrypt(plain_text.encode())
            encrypted_str = encrypted_bytes.decode()
            logger.debug("[EncryptionManager] Successfully encrypted data")
            return encrypted_str
        except Exception as exc:
            logger.error(f"[EncryptionManager] Encryption failed: {exc}")
            raise

    def decrypt(self, encrypted_text: str) -> Optional[str]:
        """Decrypt an encrypted string.

        Args:
            encrypted_text: Base64 encoded encrypted string

        Returns:
            str: Decrypted plain text
            None: If decryption fails
        """
        if not encrypted_text:
            return encrypted_text

        try:
            decrypted_bytes = self.fernet.decrypt(encrypted_text.encode())
            decrypted_str = decrypted_bytes.decode()
            logger.debug("[EncryptionManager] Successfully decrypted data")
            return decrypted_str
        except InvalidToken:
            logger.warning("[EncryptionManager] Invalid token - data may not be encrypted")
            return None
        except Exception as exc:
            logger.error(f"[EncryptionManager] Decryption failed: {exc}")
            return None

    def encrypt_dict(self, data: dict, fields: list) -> dict:
        """Encrypt specific fields in a dictionary.

        Args:
            data: Dictionary containing fields to encrypt
            fields: List of field names to encrypt

        Returns:
            dict: Dictionary with specified fields encrypted
        """
        encrypted_data = data.copy()

        for field in fields:
            if field in encrypted_data and encrypted_data[field]:
                try:
                    encrypted_data[field] = self.encrypt(encrypted_data[field])
                    logger.debug(f"[EncryptionManager] Encrypted field: {field}")
                except Exception as exc:
                    logger.error(f"[EncryptionManager] Failed to encrypt field {field}: {exc}")
                    # Keep original value if encryption fails

        return encrypted_data

    def decrypt_dict(self, data: dict, fields: list) -> dict:
        """Decrypt specific fields in a dictionary.

        Args:
            data: Dictionary containing encrypted fields
            fields: List of field names to decrypt

        Returns:
            dict: Dictionary with specified fields decrypted
        """
        decrypted_data = data.copy()

        for field in fields:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_value = self.decrypt(decrypted_data[field])

                    if decrypted_value is None:
                        # Decryption failed - assume it's plain text (legacy data)
                        logger.warning(
                            f"[EncryptionManager] Field {field} appears to be plain text. "
                            "Using as-is for backward compatibility."
                        )
                        # Keep original value
                    else:
                        decrypted_data[field] = decrypted_value
                        logger.debug(f"[EncryptionManager] Decrypted field: {field}")
                except Exception as exc:
                    logger.error(f"[EncryptionManager] Failed to decrypt field {field}: {exc}")
                    # Keep original value if decryption fails

        return decrypted_data

    def is_encrypted(self, text: str) -> bool:
        """Check if a text string appears to be encrypted.

        Args:
            text: Text to check

        Returns:
            bool: True if text is encrypted, False otherwise
        """
        if not text:
            return False

        try:
            self.decrypt(text)
            return True
        except Exception:
            return False
