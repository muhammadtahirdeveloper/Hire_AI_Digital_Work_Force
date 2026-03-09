"""One-time migration script to encrypt existing OAuth tokens.

Reads all existing user_credentials from the database and encrypts
any plain text tokens using the EncryptionManager.

Usage::

    python -m scripts.encrypt_existing_tokens

This script is idempotent - it will only encrypt tokens that are
currently stored as plain text. Already encrypted tokens are skipped.
"""

import json
import logging
import sys
import os

# Ensure the project root is on sys.path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from sqlalchemy import text

from config.database import engine
from security.encryption import EncryptionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def encrypt_existing_tokens():
    """Migrate plain text tokens to encrypted format."""

    print("=" * 60)
    print(" GmailMind — Encrypt Existing OAuth Tokens")
    print("=" * 60)
    print()

    encryption_manager = EncryptionManager()

    with engine.connect() as conn:
        # Fetch all user credentials
        result = conn.execute(
            text("SELECT user_id, encrypted_creds FROM user_credentials")
        ).fetchall()

        if not result:
            print("[encrypt_existing_tokens] No user credentials found in database.")
            print()
            return

        print(f"[encrypt_existing_tokens] Found {len(result)} user credential(s).")
        print()

        encrypted_count = 0
        skipped_count = 0
        error_count = 0

        for user_id, creds_json in result:
            try:
                # Parse JSON
                credentials = json.loads(creds_json)

                # Check if access_token is already encrypted
                access_token = credentials.get('access_token', '')
                if encryption_manager.is_encrypted(access_token):
                    print(f"[encrypt_existing_tokens] Skipping {user_id} (already encrypted)")
                    skipped_count += 1
                    continue

                # Encrypt the tokens
                print(f"[encrypt_existing_tokens] Encrypting tokens for {user_id}...")
                encrypted_credentials = encryption_manager.encrypt_dict(
                    credentials,
                    fields=['access_token', 'refresh_token']
                )

                # Save back to database
                encrypted_json = json.dumps(encrypted_credentials)
                conn.execute(
                    text("""
                        UPDATE user_credentials
                        SET encrypted_creds = :creds, updated_at = NOW()
                        WHERE user_id = :user_id
                    """),
                    {"user_id": user_id, "creds": encrypted_json}
                )

                print(f"[encrypt_existing_tokens] ✓ Encrypted tokens for {user_id}")
                encrypted_count += 1

            except json.JSONDecodeError as exc:
                logger.error(f"[encrypt_existing_tokens] Invalid JSON for {user_id}: {exc}")
                error_count += 1
            except Exception as exc:
                logger.error(f"[encrypt_existing_tokens] Failed to encrypt {user_id}: {exc}")
                error_count += 1

        # Commit all changes
        conn.commit()

    print()
    print("=" * 60)
    print(" Migration Summary")
    print("=" * 60)
    print(f"  Total credentials: {len(result)}")
    print(f"  Encrypted: {encrypted_count}")
    print(f"  Skipped (already encrypted): {skipped_count}")
    print(f"  Errors: {error_count}")
    print()

    if encrypted_count > 0:
        print("✓ Migration completed successfully!")
    elif skipped_count > 0:
        print("✓ All tokens already encrypted. Nothing to do.")
    else:
        print("⚠ No tokens were encrypted. Check for errors above.")

    print()


if __name__ == "__main__":
    encrypt_existing_tokens()
