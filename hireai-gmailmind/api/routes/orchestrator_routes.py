"""Orchestrator & Platform management endpoints.

Routes:
  GET  /platform/stats                    — Platform-wide statistics.
  POST /platform/users/{user_id}/setup    — Set up user industry and tier.
  GET  /platform/users/{user_id}/agent-info — Get user's agent routing info.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body
from sqlalchemy import text

from config.database import SessionLocal
from orchestrator.feature_gates import FeatureGate
from orchestrator.orchestrator import GmailMindOrchestrator
from orchestrator.user_router import UserRouter

logger = logging.getLogger(__name__)

router = APIRouter()

# Shared instances
_orchestrator = GmailMindOrchestrator()
_gates = FeatureGate()
_user_router = UserRouter()


# ============================================================================
# Helpers
# ============================================================================


def _ok(data: Any = None) -> dict:
    return {"success": True, "data": data, "error": None}


def _err(message: str) -> dict:
    return {"success": False, "data": None, "error": message}


# ============================================================================
# GET /platform/stats
# ============================================================================


@router.get("/stats", tags=["Platform"])
async def platform_stats():
    """Get platform-wide statistics.

    Returns active user count, emails processed today, and per-agent counts.
    """
    try:
        stats = _orchestrator.get_platform_stats()

        # Add per-agent breakdown
        db = SessionLocal()
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            general_count = db.execute(
                text("""
                    SELECT COUNT(DISTINCT uc.user_id) FROM user_configs uc
                    WHERE COALESCE(uc.industry, 'general') = 'general'
                """),
            ).scalar() or 0

            hr_count = db.execute(
                text("""
                    SELECT COUNT(DISTINCT user_id) FROM user_configs
                    WHERE industry = 'hr'
                """),
            ).scalar() or 0
        finally:
            db.close()

        stats["agents_running"] = {
            "general": general_count,
            "hr": hr_count,
        }

        return _ok(stats)

    except Exception as exc:
        logger.exception("Failed to get platform stats")
        return _err(f"Failed to get stats: {exc}")


# ============================================================================
# POST /platform/users/{user_id}/setup
# ============================================================================


@router.post("/users/{user_id}/setup", tags=["Platform"])
async def setup_user(
    user_id: str,
    body: dict = Body(...),
):
    """Set up or update a user's industry and subscription tier.

    Body:
        {
            "industry": "hr",   // or "general"
            "tier": "tier2"     // tier1, tier2, or tier3
        }
    """
    industry = body.get("industry", "general")
    tier = body.get("tier", "tier2")

    # Validate tier
    valid_tiers = ("tier1", "tier2", "tier3")
    if tier not in valid_tiers:
        return _err(f"Invalid tier '{tier}'. Must be one of: {valid_tiers}")

    db = SessionLocal()
    try:
        # Upsert user_configs with industry
        db.execute(
            text("""
                INSERT INTO user_configs (user_id, config_json, industry, created_at, updated_at)
                VALUES (:uid, '{}', :industry, NOW(), NOW())
                ON CONFLICT (user_id) DO UPDATE
                    SET industry = :industry,
                        updated_at = NOW()
            """),
            {"uid": user_id, "industry": industry},
        )

        # Upsert user_subscriptions with tier
        db.execute(
            text("""
                INSERT INTO user_subscriptions (user_id, status, plan, tier, created_at, updated_at)
                VALUES (:uid, 'active', :tier, :tier, NOW(), NOW())
                ON CONFLICT (user_id) DO UPDATE
                    SET tier = :tier,
                        plan = :tier,
                        updated_at = NOW()
            """),
            {"uid": user_id, "tier": tier},
        )

        db.commit()
        logger.info("User %s set up: industry=%s, tier=%s", user_id, industry, tier)

        return _ok({
            "success": True,
            "user_id": user_id,
            "industry": industry,
            "tier": tier,
        })

    except Exception as exc:
        db.rollback()
        logger.exception("Failed to set up user %s", user_id)
        return _err(f"Failed to set up user: {exc}")
    finally:
        db.close()


# ============================================================================
# GET /platform/users/{user_id}/agent-info
# ============================================================================


@router.get("/users/{user_id}/agent-info", tags=["Platform"])
async def get_agent_info(user_id: str):
    """Get a user's agent routing information.

    Returns the assigned agent, tier, features, and daily usage.
    """
    try:
        tier = _gates.get_user_tier(user_id)
        industry = _user_router.get_user_industry(user_id)

        # Get agent name
        agent_class = _orchestrator.registry.get_agent(industry)
        if agent_class is None:
            agent_class = _orchestrator.registry.get_agent("general")
            industry = "general"
        agent_name = agent_class.__name__ if agent_class else "Unknown"

        # Features
        tier_config = _gates.TIER_FEATURES.get(tier, {})
        features = tier_config.get("features", [])
        daily_limit = tier_config.get("max_emails_per_day", 200)

        # Usage today
        emails_today = _gates.get_usage_today(user_id)

        return _ok({
            "user_id": user_id,
            "industry": industry,
            "tier": tier,
            "agent_name": agent_name,
            "features_available": features,
            "emails_processed_today": emails_today,
            "daily_limit": daily_limit,
        })

    except Exception as exc:
        logger.exception("Failed to get agent info for user %s", user_id)
        return _err(f"Failed to get agent info: {exc}")
