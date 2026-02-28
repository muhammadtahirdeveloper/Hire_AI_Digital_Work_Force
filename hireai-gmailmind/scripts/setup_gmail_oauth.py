"""Interactive Gmail OAuth2 setup for GmailMind.

Guides the user step-by-step through the Google OAuth2 consent flow,
obtains access + refresh tokens, and saves them securely (encrypted)
for use by the GmailMind agent.

Usage::

    python -m scripts.setup_gmail_oauth
"""

import json
import os
import sys

# Ensure project root is on sys.path.
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from config.settings import (
    ENCRYPTION_KEY,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GMAIL_SCOPES,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CREDENTIALS_FILE = os.path.join(_project_root, "credentials.json")
TOKEN_FILE = os.path.join(_project_root, "token.json")


def _banner() -> None:
    print()
    print("=" * 55)
    print("  GmailMind — Gmail OAuth2 Setup Wizard")
    print("=" * 55)
    print()


def _check_prerequisites() -> bool:
    """Verify that required environment variables are set."""
    ok = True
    if not GOOGLE_CLIENT_ID:
        print("[ERROR] GOOGLE_CLIENT_ID is not set in .env")
        ok = False
    if not GOOGLE_CLIENT_SECRET:
        print("[ERROR] GOOGLE_CLIENT_SECRET is not set in .env")
        ok = False
    if not ENCRYPTION_KEY:
        print("[WARNING] ENCRYPTION_KEY is not set — tokens will be saved "
              "as plain JSON. Set ENCRYPTION_KEY in .env for encrypted storage.")
    return ok


def _print_instructions() -> None:
    """Print step-by-step instructions for getting Google OAuth credentials."""
    print("Before we begin, make sure you have a Google Cloud project with")
    print("the Gmail API enabled. If not, follow these steps:\n")
    print("  1. Go to https://console.cloud.google.com/")
    print("  2. Create a new project (or select existing)")
    print("  3. Navigate to 'APIs & Services' > 'Library'")
    print("  4. Search for 'Gmail API' and click 'Enable'")
    print("  5. Also enable 'Google Calendar API' (optional)")
    print("  6. Go to 'APIs & Services' > 'Credentials'")
    print("  7. Click '+ CREATE CREDENTIALS' > 'OAuth client ID'")
    print("  8. Application type: 'Desktop app'")
    print("  9. Download the JSON file")
    print(" 10. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env")
    print()
    print("Scopes that will be requested:")
    for scope in GMAIL_SCOPES:
        print(f"  - {scope}")
    print()


def _run_oauth_flow() -> dict:
    """Run the OAuth2 installed-app flow and return token data."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_config = {
        "installed": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": ["http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, scopes=GMAIL_SCOPES)

    print("Opening browser for Google sign-in...")
    print("(If the browser does not open, copy the URL printed below.)\n")

    credentials = flow.run_local_server(port=8090, open_browser=True)

    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes or GMAIL_SCOPES),
        "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
    }

    return token_data


def _save_token_plain(token_data: dict) -> str:
    """Save token data as plain JSON (fallback if no encryption key)."""
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    # Restrict file permissions (Unix only).
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        pass  # Windows doesn't support Unix permissions

    return TOKEN_FILE


def _save_token_encrypted(token_data: dict) -> str:
    """Encrypt and save token data using Fernet."""
    from cryptography.fernet import Fernet

    fernet = Fernet(ENCRYPTION_KEY.encode())
    encrypted = fernet.encrypt(json.dumps(token_data).encode())

    encrypted_path = TOKEN_FILE + ".enc"
    with open(encrypted_path, "wb") as f:
        f.write(encrypted)

    # Restrict file permissions (Unix only).
    try:
        os.chmod(encrypted_path, 0o600)
    except OSError:
        pass

    return encrypted_path


def _verify_credentials(token_data: dict) -> bool:
    """Quick test — list Gmail labels to verify the token works."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=token_data["token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data["scopes"],
    )

    try:
        service = build("gmail", "v1", credentials=creds)
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])
        print(f"[OK] Successfully connected to Gmail! Found {len(labels)} labels.")
        return True
    except Exception as exc:
        print(f"[ERROR] Failed to verify credentials: {exc}")
        return False


def main() -> None:
    """Run the complete OAuth setup wizard."""
    _banner()

    if not _check_prerequisites():
        print("\nPlease fix the errors above and try again.")
        sys.exit(1)

    _print_instructions()

    input("Press Enter when you are ready to start the OAuth flow... ")
    print()

    # Run the flow
    try:
        token_data = _run_oauth_flow()
    except Exception as exc:
        print(f"\n[ERROR] OAuth flow failed: {exc}")
        print("Make sure your GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are correct.")
        sys.exit(1)

    print("\n[OK] OAuth tokens obtained successfully!")

    # Save credentials
    if ENCRYPTION_KEY:
        path = _save_token_encrypted(token_data)
        print(f"[OK] Encrypted credentials saved to: {path}")
    else:
        path = _save_token_plain(token_data)
        print(f"[OK] Credentials saved to: {path}")

    # Verify
    print("\nVerifying credentials...")
    if _verify_credentials(token_data):
        print("\n" + "=" * 55)
        print("  Setup complete! GmailMind can now access your Gmail.")
        print("=" * 55)
    else:
        print("\n[WARNING] Verification failed, but tokens were saved.")
        print("The agent may still work — check your API settings.")


if __name__ == "__main__":
    main()
