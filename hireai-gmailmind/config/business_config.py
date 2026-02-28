"""Business configuration loader for GmailMind.

Loads the user's business goals, personality preferences, custom rules,
and operational settings. These are injected into the agent's system prompt
so that GmailMind pursues the user's objectives autonomously.

The config can be loaded from a database record (for multi-user SaaS) or
from a local JSON/dict for single-user setups.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default business configuration — used when no user-specific config exists.
DEFAULT_CONFIG: dict[str, Any] = {
    # --- Identity ---
    "business_name": "My Business",
    "owner_name": "Owner",
    "owner_email": "",
    "business_type": "general",  # e.g. "agency", "saas", "consulting", "ecommerce"

    # --- Active Business Goals ---
    "business_goals": [
        "Respond to potential clients quickly",
        "Never miss a follow-up",
        "Keep inbox organized and clean",
    ],

    # --- Personality & Tone ---
    "reply_tone": "professional-friendly",  # professional, friendly, formal, casual
    "language": "English",
    "signature": "",

    # --- Autonomy Levels ---
    "autonomy": {
        "auto_reply_known_contacts": True,
        "auto_reply_new_leads": False,    # create draft instead
        "auto_label_and_archive": True,
        "auto_schedule_followups": True,
        "escalate_unknown_senders": False,
    },

    # --- Category Rules ---
    "category_rules": {
        "lead": {
            "action": "draft_reply",
            "priority": "high",
            "notify": True,
        },
        "client": {
            "action": "auto_reply",
            "priority": "high",
            "notify": False,
        },
        "vendor": {
            "action": "label_and_archive",
            "priority": "low",
            "notify": False,
        },
        "newsletter": {
            "action": "archive",
            "priority": "low",
            "notify": False,
        },
        "spam": {
            "action": "label_spam_and_archive",
            "priority": "none",
            "notify": False,
        },
        "urgent": {
            "action": "escalate",
            "priority": "critical",
            "notify": True,
        },
    },

    # --- Follow-up Settings ---
    "followup_defaults": {
        "lead_followup_hours": 24,
        "client_followup_hours": 48,
        "vendor_followup_hours": 72,
    },

    # --- Working Hours ---
    "working_hours": {
        "timezone": "Asia/Karachi",
        "start": "09:00",
        "end": "18:00",
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
    },

    # --- Escalation Preferences ---
    "escalation": {
        "channel": "slack",  # "slack" or "whatsapp"
        "urgency_threshold": "high",  # escalate if urgency >= this
    },

    # --- Custom Reply Templates ---
    "reply_templates": {
        "acknowledge_lead": (
            "Thank you for reaching out! I've received your message and "
            "will get back to you shortly with more details."
        ),
        "out_of_office": (
            "Thank you for your email. I'm currently unavailable but will "
            "respond as soon as possible."
        ),
        "meeting_request": (
            "Thank you for your interest in scheduling a meeting. Let me "
            "check my calendar and get back to you with available times."
        ),
    },

    # --- VIP Contacts (always prioritize) ---
    "vip_contacts": [],

    # --- Blocked Senders (never reply) ---
    "blocked_senders": [],
}


def load_business_config(
    user_id: Optional[str] = None,
    config_path: Optional[str] = None,
) -> dict[str, Any]:
    """Load business configuration for a user.

    Resolution order:
    1. If ``config_path`` is given, load from that JSON file.
    2. If ``user_id`` is given, attempt to load from the database.
    3. Fall back to the DEFAULT_CONFIG.

    Args:
        user_id: Optional user identifier for database lookup.
        config_path: Optional path to a JSON config file.

    Returns:
        A complete business configuration dict.
    """
    config = dict(DEFAULT_CONFIG)

    # 1. Try JSON file
    if config_path:
        path = Path(config_path)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    file_config = json.load(f)
                config.update(file_config)
                logger.info("Loaded business config from file: %s", config_path)
                return config
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load config from %s: %s", config_path, exc)

    # 2. Try environment variable pointing to a config file
    env_path = os.getenv("GMAILMIND_BUSINESS_CONFIG")
    if env_path:
        path = Path(env_path)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    file_config = json.load(f)
                config.update(file_config)
                logger.info("Loaded business config from env path: %s", env_path)
                return config
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load config from env %s: %s", env_path, exc)

    # 3. Try database (if user_id provided)
    if user_id:
        db_config = _load_from_database(user_id)
        if db_config:
            config.update(db_config)
            logger.info("Loaded business config from database for user: %s", user_id)
            return config

    logger.info("Using default business config (no user-specific config found).")
    return config


def _load_from_database(user_id: str) -> Optional[dict[str, Any]]:
    """Attempt to load user config from the database.

    Args:
        user_id: The user identifier.

    Returns:
        Config dict if found, None otherwise.
    """
    try:
        from config.database import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()
        try:
            result = db.execute(
                text("SELECT config_json FROM user_configs WHERE user_id = :uid"),
                {"uid": user_id},
            ).fetchone()

            if result and result[0]:
                return json.loads(result[0]) if isinstance(result[0], str) else result[0]
        finally:
            db.close()
    except Exception as exc:
        logger.debug("Database config lookup failed (table may not exist): %s", exc)

    return None


def format_goals_for_prompt(config: dict[str, Any]) -> str:
    """Format business goals into a string suitable for the agent prompt.

    Args:
        config: The business configuration dict.

    Returns:
        A formatted string listing business goals.
    """
    goals = config.get("business_goals", [])
    if not goals:
        return "No specific business goals configured."

    lines = [f"  {i}. {goal}" for i, goal in enumerate(goals, 1)]
    return "\n".join(lines)


def format_rules_for_prompt(config: dict[str, Any]) -> str:
    """Format category rules into a string suitable for the agent prompt.

    Args:
        config: The business configuration dict.

    Returns:
        A formatted string describing how to handle each category.
    """
    rules = config.get("category_rules", {})
    if not rules:
        return "No category rules configured."

    lines = []
    for category, rule in rules.items():
        action = rule.get("action", "unknown")
        priority = rule.get("priority", "normal")
        notify = "yes" if rule.get("notify") else "no"
        lines.append(
            f"  - {category.upper()}: action={action}, "
            f"priority={priority}, notify_owner={notify}"
        )
    return "\n".join(lines)
