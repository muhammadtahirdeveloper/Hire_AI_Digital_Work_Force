"""Application-wide settings loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


# --- Google OAuth 2.0 ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "https://hireai-backend-an68.onrender.com/auth/google/callback",
)
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# --- Anthropic Claude ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# --- Database ---
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:password@localhost:5432/gmailmind"
)

# --- Redis ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL") or REDIS_URL
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND") or REDIS_URL

# --- Encryption ---
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

# --- App ---
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT") or os.getenv("PORT") or "8000")
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

# --- Safety ---
DAILY_ACTION_LIMIT = int(os.getenv("DAILY_ACTION_LIMIT", "200"))
MAX_RECIPIENTS_PER_SEND = int(os.getenv("MAX_RECIPIENTS_PER_SEND", "50"))

# --- JWT / Auth ---
JWT_SECRET = os.getenv("JWT_SECRET", "hireai-jwt-secret-2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# --- Supabase Auth ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# --- Lemon Squeezy ---
LEMON_SQUEEZY_API_KEY = os.getenv("LEMON_SQUEEZY_API_KEY", "")
LEMON_SQUEEZY_STORE_ID = os.getenv("LEMON_SQUEEZY_STORE_ID", "")
LEMON_SQUEEZY_WEBHOOK_SECRET = os.getenv("LEMON_SQUEEZY_WEBHOOK_SECRET", "")
LEMON_SQUEEZY_STARTER_VARIANT_ID = os.getenv("LEMON_SQUEEZY_STARTER_VARIANT_ID", "")
LEMON_SQUEEZY_PRO_VARIANT_ID = os.getenv("LEMON_SQUEEZY_PRO_VARIANT_ID", "")
LEMON_SQUEEZY_ENTERPRISE_VARIANT_ID = os.getenv("LEMON_SQUEEZY_ENTERPRISE_VARIANT_ID", "")

# --- CORS ---
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")

# --- Scheduler ---
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))

# --- Gmail Push Notifications (Pub/Sub) ---
GOOGLE_PUBSUB_TOPIC = os.getenv(
    "GOOGLE_PUBSUB_TOPIC",
    "projects/hireai-prod/topics/hireai-gmail-notifications",
)
GMAIL_WEBHOOK_URL = os.getenv(
    "GMAIL_WEBHOOK_URL",
    "https://hireai-backend-an68.onrender.com/webhooks/gmail",
)
