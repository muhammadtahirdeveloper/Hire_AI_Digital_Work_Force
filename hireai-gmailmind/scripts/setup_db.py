"""Database initialisation script for GmailMind.

Creates all tables defined in models/schemas.py plus the auxiliary
tables used by the scheduler and API (agent_status, user_configs,
user_credentials, user_subscriptions).

Also creates performance indexes and seeds the database with default
business rule templates.

Usage::

    python -m scripts.setup_db
"""

import json
import sys
import os

# Ensure the project root is on sys.path so that imports work when the
# script is executed directly (e.g. ``python scripts/setup_db.py``).
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from sqlalchemy import text

from config.database import Base, engine


# ============================================================================
# Default business rule templates
# ============================================================================

DEFAULT_BUSINESS_RULES = [
    {
        "name": "Lead Response",
        "description": "Auto-reply to new lead inquiries within minutes",
        "category": "LEAD",
        "action": "auto_reply",
        "priority": "high",
        "template": (
            "Thank you for reaching out! We received your message and will "
            "get back to you shortly. In the meantime, feel free to check "
            "out our website for more information."
        ),
        "conditions": {
            "keywords": ["interested", "pricing", "demo", "quote", "inquiry"],
            "auto_label": "lead",
        },
    },
    {
        "name": "Client Support",
        "description": "Acknowledge client support requests and escalate if urgent",
        "category": "CLIENT",
        "action": "acknowledge_and_escalate",
        "priority": "high",
        "template": (
            "Thank you for contacting support. We have received your request "
            "and our team is looking into it. We will update you shortly."
        ),
        "conditions": {
            "keywords": ["help", "issue", "problem", "bug", "error", "broken"],
            "auto_label": "support",
            "escalate_if": ["urgent", "critical", "down", "outage"],
        },
    },
    {
        "name": "Meeting Request",
        "description": "Check calendar and propose available slots",
        "category": "MEETING",
        "action": "check_calendar_and_reply",
        "priority": "medium",
        "template": (
            "Thank you for your meeting request! Let me check available "
            "slots and get back to you with some options."
        ),
        "conditions": {
            "keywords": ["meeting", "schedule", "call", "availability", "calendar"],
            "auto_label": "meeting",
        },
    },
    {
        "name": "Vendor Communication",
        "description": "Log vendor emails and flag for review",
        "category": "VENDOR",
        "action": "label_and_log",
        "priority": "low",
        "template": None,
        "conditions": {
            "keywords": ["invoice", "payment", "contract", "proposal", "renewal"],
            "auto_label": "vendor",
        },
    },
    {
        "name": "Newsletter / Marketing",
        "description": "Auto-archive newsletters and marketing emails",
        "category": "NEWSLETTER",
        "action": "archive",
        "priority": "low",
        "template": None,
        "conditions": {
            "keywords": ["unsubscribe", "newsletter", "promotional"],
            "auto_label": "newsletter",
            "auto_archive": True,
        },
    },
    {
        "name": "Spam Handling",
        "description": "Detect spam and auto-archive without replying",
        "category": "SPAM",
        "action": "archive_silent",
        "priority": "low",
        "template": None,
        "conditions": {
            "patterns": ["lottery", "winner", "click here", "act now", "limited time"],
            "auto_label": "spam",
            "auto_archive": True,
            "never_reply": True,
        },
    },
    {
        "name": "Urgent Escalation",
        "description": "Immediately escalate urgent emails to owner",
        "category": "URGENT",
        "action": "escalate",
        "priority": "critical",
        "template": None,
        "conditions": {
            "keywords": ["urgent", "asap", "emergency", "legal", "complaint", "lawsuit"],
            "escalate_channel": "whatsapp",
        },
    },
    {
        "name": "Follow-Up Reminder",
        "description": "Set automatic follow-up for emails that need a response",
        "category": "FOLLOWUP",
        "action": "schedule_followup",
        "priority": "medium",
        "template": (
            "Hi, just following up on my previous email. "
            "Please let me know if you need any additional information."
        ),
        "conditions": {
            "follow_up_after_hours": 48,
            "max_followups": 3,
        },
    },
]


def create_tables() -> None:
    """Create all ORM-managed tables and auxiliary tables."""

    # Enable pgvector extension (safe to call repeatedly).
    with engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("[setup_db] pgvector extension enabled.")
        except Exception as exc:
            print(f"[setup_db] pgvector extension skipped: {exc}")

    # Import ORM models so they register with Base.metadata.
    import models.schemas  # noqa: F401

    # Create all tables declared via DeclarativeBase.
    Base.metadata.create_all(bind=engine)
    print("[setup_db] ORM tables created:")
    for table_name in sorted(Base.metadata.tables):
        print(f"  - {table_name}")

    # Auxiliary tables used by scheduler/tasks.py and api/ routes.
    _auxiliary_sql = [
        # Agent runtime status
        """
        CREATE TABLE IF NOT EXISTS agent_status (
            user_id    VARCHAR(128) PRIMARY KEY,
            status     VARCHAR(32)  NOT NULL DEFAULT 'idle',
            last_run   TIMESTAMP WITH TIME ZONE,
            error_msg  TEXT,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        # User business configuration (JSON)
        """
        CREATE TABLE IF NOT EXISTS user_configs (
            user_id     VARCHAR(128) PRIMARY KEY,
            config_json JSONB NOT NULL DEFAULT '{}',
            created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        # Encrypted OAuth / API credentials
        """
        CREATE TABLE IF NOT EXISTS user_credentials (
            user_id         VARCHAR(128) PRIMARY KEY,
            encrypted_creds TEXT NOT NULL,
            created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        # Subscription tracking
        """
        CREATE TABLE IF NOT EXISTS user_subscriptions (
            user_id    VARCHAR(128) PRIMARY KEY,
            status     VARCHAR(32)  NOT NULL DEFAULT 'active',
            plan       VARCHAR(64)  DEFAULT 'free',
            expires_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        # Business rule templates
        """
        CREATE TABLE IF NOT EXISTS business_rule_templates (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(128) NOT NULL UNIQUE,
            description TEXT,
            category    VARCHAR(64) NOT NULL,
            action      VARCHAR(64) NOT NULL,
            priority    VARCHAR(32) NOT NULL DEFAULT 'medium',
            template    TEXT,
            conditions  JSONB NOT NULL DEFAULT '{}',
            is_active   BOOLEAN NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
    ]

    with engine.connect() as conn:
        for stmt in _auxiliary_sql:
            conn.execute(text(stmt))
        conn.commit()

    print("[setup_db] Auxiliary tables created:")
    print("  - agent_status")
    print("  - user_configs")
    print("  - user_credentials")
    print("  - user_subscriptions")
    print("  - business_rule_templates")


def create_indexes() -> None:
    """Create additional performance indexes on auxiliary tables."""

    _index_sql = [
        "CREATE INDEX IF NOT EXISTS ix_agent_status_status ON agent_status(status);",
        "CREATE INDEX IF NOT EXISTS ix_agent_status_last_run ON agent_status(last_run);",
        "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_status ON user_subscriptions(status);",
        "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_expires ON user_subscriptions(expires_at);",
        "CREATE INDEX IF NOT EXISTS ix_business_rules_category ON business_rule_templates(category);",
        "CREATE INDEX IF NOT EXISTS ix_business_rules_active ON business_rule_templates(is_active);",
    ]

    with engine.connect() as conn:
        for stmt in _index_sql:
            conn.execute(text(stmt))
        conn.commit()

    print("[setup_db] Indexes created on auxiliary tables.")


def seed_business_rules() -> None:
    """Insert default business rule templates (skip if they already exist)."""

    inserted = 0
    with engine.connect() as conn:
        for rule in DEFAULT_BUSINESS_RULES:
            # Only insert if not already present (idempotent).
            exists = conn.execute(
                text("SELECT 1 FROM business_rule_templates WHERE name = :name"),
                {"name": rule["name"]},
            ).fetchone()
            if exists:
                continue

            conn.execute(
                text(
                    """
                    INSERT INTO business_rule_templates
                        (name, description, category, action, priority, template, conditions)
                    VALUES
                        (:name, :description, :category, :action, :priority, :template, :conditions)
                    """
                ),
                {
                    "name": rule["name"],
                    "description": rule["description"],
                    "category": rule["category"],
                    "action": rule["action"],
                    "priority": rule["priority"],
                    "template": rule["template"],
                    "conditions": json.dumps(rule["conditions"]),
                },
            )
            inserted += 1

        conn.commit()

    print(f"[setup_db] Business rule templates seeded: {inserted} new, "
          f"{len(DEFAULT_BUSINESS_RULES) - inserted} already existed.")


def create_hr_tables() -> None:
    """Create HR-specific tables for recruitment workflows."""

    _hr_sql = [
        # Candidates table
        """
        CREATE TABLE IF NOT EXISTS candidates (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            name VARCHAR(255),
            phone VARCHAR(50),
            current_role VARCHAR(255),
            experience_years INTEGER DEFAULT 0,
            skills JSONB DEFAULT '[]',
            education TEXT,
            location VARCHAR(255),
            cv_score INTEGER DEFAULT 0,
            stage VARCHAR(50) DEFAULT 'applied',
            job_title_applied VARCHAR(255),
            notes TEXT,
            source_email_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id, email)
        );
        """,
        # Interviews table
        """
        CREATE TABLE IF NOT EXISTS interviews (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            candidate_email VARCHAR(255) NOT NULL,
            scheduled_at TIMESTAMP NOT NULL,
            duration_minutes INTEGER DEFAULT 60,
            interview_type VARCHAR(50) DEFAULT 'video',
            calendar_event_id VARCHAR(255),
            status VARCHAR(50) DEFAULT 'scheduled',
            notes TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """,
        # Job requirements table
        """
        CREATE TABLE IF NOT EXISTS job_requirements (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            job_title VARCHAR(255) NOT NULL,
            required_skills JSONB DEFAULT '[]',
            min_experience_years INTEGER DEFAULT 0,
            location VARCHAR(255),
            salary_range VARCHAR(100),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """,
    ]

    with engine.connect() as conn:
        for stmt in _hr_sql:
            conn.execute(text(stmt))
        conn.commit()

    print("[setup_db] HR tables created:")
    print("  - candidates")
    print("  - interviews")
    print("  - job_requirements")


def create_hr_indexes() -> None:
    """Create indexes on HR tables for query performance."""

    _hr_index_sql = [
        "CREATE INDEX IF NOT EXISTS idx_candidates_user_id ON candidates(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_candidates_stage ON candidates(stage);",
        "CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates(user_id, email);",
        "CREATE INDEX IF NOT EXISTS idx_interviews_user_id ON interviews(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_interviews_scheduled ON interviews(scheduled_at);",
        "CREATE INDEX IF NOT EXISTS idx_job_requirements_user_id ON job_requirements(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_job_requirements_active ON job_requirements(is_active);",
    ]

    with engine.connect() as conn:
        for stmt in _hr_index_sql:
            conn.execute(text(stmt))
        conn.commit()

    print("[setup_db] HR indexes created.")


def add_phase2_columns() -> None:
    """Add Phase 2 columns to existing tables (idempotent)."""

    _alter_sql = [
        # Add tier column to user_subscriptions
        "ALTER TABLE user_subscriptions ADD COLUMN IF NOT EXISTS tier VARCHAR(10) DEFAULT 'tier2';",
        # Add industry column to user_configs
        "ALTER TABLE user_configs ADD COLUMN IF NOT EXISTS industry VARCHAR(20) DEFAULT 'general';",
    ]

    with engine.connect() as conn:
        for stmt in _alter_sql:
            try:
                conn.execute(text(stmt))
            except Exception as exc:
                print(f"[setup_db] Column migration skipped: {exc}")
        conn.commit()

    print("[setup_db] Phase 2 columns added:")
    print("  - user_subscriptions.tier (default: tier2)")
    print("  - user_configs.industry (default: general)")


def main() -> None:
    """Run full database setup: tables, indexes, seed data, Phase 2 columns."""
    print("=" * 50)
    print(" GmailMind — Database Setup")
    print("=" * 50)
    print()

    create_tables()
    print()
    create_indexes()
    print()
    seed_business_rules()
    print()
    add_phase2_columns()
    print()
    create_hr_tables()
    print()
    create_hr_indexes()

    print()
    print("[setup_db] All done. Database is ready.")


if __name__ == "__main__":
    main()
