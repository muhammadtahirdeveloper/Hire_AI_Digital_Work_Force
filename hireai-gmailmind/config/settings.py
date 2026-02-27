"""Application-wide settings loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


# --- Google OAuth 2.0 ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
)
GMAIL_SCOPES = os.getenv(
    "GMAIL_SCOPES",
    "https://www.googleapis.com/auth/gmail.readonly,"
    "https://www.googleapis.com/auth/gmail.send,"
    "https://www.googleapis.com/auth/gmail.modify",
).split(",")

# --- OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# --- Database ---
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:password@localhost:5432/gmailmind"
)

# --- Redis ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# --- Encryption ---
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

# --- App ---
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# --- Google Calendar ---
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")

# --- HubSpot CRM ---
HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY", "")
HUBSPOT_BASE_URL = os.getenv(
    "HUBSPOT_BASE_URL", "https://api.hubapi.com"
)

# --- Twilio (WhatsApp Escalation) ---
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")
ESCALATION_WHATSAPP_TO = os.getenv("ESCALATION_WHATSAPP_TO", "")

# --- Slack (Escalation) ---
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# --- Scheduler ---
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))
