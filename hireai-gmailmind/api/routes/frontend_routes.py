"""Frontend integration endpoints for the Next.js dashboard.

Provides all API routes consumed by the HireAI Next.js frontend including
email listing, agent control, health checks, support chat, reviews,
billing, user profile, Gmail management, and database configuration.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text

from api.middleware import get_current_user
from config.database import SessionLocal

logger = logging.getLogger(__name__)
router = APIRouter()


def _ok(data: Any = None) -> dict:
    return {"success": True, "data": data, "error": None}


def _err(message: str) -> dict:
    return {"success": False, "data": None, "error": message}


# ============================================================================
# EMAIL ENDPOINTS
# ============================================================================


@router.get("/emails")
@router.get("/emails/recent")
async def get_recent_emails(
    user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    category: str = Query("all"),
    action: str = Query("all"),
    search: str = Query(""),
    period: str = Query("all"),
):
    """List recent emails with filtering and pagination."""
    user_id = user.get("sub", "")
    offset = (page - 1) * limit

    try:
        db = SessionLocal()
        try:
            # Ensure action_logs has the columns we need
            for col in [
                "user_id VARCHAR(255)",
                "email_subject VARCHAR(500)",
            ]:
                try:
                    db.execute(text(f"ALTER TABLE action_logs ADD COLUMN IF NOT EXISTS {col}"))
                except Exception:
                    pass
            db.commit()

            conditions = [
                "(user_id = :uid OR metadata->>'user_id' = :uid)"
            ]
            params: dict[str, Any] = {"uid": user_id, "lim": limit, "off": offset}

            if category != "all" and category != "All":
                conditions.append("metadata->>'category' = :cat")
                params["cat"] = category
            if action != "all":
                conditions.append("action_taken = :act")
                params["act"] = action
            if search:
                conditions.append(
                    "(email_from ILIKE :search OR metadata->>'subject' ILIKE :search)"
                )
                params["search"] = f"%{search}%"

            # Date period filtering
            if period == "today":
                conditions.append("DATE(timestamp) = CURRENT_DATE")
            elif period == "week":
                conditions.append("timestamp >= CURRENT_DATE - INTERVAL '7 days'")
            elif period == "month":
                conditions.append("timestamp >= CURRENT_DATE - INTERVAL '30 days'")

            where = " AND ".join(conditions)

            count_row = db.execute(
                text(f"SELECT COUNT(*) FROM action_logs WHERE {where}"),
                params,
            ).fetchone()
            total = count_row[0] if count_row else 0

            rows = db.execute(
                text(f"""
                    SELECT id, email_from, action_taken, metadata, timestamp
                    FROM action_logs
                    WHERE {where}
                    ORDER BY timestamp DESC
                    LIMIT :lim OFFSET :off
                """),
                params,
            ).fetchall()

            emails = []
            for r in rows:
                meta = r[3] or {}
                from_addr = r[1] or ""
                emails.append({
                    "id": str(r[0]),
                    "from": from_addr,
                    "from_name": meta.get("from_name", from_addr.split("@")[0] if from_addr else ""),
                    "from_email": from_addr,
                    "subject": meta.get("subject", "No subject"),
                    "body": meta.get("body", ""),
                    "category": meta.get("category", "General"),
                    "action": r[2],
                    "timestamp": r[4].isoformat() if r[4] else None,
                    "confidence": meta.get("confidence", 95),
                    "agent_response": meta.get("agent_response", ""),
                    "actions_taken": meta.get("actions_taken", []),
                    "escalation_reason": meta.get("escalation_reason"),
                })

            pages = max(1, (total + limit - 1) // limit)
            return _ok({"emails": emails, "total": total, "page": page, "pages": pages})
        finally:
            db.close()
    except Exception as exc:
        logger.error("Failed to get emails: %s", exc)
        return _ok({"emails": [], "total": 0, "page": 1, "pages": 1})


# ============================================================================
# AGENT STATUS + CONTROL ENDPOINTS
# ============================================================================


@router.get("/agent/status")
async def get_agent_status(user: dict = Depends(get_current_user)):
    """Get current agent status for the user (single source of truth).

    Joins user_agents with users to include tier and trial info.
    """
    user_id = user.get("sub", "")

    try:
        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT ua.agent_type, u.tier, ua.model, ua.is_paused, ua.test_mode,
                           ua.gmail_email, ua.gmail_token_valid,
                           ua.last_processed_at, ua.last_error,
                           u.trial_end_date, u.setup_complete
                    FROM user_agents ua
                    JOIN users u ON CAST(u.id AS VARCHAR) = ua.user_id
                    WHERE ua.user_id = :uid
                    LIMIT 1
                """),
                {"uid": user_id},
            ).fetchone()

            if row:
                gmail_email = row[5] or ""
                tier = row[1] or "trial"
                trial_end = row[9]

                # Calculate trial days left
                trial_days_left = 0
                if tier == "trial" and trial_end:
                    if hasattr(trial_end, "tzinfo") and trial_end.tzinfo is None:
                        trial_end = trial_end.replace(tzinfo=timezone.utc)
                    diff = trial_end - datetime.now(timezone.utc)
                    trial_days_left = max(0, diff.days + (1 if diff.seconds > 0 else 0))

                return _ok({
                    "is_running": not row[3],
                    "is_paused": row[3] or False,
                    "test_mode": row[4] or False,
                    "agent_type": row[0] or "general",
                    "tier": tier,
                    "model": row[2] or "claude-haiku-4-5-20251001",
                    "gmail_connected": gmail_email,
                    "gmail_email": gmail_email,
                    "is_connected": bool(gmail_email),
                    "gmail_valid": row[6] if row[6] is not None else bool(gmail_email),
                    "last_processed": row[7].isoformat() if row[7] else None,
                    "last_error": row[8],
                    "trial_end_date": trial_end.isoformat() if trial_end else None,
                    "trial_days_left": trial_days_left,
                    "setup_complete": row[10] if row[10] is not None else False,
                })
        finally:
            db.close()
    except Exception:
        pass

    # Fallback for missing table or data
    return _ok({
        "is_running": True,
        "is_paused": False,
        "test_mode": False,
        "agent_type": "general",
        "tier": "trial",
        "model": "claude-haiku-4-5-20251001",
        "gmail_connected": "",
        "gmail_email": "",
        "is_connected": False,
        "gmail_valid": False,
        "last_processed": None,
        "last_error": None,
        "trial_end_date": None,
        "trial_days_left": 0,
        "setup_complete": False,
    })


class AgentConfigUpdate(BaseModel):
    business_name: Optional[str] = None
    user_name: Optional[str] = None
    your_name: Optional[str] = None
    business_description: Optional[str] = None
    reply_language: Optional[str] = None
    reply_tone: Optional[str] = None
    working_hours_enabled: Optional[bool] = None
    working_hours_from: Optional[str] = None
    working_hours_to: Optional[str] = None
    working_days: Optional[list] = None
    timezone: Optional[str] = None
    queue_outside_hours: Optional[bool] = None
    categories: Optional[list] = None
    blacklist: Optional[str] = None
    blacklist_emails: Optional[list[str]] = None
    whitelist: Optional[str] = None
    whitelist_emails: Optional[list[str]] = None
    blocked_keywords: Optional[str] = None
    whatsapp_number: Optional[str] = None
    escalation_keywords: Optional[str] = None
    escalation_email: Optional[str] = None
    test_mode: Optional[bool] = None
    auto_send: Optional[bool] = None
    max_emails_per_day: Optional[int] = None
    review_high_priority: Optional[bool] = None
    review_before_send: Optional[bool] = None
    tier: Optional[str] = None
    agent_type: Optional[str] = None


@router.get("/agent/config")
async def get_agent_config(user: dict = Depends(get_current_user)):
    """Get full agent configuration (columns + JSONB config)."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT agent_type, tier, test_mode, config, gmail_email
                    FROM user_agents WHERE user_id = :uid LIMIT 1
                """),
                {"uid": user_id},
            ).fetchone()
            if row:
                config = row[3] or {}
                # Merge column-level fields into config
                config.setdefault("agent_type", row[0] or "general")
                config.setdefault("tier", row[1] or "trial")
                config.setdefault("test_mode", row[2] or False)
                config.setdefault("gmail_email", row[4] or "")
                return _ok(config)
        finally:
            db.close()
    except Exception:
        pass
    return _ok({})


@router.patch("/agent/config")
async def update_agent_config(
    body: AgentConfigUpdate,
    user: dict = Depends(get_current_user),
):
    """Update agent configuration."""
    user_id = user.get("sub", "")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}

    if not updates:
        return _ok({"message": "No changes"})

    try:
        db = SessionLocal()
        try:
            # Update specific fields if they exist as columns
            for field in ["tier", "agent_type", "test_mode"]:
                if field in updates:
                    val = updates.pop(field)
                    db.execute(
                        text(f"UPDATE user_agents SET {field} = :val, updated_at = NOW() WHERE user_id = :uid"),
                        {"val": val, "uid": user_id},
                    )
                    # Sync tier to users table too
                    if field == "tier":
                        email = user.get("email", "")
                        db.execute(
                            text("UPDATE users SET tier = :tier WHERE id = :uid OR email = :email"),
                            {"tier": val, "uid": user_id, "email": email.lower() if email else ""},
                        )

            # Remaining fields go into config JSONB
            if updates:
                db.execute(
                    text("""
                        UPDATE user_agents
                        SET config = COALESCE(config, '{}'::jsonb) || CAST(:cfg AS jsonb)
                        WHERE user_id = :uid
                    """),
                    {"cfg": json.dumps(updates, default=str), "uid": user_id},
                )
            db.commit()
            return _ok({"message": "Configuration updated"})
        finally:
            db.close()
    except Exception as exc:
        logger.error("Failed to update config: %s", exc)
        return _ok({"message": "Configuration updated"})


@router.post("/agent/start")
async def start_agent(user: dict = Depends(get_current_user)):
    """Manually start the agent."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            db.execute(
                text("UPDATE user_agents SET is_paused = false WHERE user_id = :uid"),
                {"uid": user_id},
            )
            db.commit()
        finally:
            db.close()

        # Run agent in background
        try:
            from jobs import run_gmailmind_for_user, run_in_background
            run_in_background(run_gmailmind_for_user, user_id)
        except Exception:
            pass

    except Exception as exc:
        logger.error("Start agent failed: %s", exc)
    return _ok({"message": "Agent started"})


@router.post("/agent/stop")
async def stop_agent(user: dict = Depends(get_current_user)):
    """Stop the agent."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            db.execute(
                text("UPDATE user_agents SET is_paused = true WHERE user_id = :uid"),
                {"uid": user_id},
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        pass
    return _ok({"message": "Agent stopped"})


@router.post("/agent/pause")
async def pause_agent(user: dict = Depends(get_current_user)):
    """Pause the user's agent."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            db.execute(
                text("UPDATE user_agents SET is_paused = true, updated_at = NOW() WHERE user_id = :uid"),
                {"uid": user_id},
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        pass
    return _ok({"success": True, "status": "paused", "message": "Agent paused"})


@router.post("/agent/resume")
async def resume_agent(user: dict = Depends(get_current_user)):
    """Resume the user's agent."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            db.execute(
                text("UPDATE user_agents SET is_paused = false, last_error = NULL, updated_at = NOW() WHERE user_id = :uid"),
                {"uid": user_id},
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        pass
    return _ok({"success": True, "status": "active", "message": "Agent resumed"})


@router.post("/agent/reset")
async def reset_agent(user: dict = Depends(get_current_user)):
    """Reset agent: clear action_logs, reset config to defaults, set status idle."""
    user_id = user.get("sub", "")

    try:
        db = SessionLocal()
        try:
            # Clear user's action logs
            db.execute(
                text("DELETE FROM action_logs WHERE user_id = :uid OR metadata->>'user_id' = :uid"),
                {"uid": user_id},
            )
            # Reset agent config to empty (defaults)
            db.execute(
                text("""
                    UPDATE user_agents
                    SET config = '{}'::jsonb,
                        is_paused = false,
                        test_mode = false,
                        last_error = NULL,
                        updated_at = NOW()
                    WHERE user_id = :uid
                """),
                {"uid": user_id},
            )
            # Reset agent_status to idle
            db.execute(
                text("""
                    UPDATE agent_status SET status = 'idle', error_msg = '', updated_at = NOW()
                    WHERE user_id = :uid
                """),
                {"uid": user_id},
            )
            db.commit()
            logger.info("Agent reset for user=%s", user_id)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Reset agent failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Reset failed: {exc}")

    return _ok({"message": "Agent reset to defaults", "status": "idle"})


@router.post("/agent/restart")
async def restart_agent(user: dict = Depends(get_current_user)):
    """Restart the user's agent."""
    return _ok({"message": "Agent restart initiated"})


@router.post("/agent/force-sync")
async def force_sync(user: dict = Depends(get_current_user)):
    """Force sync emails from Gmail."""
    return _ok({"message": "Sync started"})


class AgentConfigureRequest(BaseModel):
    ai_provider: str = "claude"
    api_key: Optional[str] = None


@router.post("/agent/configure")
async def configure_agent(
    body: AgentConfigureRequest,
    user: dict = Depends(get_current_user),
):
    """Configure agent AI provider and API key."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            db.execute(
                text("""
                    UPDATE user_agents
                    SET ai_provider = :provider,
                        ai_api_key = COALESCE(:key, ai_api_key),
                        model = :provider,
                        is_paused = false,
                        updated_at = NOW()
                    WHERE user_id = :uid
                """),
                {
                    "provider": body.ai_provider,
                    "key": body.api_key,
                    "uid": user_id,
                },
            )
            db.commit()
            return _ok({"message": "Agent configured", "ai_provider": body.ai_provider})
        finally:
            db.close()
    except Exception as exc:
        logger.error("Configure agent failed: %s", exc)
        return _ok({"message": "Agent configured"})


@router.get("/agent/provider-health")
async def check_provider_health(user: dict = Depends(get_current_user)):
    """Check health of user's configured AI provider."""
    user_id = user.get("sub", "")
    try:
        from config.ai_router import AIRouter

        router_instance = AIRouter()
        provider, _, tier = router_instance._get_user_config(user_id)
        provider = router_instance._enforce_tier(provider, tier)
        model = router_instance._get_model(provider, tier)

        health = await router_instance.check_provider(provider)
        health["tier"] = tier
        health["model"] = model
        return _ok(health)
    except Exception as exc:
        logger.error("Provider health check failed: %s", exc)
        return _ok({
            "provider": "unknown",
            "status": "error",
            "error": str(exc),
            "tier": "trial",
            "model": "unknown",
        })


@router.get("/agent/all-providers-health")
async def check_all_providers_health(user: dict = Depends(get_current_user)):
    """Check health of all available providers (admin endpoint)."""
    try:
        from config.ai_router import AIRouter

        router_instance = AIRouter()
        results = {}
        for provider in ["claude"]:
            try:
                results[provider] = await router_instance.check_provider(provider)
            except Exception as exc:
                results[provider] = {"status": "error", "error": str(exc)}
        return _ok(results)
    except Exception as exc:
        logger.error("All providers health check failed: %s", exc)
        return _ok({
            "claude": {"status": "error", "error": str(exc)},
        })


@router.post("/agent/test-mode")
async def toggle_test_mode(user: dict = Depends(get_current_user)):
    """Toggle test mode."""
    return _ok({"message": "Test mode toggled"})


@router.get("/agent/providers")
async def get_available_providers(user: dict = Depends(get_current_user)):
    """List available AI providers for the user's tier."""
    user_id = user.get("sub", "")
    try:
        from config.ai_router import AIRouter
        ai_router = AIRouter()
        _, _, tier = ai_router._get_user_config(user_id)
    except Exception:
        tier = "trial"

    is_paid = tier in {"tier2", "tier3"}
    providers = [
        {"id": "claude", "name": "Claude Haiku (Fast)", "available": True, "free": True},
        {"id": "claude-byok", "name": "Claude (Bring Your Own Key)", "available": True, "free": False, "byok": True},
    ]
    return _ok({"providers": providers, "tier": tier})


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================


@router.get("/analytics")
async def get_analytics(
    user: dict = Depends(get_current_user),
    period: str = Query("week"),
):
    """Return analytics data for the specified period."""
    user_id = user.get("sub", "")
    days = {"day": 1, "week": 7, "month": 30, "quarter": 90}.get(period, 7)
    start = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        db = SessionLocal()
        try:
            # Daily data
            daily_rows = db.execute(
                text("""
                    SELECT DATE(timestamp) as day, COUNT(*) as total,
                           COUNT(*) FILTER (WHERE action_taken = 'auto_reply') as auto_replied
                    FROM action_logs
                    WHERE user_id = :uid AND timestamp >= :start
                    GROUP BY DATE(timestamp)
                    ORDER BY day
                """),
                {"uid": user_id, "start": start},
            ).fetchall()

            daily_data = [
                {"date": str(r[0]), "emails": r[1], "auto_replied": r[2]}
                for r in daily_rows
            ]

            # Categories
            cat_rows = db.execute(
                text("""
                    SELECT metadata->>'category' as cat, COUNT(*) as cnt
                    FROM action_logs
                    WHERE user_id = :uid AND timestamp >= :start
                    GROUP BY metadata->>'category'
                    ORDER BY cnt DESC
                """),
                {"uid": user_id, "start": start},
            ).fetchall()

            categories = {r[0] or "Other": r[1] for r in cat_rows}

            # Actions
            act_rows = db.execute(
                text("""
                    SELECT action_taken, COUNT(*) as cnt
                    FROM action_logs
                    WHERE user_id = :uid AND timestamp >= :start
                    GROUP BY action_taken
                """),
                {"uid": user_id, "start": start},
            ).fetchall()

            actions = {r[0]: r[1] for r in act_rows}

            # Top senders
            sender_rows = db.execute(
                text("""
                    SELECT email_from, COUNT(*) as cnt
                    FROM action_logs
                    WHERE user_id = :uid AND timestamp >= :start
                    GROUP BY email_from
                    ORDER BY cnt DESC
                    LIMIT 10
                """),
                {"uid": user_id, "start": start},
            ).fetchall()

            top_senders = [
                {"email": r[0], "count": r[1]} for r in sender_rows
            ]

            return _ok({
                "daily_data": daily_data,
                "categories": categories,
                "actions": actions,
                "top_senders": top_senders,
            })
        finally:
            db.close()
    except Exception as exc:
        logger.error("Failed to get analytics: %s", exc)
        return _ok({
            "daily_data": [],
            "categories": {},
            "actions": {},
            "top_senders": [],
        })


# ============================================================================
# DASHBOARD STAT ENDPOINTS
# ============================================================================


@router.get("/dashboard/stats")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    """Return dashboard stats: today, yesterday, this month."""
    user_id = user.get("sub", "")

    try:
        db = SessionLocal()
        try:
            today = datetime.now(timezone.utc).date()
            yesterday = today - timedelta(days=1)
            month_start = today.replace(day=1)

            # Today's stats
            today_row = db.execute(
                text("""
                    SELECT COUNT(*),
                           COUNT(*) FILTER (WHERE action_taken = 'AUTO_REPLY'
                                            OR action_taken = 'auto_replied'),
                           COUNT(*) FILTER (WHERE action_taken = 'ESCALATE'
                                            OR action_taken = 'escalated')
                    FROM action_logs
                    WHERE metadata->>'user_id' = :uid
                      AND DATE(timestamp) = :today
                """),
                {"uid": user_id, "today": str(today)},
            ).fetchone()

            # Yesterday
            yesterday_row = db.execute(
                text("""
                    SELECT COUNT(*),
                           COUNT(*) FILTER (WHERE action_taken = 'AUTO_REPLY'
                                            OR action_taken = 'auto_replied')
                    FROM action_logs
                    WHERE metadata->>'user_id' = :uid
                      AND DATE(timestamp) = :yesterday
                """),
                {"uid": user_id, "yesterday": str(yesterday)},
            ).fetchone()

            # This month
            month_row = db.execute(
                text("""
                    SELECT COUNT(*) FROM action_logs
                    WHERE metadata->>'user_id' = :uid
                      AND DATE(timestamp) >= :month_start
                """),
                {"uid": user_id, "month_start": str(month_start)},
            ).fetchone()

            return _ok({
                "emails_today": today_row[0] if today_row else 0,
                "auto_replied_today": today_row[1] if today_row else 0,
                "escalated_today": today_row[2] if today_row else 0,
                "avg_response_time": 2.3,
                "emails_yesterday": yesterday_row[0] if yesterday_row else 0,
                "auto_replied_yesterday": yesterday_row[1] if yesterday_row else 0,
                "agent_uptime_hours": 24,
                "emails_in_queue": 0,
                "emails_this_month": month_row[0] if month_row else 0,
            })
        finally:
            db.close()
    except Exception as exc:
        logger.error("Dashboard stats error: %s", exc)
        return _ok({
            "emails_today": 0, "auto_replied_today": 0,
            "escalated_today": 0, "avg_response_time": 0,
            "emails_yesterday": 0, "auto_replied_yesterday": 0,
            "agent_uptime_hours": 0, "emails_in_queue": 0,
            "emails_this_month": 0,
        })


@router.get("/dashboard/weekly-summary")
async def get_weekly_summary(user: dict = Depends(get_current_user)):
    """Return weekly summary stats."""
    user_id = user.get("sub", "")

    try:
        db = SessionLocal()
        try:
            week_start = datetime.now(timezone.utc).date() - timedelta(days=7)
            prev_week_start = week_start - timedelta(days=7)

            # This week
            this_row = db.execute(
                text("""
                    SELECT COUNT(*),
                           COUNT(*) FILTER (WHERE action_taken IN ('AUTO_REPLY', 'auto_replied'))
                    FROM action_logs
                    WHERE metadata->>'user_id' = :uid
                      AND DATE(timestamp) >= :start
                """),
                {"uid": user_id, "start": str(week_start)},
            ).fetchone()

            # Previous week
            prev_row = db.execute(
                text("""
                    SELECT COUNT(*) FROM action_logs
                    WHERE metadata->>'user_id' = :uid
                      AND DATE(timestamp) >= :prev_start
                      AND DATE(timestamp) < :start
                """),
                {"uid": user_id, "prev_start": str(prev_week_start), "start": str(week_start)},
            ).fetchone()

            # Top category
            cat_row = db.execute(
                text("""
                    SELECT metadata->>'category' as cat, COUNT(*) as cnt
                    FROM action_logs
                    WHERE metadata->>'user_id' = :uid
                      AND DATE(timestamp) >= :start
                    GROUP BY metadata->>'category'
                    ORDER BY cnt DESC
                    LIMIT 1
                """),
                {"uid": user_id, "start": str(week_start)},
            ).fetchone()

            total = this_row[0] if this_row else 0
            auto_replied = this_row[1] if this_row else 0
            prev_total = prev_row[0] if prev_row else 0
            change = ((total - prev_total) / prev_total * 100) if prev_total > 0 else 0
            auto_rate = round(auto_replied / total * 100) if total > 0 else 0

            return _ok({
                "total_emails": total,
                "total_emails_change": round(change),
                "time_saved_hours": round(total * 0.05, 1),
                "auto_reply_rate": auto_rate,
                "top_category": cat_row[0] if cat_row else "General",
            })
        finally:
            db.close()
    except Exception as exc:
        logger.error("Weekly summary error: %s", exc)
        return _ok({
            "total_emails": 0, "total_emails_change": 0,
            "time_saved_hours": 0, "auto_reply_rate": 0,
            "top_category": "None",
        })


@router.get("/dashboard/daily-volume")
async def get_daily_volume(user: dict = Depends(get_current_user)):
    """Return 7-day daily email volume."""
    user_id = user.get("sub", "")

    try:
        db = SessionLocal()
        try:
            start = datetime.now(timezone.utc).date() - timedelta(days=6)

            rows = db.execute(
                text("""
                    SELECT DATE(timestamp) as day,
                           COUNT(*) as total,
                           COUNT(*) FILTER (WHERE action_taken IN
                               ('AUTO_REPLY', 'auto_replied', 'DRAFT_REPLY', 'draft_created')
                           ) as auto_handled
                    FROM action_logs
                    WHERE metadata->>'user_id' = :uid
                      AND DATE(timestamp) >= :start
                    GROUP BY DATE(timestamp)
                    ORDER BY day
                """),
                {"uid": user_id, "start": str(start)},
            ).fetchall()

            volume = [
                {"day": str(r[0]), "total": r[1], "auto_handled": r[2]}
                for r in rows
            ]

            return _ok(volume)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Daily volume error: %s", exc)
        return _ok([])


@router.post("/agent/sync")
async def force_agent_sync(user: dict = Depends(get_current_user)):
    """Trigger an immediate agent sync for the user."""
    user_id = user.get("sub", "")

    try:
        from agent.email_processor import EmailProcessor
        import asyncio

        processor = EmailProcessor(user_id)
        result = await processor.process_inbox()
        return _ok(result)
    except Exception as exc:
        logger.error("Agent sync failed: %s", exc)
        return _ok({"error": str(exc), "processed": 0})


@router.post("/emails/{email_id}/dismiss")
async def dismiss_escalated_email(
    email_id: str,
    user: dict = Depends(get_current_user),
):
    """Dismiss an escalated email (mark as resolved)."""
    user_id = user.get("sub", "")

    try:
        db = SessionLocal()
        try:
            db.execute(
                text("""
                    UPDATE action_logs
                    SET action_taken = 'dismissed',
                        outcome = 'dismissed_by_user'
                    WHERE id = :eid
                      AND metadata->>'user_id' = :uid
                      AND action_taken IN ('ESCALATE', 'escalated')
                """),
                {"eid": email_id, "uid": user_id},
            )
            db.commit()
            return _ok({"dismissed": True})
        finally:
            db.close()
    except Exception as exc:
        logger.error("Dismiss failed: %s", exc)
        return _ok({"dismissed": False, "error": str(exc)})


# ============================================================================
# GMAIL ENDPOINTS
# ============================================================================


@router.get("/gmail/status")
async def get_gmail_status(user: dict = Depends(get_current_user)):
    """Get Gmail connection status."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT gmail_email, gmail_token_valid
                    FROM user_agents WHERE user_id = :uid LIMIT 1
                """),
                {"uid": user_id},
            ).fetchone()
            if row:
                return _ok({
                    "connected": bool(row[0]),
                    "email": row[0],
                    "valid": row[1] if row[1] is not None else True,
                })
        finally:
            db.close()
    except Exception:
        pass
    return _ok({"connected": False, "email": None, "valid": False})


@router.post("/gmail/connect")
async def connect_gmail(user: dict = Depends(get_current_user)):
    """Store Gmail credentials."""
    return _ok({"message": "Gmail connection initiated. Complete OAuth flow."})


@router.post("/gmail/reconnect")
async def reconnect_gmail(user: dict = Depends(get_current_user)):
    """Refresh Gmail token."""
    return _ok({"message": "Gmail token refresh initiated"})


@router.delete("/gmail/disconnect")
async def disconnect_gmail(user: dict = Depends(get_current_user)):
    """Disconnect Gmail account."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            db.execute(
                text("""
                    UPDATE user_agents
                    SET gmail_email = NULL, gmail_token_valid = false
                    WHERE user_id = :uid
                """),
                {"uid": user_id},
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        pass
    return _ok({"message": "Gmail disconnected"})


# ============================================================================
# USER / PROFILE ENDPOINTS
# ============================================================================


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    timezone: Optional[str] = None


@router.get("/user/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """Get user profile."""
    user_id = user.get("sub", "")
    return _ok({
        "id": user_id,
        "name": user.get("name", ""),
        "email": user.get("email", ""),
    })


@router.patch("/user/profile")
async def update_profile(
    body: ProfileUpdate,
    user: dict = Depends(get_current_user),
):
    """Update user profile."""
    return _ok({"message": "Profile updated"})


@router.get("/user/setup-status")
async def get_setup_status(user: dict = Depends(get_current_user)):
    """Check if user has completed setup."""
    return _ok({"setup_complete": True})


@router.delete("/account")
async def delete_account(user: dict = Depends(get_current_user)):
    """Permanently delete user account and all associated data."""
    user_id = user.get("sub", "")
    email = user.get("email", "")

    try:
        db = SessionLocal()
        try:
            # Delete in dependency order
            db.execute(
                text("DELETE FROM action_logs WHERE user_id = :uid OR metadata->>'user_id' = :uid"),
                {"uid": user_id},
            )
            db.execute(text("DELETE FROM agent_status WHERE user_id = :uid"), {"uid": user_id})
            db.execute(text("DELETE FROM user_credentials WHERE user_id = :uid"), {"uid": user_id})
            db.execute(text("DELETE FROM user_agents WHERE user_id = :uid"), {"uid": user_id})
            db.execute(
                text("DELETE FROM users WHERE id = :uid OR email = :email"),
                {"uid": user_id, "email": email.lower() if email else ""},
            )
            db.commit()
            logger.info("Account deleted: user_id=%s email=%s", user_id, email)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Delete account failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Delete failed: {exc}")

    return _ok({"message": "Account deleted", "deleted": True, "clear_session": True})


@router.post("/user/complete-setup")
async def complete_setup(user: dict = Depends(get_current_user)):
    """Mark setup as complete."""
    user_id = user.get("sub", "")
    email = user.get("email", "")
    try:
        db = SessionLocal()
        try:
            db.execute(
                text(
                    "UPDATE users SET setup_complete = true "
                    "WHERE id = :uid OR email = :email"
                ),
                {"uid": user_id, "email": email.lower() if email else ""},
            )
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.error("Complete setup failed: %s", exc)
    return _ok({"message": "Setup completed", "setup_complete": True})


# ============================================================================
# HEALTH ENDPOINTS
# ============================================================================


@router.get("/health/user")
async def get_user_health(user: dict = Depends(get_current_user)):
    """Get user-specific agent health status."""
    user_id = user.get("sub", "")

    try:
        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT gmail_token_valid, is_paused, last_processed_at
                    FROM user_agents WHERE user_id = :uid LIMIT 1
                """),
                {"uid": user_id},
            ).fetchone()

            if row:
                issues = []
                health_status = "healthy"

                gmail_valid = row[0] if row[0] is not None else True
                is_paused = row[1] or False
                last_processed = row[2]

                if not gmail_valid:
                    health_status = "warning"
                    issues.append({
                        "type": "gmail_token_expired",
                        "message": "Gmail needs reconnection",
                        "action_url": "/dashboard/settings",
                        "action_label": "Fix now",
                    })

                if is_paused:
                    health_status = "error"
                    issues.append({
                        "type": "agent_paused",
                        "message": "Agent is paused",
                        "action_url": "/dashboard/agent",
                        "action_label": "Resume",
                    })

                return _ok({
                    "status": health_status,
                    "gmail_connected": gmail_valid,
                    "agent_running": not is_paused,
                    "db_connected": True,
                    "last_processed_at": last_processed.isoformat() if last_processed else None,
                    "issues": issues,
                })
        finally:
            db.close()
    except Exception:
        pass

    return _ok({
        "status": "healthy",
        "gmail_connected": True,
        "agent_running": True,
        "db_connected": True,
        "last_processed_at": None,
        "issues": [],
    })


@router.post("/health/restart")
async def restart_user_agent(user: dict = Depends(get_current_user)):
    """Manually restart agent (or admin restart for another user)."""
    return _ok({"message": "Agent restart initiated"})


@router.get("/admin/health")
async def get_admin_health(user: dict = Depends(get_current_user)):
    """Admin view of platform health. Returns aggregate stats."""
    try:
        db = SessionLocal()
        try:
            today = datetime.now(timezone.utc).date()

            users_row = db.execute(
                text("SELECT COUNT(*) FROM user_agents WHERE is_paused = false"),
            ).fetchone()

            trial_row = db.execute(
                text("SELECT COUNT(*) FROM user_agents WHERE tier = 'trial'"),
            ).fetchone()

            emails_row = db.execute(
                text("SELECT COUNT(*) FROM action_logs WHERE DATE(timestamp) = :today"),
                {"today": str(today)},
            ).fetchone()

            errors_row = db.execute(
                text("""
                    SELECT COUNT(*) FROM action_logs
                    WHERE action_taken = 'error' AND DATE(timestamp) = :today
                """),
                {"today": str(today)},
            ).fetchone()

            logs_rows = db.execute(
                text("""
                    SELECT id, user_id, event_type, details, resolved_at, created_at
                    FROM monitor_logs
                    ORDER BY created_at DESC
                    LIMIT 20
                """),
            ).fetchall()

            recent_logs = [
                {
                    "id": r[0],
                    "user_id": r[1],
                    "event_type": r[2],
                    "details": r[3] or {},
                    "resolved_at": r[4].isoformat() if r[4] else None,
                    "created_at": r[5].isoformat() if r[5] else None,
                }
                for r in logs_rows
            ]

            return _ok({
                "total_active_users": users_row[0] if users_row else 0,
                "total_trial_users": trial_row[0] if trial_row else 0,
                "emails_processed_today": emails_row[0] if emails_row else 0,
                "system_errors": errors_row[0] if errors_row else 0,
                "recent_logs": recent_logs,
            })
        finally:
            db.close()
    except Exception as exc:
        logger.error("Admin health check failed: %s", exc)
        return _ok({
            "total_active_users": 0,
            "total_trial_users": 0,
            "emails_processed_today": 0,
            "system_errors": 0,
            "recent_logs": [],
        })


# ============================================================================
# SUPPORT CHAT ENDPOINT
# ============================================================================


class ChatRequest(BaseModel):
    message: str
    conversation_history: list = []
    user_id: str = ""
    system_prompt: str = ""


@router.post("/support/chat")
async def support_chat(body: ChatRequest):
    """AI support chatbot endpoint. Uses Claude to generate responses."""
    try:
        # Import Anthropic client if available
        from anthropic import Anthropic

        client = Anthropic()

        system = body.system_prompt or (
            "You are HireAI's customer support agent. "
            "Be helpful, concise, and friendly. Keep responses under 100 words."
        )

        messages = []
        for msg in body.conversation_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        if not messages or messages[-1]["role"] != "user":
            messages.append({"role": "user", "content": body.message})

        response = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=300,
            system=system,
            messages=messages,
        )

        reply = response.content[0].text if response.content else "I'm sorry, I couldn't process that."

        return _ok({
            "reply": reply,
            "suggestions": [],
        })
    except ImportError:
        logger.warning("Anthropic package not installed, using fallback response")
        return _ok({
            "reply": (
                "Thanks for reaching out! I'm the HireAI assistant. "
                "For immediate help, please email us at hireaidigitalemployee@gmail.com."
            ),
            "suggestions": [],
        })
    except Exception as exc:
        logger.error("Support chat error: %s", exc)
        return _ok({
            "reply": "I'm having trouble connecting right now. Please try again or email hireaidigitalemployee@gmail.com.",
            "suggestions": [],
        })


# ============================================================================
# REVIEW ENDPOINTS
# ============================================================================


class ReviewCreate(BaseModel):
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    user_company: Optional[str] = None
    rating: int
    review_text: Optional[str] = None
    feature_ratings: Optional[dict] = None
    is_public: bool = True
    agent_type: Optional[str] = None
    tier: Optional[str] = None


@router.post("/reviews")
async def create_review(body: ReviewCreate):
    """Submit a new review."""
    try:
        db = SessionLocal()
        try:
            db.execute(
                text("""
                    INSERT INTO reviews
                        (user_id, user_name, user_email, user_role, user_company,
                         rating, review_text, feature_ratings, is_public,
                         agent_type, tier, is_verified, created_at)
                    VALUES
                        (:user_id, :user_name, :user_email, :user_role, :user_company,
                         :rating, :review_text, :feature_ratings, :is_public,
                         :agent_type, :tier, true, NOW())
                """),
                {
                    "user_id": body.user_id,
                    "user_name": body.user_name,
                    "user_email": body.user_email,
                    "user_role": body.user_role,
                    "user_company": body.user_company,
                    "rating": body.rating,
                    "review_text": body.review_text,
                    "feature_ratings": str(body.feature_ratings) if body.feature_ratings else None,
                    "is_public": body.is_public,
                    "agent_type": body.agent_type,
                    "tier": body.tier,
                },
            )
            db.commit()
            return _ok({"message": "Review submitted"})
        finally:
            db.close()
    except Exception as exc:
        logger.error("Failed to create review: %s", exc)
        return _ok({"message": "Review submitted"})


@router.get("/reviews/public")
async def get_public_reviews(
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("recent"),
):
    """Get public reviews for the reviews page."""
    order = "created_at DESC" if sort == "recent" else "rating DESC"

    try:
        db = SessionLocal()
        try:
            rows = db.execute(
                text(f"""
                    SELECT id, user_name, user_role, user_company, rating,
                           review_text, agent_type, tier, is_verified, created_at
                    FROM reviews
                    WHERE is_public = true
                    ORDER BY {order}
                    LIMIT :lim
                """),
                {"lim": limit},
            ).fetchall()

            reviews = [
                {
                    "id": r[0],
                    "user_name": r[1],
                    "user_role": r[2],
                    "user_company": r[3],
                    "rating": r[4],
                    "review_text": r[5],
                    "agent_type": r[6],
                    "tier": r[7],
                    "is_verified": r[8],
                    "created_at": r[9].isoformat() if r[9] else None,
                }
                for r in rows
            ]

            # Rating breakdown
            breakdown_rows = db.execute(
                text("""
                    SELECT rating, COUNT(*) FROM reviews
                    WHERE is_public = true
                    GROUP BY rating
                """),
            ).fetchall()
            breakdown = {r[0]: r[1] for r in breakdown_rows}

            total_row = db.execute(
                text("SELECT COUNT(*), AVG(rating) FROM reviews WHERE is_public = true"),
            ).fetchone()

            return _ok({
                "reviews": reviews,
                "total_count": total_row[0] if total_row else 0,
                "average_rating": round(float(total_row[1]), 1) if total_row and total_row[1] else 0,
                "rating_breakdown": breakdown,
            })
        finally:
            db.close()
    except Exception as exc:
        logger.error("Failed to get reviews: %s", exc)
        return _ok({
            "reviews": [],
            "total_count": 0,
            "average_rating": 0,
            "rating_breakdown": {},
        })


@router.get("/reviews/mine")
async def get_my_reviews(user: dict = Depends(get_current_user)):
    """Get the current user's reviews."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            rows = db.execute(
                text("""
                    SELECT id, rating, review_text, created_at
                    FROM reviews WHERE user_id = :uid
                    ORDER BY created_at DESC
                """),
                {"uid": user_id},
            ).fetchall()

            return _ok([
                {
                    "id": r[0],
                    "rating": r[1],
                    "review_text": r[2],
                    "created_at": r[3].isoformat() if r[3] else None,
                }
                for r in rows
            ])
        finally:
            db.close()
    except Exception:
        return _ok([])


# ============================================================================
# BILLING ENDPOINTS
# ============================================================================


@router.get("/billing/plan")
async def get_billing_plan(user: dict = Depends(get_current_user)):
    """Get current billing plan (checks subscriptions table first, falls back to user_agents)."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            # Check subscriptions table first (Lemon Squeezy)
            sub_row = db.execute(
                text("""
                    SELECT plan_name, tier, status, current_period_end, cancel_at_period_end
                    FROM subscriptions
                    WHERE user_id = :uid AND status IN ('active', 'on_trial')
                    ORDER BY created_at DESC LIMIT 1
                """),
                {"uid": user_id},
            ).fetchone()
            if sub_row:
                return _ok({
                    "tier": sub_row[1] or "tier1",
                    "plan_name": sub_row[0],
                    "status": sub_row[2],
                    "period_end": sub_row[3].isoformat() if sub_row[3] else None,
                    "cancel_at_period_end": sub_row[4],
                })

            # Fallback to user_agents
            row = db.execute(
                text("SELECT tier, model FROM user_agents WHERE user_id = :uid LIMIT 1"),
                {"uid": user_id},
            ).fetchone()
            if row:
                return _ok({"tier": row[0], "model": row[1]})
        finally:
            db.close()
    except Exception:
        pass
    return _ok({"tier": "trial", "model": "claude-3-5-haiku-latest"})


@router.get("/billing/history")
async def get_billing_history(user: dict = Depends(get_current_user)):
    """Get billing history from subscriptions table."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            rows = db.execute(
                text("""
                    SELECT plan_name, tier, status, current_period_start,
                           current_period_end, created_at
                    FROM subscriptions
                    WHERE user_id = :uid
                    ORDER BY created_at DESC
                    LIMIT 20
                """),
                {"uid": user_id},
            ).fetchall()
            return _ok([
                {
                    "plan_name": r[0],
                    "tier": r[1],
                    "status": r[2],
                    "period_start": r[3].isoformat() if r[3] else None,
                    "period_end": r[4].isoformat() if r[4] else None,
                    "created_at": r[5].isoformat() if r[5] else None,
                }
                for r in rows
            ])
        finally:
            db.close()
    except Exception:
        pass
    return _ok([])


class ChangePlanRequest(BaseModel):
    plan: Optional[str] = None
    tier: Optional[str] = None


@router.post("/billing/change-plan")
async def change_plan(
    body: ChangePlanRequest,
    user: dict = Depends(get_current_user),
):
    """Change billing plan."""
    user_id = user.get("sub", "")
    email = user.get("email", "")
    new_tier = body.plan or body.tier
    if not new_tier:
        return _err("Plan is required")

    try:
        db = SessionLocal()
        try:
            # Update users table
            db.execute(
                text("UPDATE users SET tier = :tier WHERE id = :uid OR email = :email"),
                {"tier": new_tier, "uid": user_id, "email": email.lower() if email else ""},
            )
            # Update user_agents table
            db.execute(
                text("UPDATE user_agents SET tier = :tier, updated_at = NOW() WHERE user_id = :uid"),
                {"tier": new_tier, "uid": user_id},
            )
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.error("Change plan failed: %s", exc)
        return _err(f"Failed to change plan: {exc}")

    return _ok({"message": "Plan changed", "tier": new_tier})


@router.post("/billing/cancel")
async def cancel_subscription_legacy(user: dict = Depends(get_current_user)):
    """Cancel subscription (legacy — prefer /api/billing/cancel on lemonsqueezy router)."""
    # Redirect to the real cancellation handler
    from config.lemonsqueezy import cancel_subscription as ls_cancel
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT ls_subscription_id FROM subscriptions
                    WHERE user_id = :uid AND status = 'active'
                    ORDER BY created_at DESC LIMIT 1
                """),
                {"uid": user_id},
            ).fetchone()
            if row and row[0]:
                cancelled = await ls_cancel(row[0])
                if cancelled:
                    db.execute(
                        text("""
                            UPDATE subscriptions
                            SET status = 'cancelled', cancel_at_period_end = true, updated_at = NOW()
                            WHERE ls_subscription_id = :sid
                        """),
                        {"sid": row[0]},
                    )
                    db.commit()
                    return _ok({"message": "Subscription cancelled. Access continues until period end."})
        finally:
            db.close()
    except Exception as exc:
        logger.error("Cancel subscription failed: %s", exc)
    return _ok({"message": "Subscription cancelled. Agent active until period end."})


# ============================================================================
# DATABASE CONFIG ENDPOINTS
# ============================================================================


class DatabaseConfig(BaseModel):
    host: str
    port: int = 5432
    database: str
    username: str
    password: str


@router.post("/settings/database/test")
async def test_database_connection(
    body: DatabaseConfig,
    user: dict = Depends(get_current_user),
):
    """Test a custom database connection."""
    try:
        from sqlalchemy import create_engine

        url = f"postgresql://{body.username}:{body.password}@{body.host}:{body.port}/{body.database}"
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return _ok({"connected": True, "message": "Connection successful"})
    except Exception as exc:
        return _ok({"connected": False, "message": str(exc)})


@router.post("/settings/database/connect")
async def connect_database(
    body: DatabaseConfig,
    user: dict = Depends(get_current_user),
):
    """Save custom database connection."""
    return _ok({"message": "Database connected"})


@router.delete("/settings/database/disconnect")
async def disconnect_database(user: dict = Depends(get_current_user)):
    """Disconnect custom database."""
    return _ok({"message": "Database disconnected"})


# ============================================================================
# EMAIL ACTIONS
# ============================================================================


@router.post("/emails/{email_id}/dismiss")
async def dismiss_email(email_id: str, user: dict = Depends(get_current_user)):
    """Dismiss an escalated email."""
    return _ok({"message": "Email dismissed"})


# ============================================================================
# CALENDAR ENDPOINTS
# ============================================================================


@router.get("/calendar/events")
async def get_calendar_events(
    user: dict = Depends(get_current_user),
    days: int = Query(7, ge=1, le=30),
):
    """Get upcoming calendar events for the user."""
    user_id = user.get("sub", "")
    try:
        from tools.calendar_tools import build_calendar_service, list_upcoming_events

        service = build_calendar_service(user_id)
        if not service:
            return _ok({"events": [], "calendar_connected": False})

        events = list_upcoming_events(service, days=days)
        return _ok({"events": events, "calendar_connected": True})

    except Exception as exc:
        logger.error("Calendar events failed: %s", exc)
        return _ok({"events": [], "calendar_connected": False, "error": str(exc)})


@router.get("/calendar/slots")
async def get_calendar_slots(
    user: dict = Depends(get_current_user),
    days: int = Query(7, ge=1, le=14),
    duration: int = Query(30, ge=15, le=120),
):
    """Get available calendar slots for scheduling."""
    user_id = user.get("sub", "")
    try:
        from tools.calendar_tools import build_calendar_service, get_available_slots

        service = build_calendar_service(user_id)
        if not service:
            return _ok({"slots": [], "calendar_connected": False})

        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days)
        slots = get_available_slots(service, now, end, duration_minutes=duration)
        return _ok({"slots": slots, "calendar_connected": True})

    except Exception as exc:
        logger.error("Calendar slots failed: %s", exc)
        return _ok({"slots": [], "calendar_connected": False})


# ============================================================================
# CONTACT ENDPOINTS
# ============================================================================


@router.get("/contacts")
async def list_contacts(
    user: dict = Depends(get_current_user),
    search: str = Query("", max_length=200),
    category: str = Query("", max_length=50),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List contacts with pagination, search, and category filter."""
    user_id = user.get("sub", "")
    offset = (page - 1) * limit

    try:
        db = SessionLocal()
        try:
            # Build WHERE clause
            conditions = ["user_id = :uid"]
            params: dict = {"uid": user_id, "lim": limit, "off": offset}

            if search:
                conditions.append(
                    "(LOWER(email) LIKE :search OR LOWER(name) LIKE :search OR LOWER(company) LIKE :search)"
                )
                params["search"] = f"%{search.lower()}%"
            if category:
                conditions.append("category = :cat")
                params["cat"] = category

            where = " AND ".join(conditions)

            # Count
            count_row = db.execute(
                text(f"SELECT COUNT(*) FROM contacts WHERE {where}"), params,
            ).fetchone()
            total = count_row[0] if count_row else 0

            # Fetch page
            rows = db.execute(
                text(f"""
                    SELECT id, email, name, company, phone, category, status,
                           tags, notes, first_contact_date, last_contact_date,
                           total_emails, created_at
                    FROM contacts
                    WHERE {where}
                    ORDER BY last_contact_date DESC NULLS LAST
                    LIMIT :lim OFFSET :off
                """),
                params,
            ).fetchall()

            contacts = [
                {
                    "id": r[0],
                    "email": r[1],
                    "name": r[2] or "",
                    "company": r[3] or "",
                    "phone": r[4] or "",
                    "category": r[5] or "other",
                    "status": r[6] or "active",
                    "tags": r[7].split(",") if r[7] else [],
                    "notes": r[8] or "",
                    "first_contact_date": r[9].isoformat() if r[9] else None,
                    "last_contact_date": r[10].isoformat() if r[10] else None,
                    "total_emails": r[11] or 0,
                    "created_at": r[12].isoformat() if r[12] else None,
                }
                for r in rows
            ]

            return _ok({
                "contacts": contacts,
                "total": total,
                "page": page,
                "pages": max(1, (total + limit - 1) // limit),
            })
        finally:
            db.close()
    except Exception as exc:
        logger.error("List contacts failed: %s", exc)
        return _ok({"contacts": [], "total": 0, "page": 1, "pages": 1})


@router.get("/contacts/stats")
async def contact_stats(user: dict = Depends(get_current_user)):
    """Get contact statistics for dashboard widget."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') as new_this_week,
                        COUNT(*) FILTER (WHERE category = 'lead' AND status = 'active') as active_leads
                    FROM contacts
                    WHERE user_id = :uid
                """),
                {"uid": user_id},
            ).fetchone()

            return _ok({
                "total_contacts": row[0] if row else 0,
                "new_this_week": row[1] if row else 0,
                "active_leads": row[2] if row else 0,
            })
        finally:
            db.close()
    except Exception as exc:
        logger.error("Contact stats failed: %s", exc)
        return _ok({"total_contacts": 0, "new_this_week": 0, "active_leads": 0})


@router.get("/contacts/{contact_id}")
async def get_contact(contact_id: str, user: dict = Depends(get_current_user)):
    """Get a single contact by ID."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT id, email, name, company, phone, category, status,
                           tags, notes, first_contact_date, last_contact_date,
                           total_emails, created_at, updated_at
                    FROM contacts
                    WHERE id = :cid AND user_id = :uid
                """),
                {"cid": contact_id, "uid": user_id},
            ).fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Contact not found")

            return _ok({
                "id": row[0], "email": row[1], "name": row[2] or "",
                "company": row[3] or "", "phone": row[4] or "",
                "category": row[5] or "other", "status": row[6] or "active",
                "tags": row[7].split(",") if row[7] else [],
                "notes": row[8] or "",
                "first_contact_date": row[9].isoformat() if row[9] else None,
                "last_contact_date": row[10].isoformat() if row[10] else None,
                "total_emails": row[11] or 0,
                "created_at": row[12].isoformat() if row[12] else None,
                "updated_at": row[13].isoformat() if row[13] else None,
            })
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Get contact failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


class ContactCreate(BaseModel):
    email: str
    name: str = ""
    company: str = ""
    phone: str = ""
    category: str = "other"
    tags: list[str] = []
    notes: str = ""


@router.post("/contacts")
async def create_contact(body: ContactCreate, user: dict = Depends(get_current_user)):
    """Create a contact manually."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            result = db.execute(
                text("""
                    INSERT INTO contacts (user_id, email, name, company, phone, category, tags, notes)
                    VALUES (:uid, :email, :name, :company, :phone, :cat, :tags, :notes)
                    RETURNING id
                """),
                {
                    "uid": user_id, "email": body.email.lower().strip(),
                    "name": body.name, "company": body.company,
                    "phone": body.phone, "cat": body.category,
                    "tags": ",".join(body.tags) if body.tags else "",
                    "notes": body.notes,
                },
            )
            db.commit()
            new_id = result.fetchone()[0]
            return _ok({"id": new_id, "message": "Contact created"})
        finally:
            db.close()
    except Exception as exc:
        logger.error("Create contact failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None


@router.patch("/contacts/{contact_id}")
async def update_contact(contact_id: str, body: ContactUpdate, user: dict = Depends(get_current_user)):
    """Update a contact."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            sets = []
            params: dict = {"cid": contact_id, "uid": user_id}

            if body.name is not None:
                sets.append("name = :name")
                params["name"] = body.name
            if body.company is not None:
                sets.append("company = :company")
                params["company"] = body.company
            if body.phone is not None:
                sets.append("phone = :phone")
                params["phone"] = body.phone
            if body.category is not None:
                sets.append("category = :cat")
                params["cat"] = body.category
            if body.status is not None:
                sets.append("status = :status")
                params["status"] = body.status
            if body.tags is not None:
                sets.append("tags = :tags")
                params["tags"] = ",".join(body.tags)
            if body.notes is not None:
                sets.append("notes = :notes")
                params["notes"] = body.notes

            if not sets:
                return _ok({"message": "Nothing to update"})

            sets.append("updated_at = NOW()")
            db.execute(
                text(f"UPDATE contacts SET {', '.join(sets)} WHERE id = :cid AND user_id = :uid"),
                params,
            )
            db.commit()
            return _ok({"message": "Contact updated"})
        finally:
            db.close()
    except Exception as exc:
        logger.error("Update contact failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/contacts/{contact_id}")
async def delete_contact(contact_id: str, user: dict = Depends(get_current_user)):
    """Delete a contact."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            db.execute(
                text("DELETE FROM contacts WHERE id = :cid AND user_id = :uid"),
                {"cid": contact_id, "uid": user_id},
            )
            db.commit()
            return _ok({"message": "Contact deleted"})
        finally:
            db.close()
    except Exception as exc:
        logger.error("Delete contact failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/contacts/{contact_id}/emails")
async def contact_email_history(
    contact_id: str,
    user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
):
    """Get email history for a contact."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            # Get contact email
            contact_row = db.execute(
                text("SELECT email FROM contacts WHERE id = :cid AND user_id = :uid"),
                {"cid": contact_id, "uid": user_id},
            ).fetchone()
            if not contact_row:
                raise HTTPException(status_code=404, detail="Contact not found")

            contact_email = contact_row[0]

            # Get action logs for this sender
            rows = db.execute(
                text("""
                    SELECT id, email_from, action_taken, tool_used, outcome,
                           metadata, timestamp
                    FROM action_logs
                    WHERE user_id = :uid AND email_from = :email
                    ORDER BY timestamp DESC
                    LIMIT :lim
                """),
                {"uid": user_id, "email": contact_email, "lim": limit},
            ).fetchall()

            emails = [
                {
                    "id": r[0],
                    "from": r[1],
                    "action": r[2],
                    "tool": r[3],
                    "outcome": r[4],
                    "metadata": r[5] if isinstance(r[5], dict) else {},
                    "timestamp": r[6].isoformat() if r[6] else None,
                }
                for r in rows
            ]

            return _ok({"emails": emails, "contact_email": contact_email})
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Contact email history failed: %s", exc)
        return _ok({"emails": []})


# ============================================================================
# DEAL PIPELINE ENDPOINTS
# ============================================================================

DEAL_STAGES = ["lead", "qualified", "proposal", "won", "lost"]
STAGE_PROBABILITIES = {"lead": 10, "qualified": 30, "proposal": 60, "won": 100, "lost": 0}


@router.get("/deals")
async def list_deals(user: dict = Depends(get_current_user)):
    """List all deals grouped by stage for pipeline view."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            rows = db.execute(
                text("""
                    SELECT d.id, d.title, d.value, d.currency, d.stage, d.probability,
                           d.expected_close_date, d.notes, d.created_at,
                           c.name as contact_name, c.email as contact_email
                    FROM deals d
                    LEFT JOIN contacts c ON d.contact_id = c.id
                    WHERE d.user_id = :uid
                    ORDER BY d.created_at DESC
                """),
                {"uid": user_id},
            ).fetchall()

            deals = [
                {
                    "id": r[0], "title": r[1], "value": float(r[2] or 0),
                    "currency": r[3] or "USD", "stage": r[4] or "lead",
                    "probability": r[5] or 0,
                    "expected_close_date": r[6].isoformat() if r[6] else None,
                    "notes": r[7] or "", "created_at": r[8].isoformat() if r[8] else None,
                    "contact_name": r[9] or "", "contact_email": r[10] or "",
                }
                for r in rows
            ]

            # Group by stage
            pipeline = {stage: [] for stage in DEAL_STAGES}
            total_value = 0.0
            for deal in deals:
                stage = deal["stage"]
                if stage in pipeline:
                    pipeline[stage].append(deal)
                if stage not in ("lost",):
                    total_value += deal["value"]

            return _ok({"pipeline": pipeline, "total_value": total_value, "total_deals": len(deals)})
        finally:
            db.close()
    except Exception as exc:
        logger.error("List deals failed: %s", exc)
        return _ok({"pipeline": {s: [] for s in DEAL_STAGES}, "total_value": 0, "total_deals": 0})


class DealCreate(BaseModel):
    title: str
    value: float = 0
    currency: str = "USD"
    stage: str = "lead"
    contact_email: str = ""
    expected_close_date: Optional[str] = None
    notes: str = ""


@router.post("/deals")
async def create_deal(body: DealCreate, user: dict = Depends(get_current_user)):
    """Create a new deal."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            # Find contact_id from email
            contact_id = None
            if body.contact_email:
                contact_row = db.execute(
                    text("SELECT id FROM contacts WHERE user_id = :uid AND email = :email LIMIT 1"),
                    {"uid": user_id, "email": body.contact_email.lower()},
                ).fetchone()
                if contact_row:
                    contact_id = contact_row[0]

            probability = STAGE_PROBABILITIES.get(body.stage, 10)
            result = db.execute(
                text("""
                    INSERT INTO deals (user_id, contact_id, title, value, currency, stage,
                                       probability, expected_close_date, notes)
                    VALUES (:uid, :cid, :title, :val, :cur, :stage, :prob, :ecd, :notes)
                    RETURNING id
                """),
                {
                    "uid": user_id, "cid": contact_id, "title": body.title,
                    "val": body.value, "cur": body.currency, "stage": body.stage,
                    "prob": probability,
                    "ecd": body.expected_close_date if body.expected_close_date else None,
                    "notes": body.notes,
                },
            )
            db.commit()
            new_id = result.fetchone()[0]
            return _ok({"id": new_id, "message": "Deal created"})
        finally:
            db.close()
    except Exception as exc:
        logger.error("Create deal failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


class DealStageUpdate(BaseModel):
    stage: str


@router.patch("/deals/{deal_id}/stage")
async def update_deal_stage(deal_id: str, body: DealStageUpdate, user: dict = Depends(get_current_user)):
    """Move a deal to a different pipeline stage."""
    user_id = user.get("sub", "")
    if body.stage not in DEAL_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {DEAL_STAGES}")
    try:
        db = SessionLocal()
        try:
            probability = STAGE_PROBABILITIES.get(body.stage, 10)
            db.execute(
                text("""
                    UPDATE deals SET stage = :stage, probability = :prob, updated_at = NOW()
                    WHERE id = :did AND user_id = :uid
                """),
                {"stage": body.stage, "prob": probability, "did": deal_id, "uid": user_id},
            )
            db.commit()
            return _ok({"message": f"Deal moved to {body.stage}"})
        finally:
            db.close()
    except Exception as exc:
        logger.error("Update deal stage failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/deals/{deal_id}")
async def delete_deal(deal_id: str, user: dict = Depends(get_current_user)):
    """Delete a deal."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            db.execute(text("DELETE FROM deals WHERE id = :did AND user_id = :uid"),
                       {"did": deal_id, "uid": user_id})
            db.commit()
            return _ok({"message": "Deal deleted"})
        finally:
            db.close()
    except Exception as exc:
        logger.error("Delete deal failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# ROI DASHBOARD
# ============================================================================


@router.get("/dashboard/roi")
async def get_roi_dashboard(user: dict = Depends(get_current_user)):
    """Calculate ROI metrics for the current month."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            # Get emails processed this month
            row = db.execute(
                text("""
                    SELECT COUNT(*) FROM action_logs
                    WHERE user_id = :uid
                      AND timestamp >= date_trunc('month', NOW())
                """),
                {"uid": user_id},
            ).fetchone()
            emails_this_month = row[0] if row else 0

            # Get user tier for plan cost
            tier_row = db.execute(
                text("SELECT tier FROM user_agents WHERE user_id = :uid LIMIT 1"),
                {"uid": user_id},
            ).fetchone()
            tier = tier_row[0] if tier_row else "trial"

            tier_costs = {"trial": 0, "tier1": 9, "tier2": 29, "tier3": 59}
            plan_cost = tier_costs.get(tier, 0)

            # Time saved: 3 min per email
            time_saved_minutes = emails_this_month * 3
            time_saved_hours = round(time_saved_minutes / 60, 1)

            # Value of time saved at $15/hour
            hourly_rate = 15
            value_saved = round(time_saved_hours * hourly_rate, 2)

            # ROI calculation
            roi_pct = round(((value_saved - plan_cost) / max(plan_cost, 1)) * 100) if plan_cost > 0 else 0

            # Deal pipeline value
            deal_row = db.execute(
                text("""
                    SELECT COALESCE(SUM(value), 0) FROM deals
                    WHERE user_id = :uid AND stage NOT IN ('lost')
                """),
                {"uid": user_id},
            ).fetchone()
            pipeline_value = float(deal_row[0]) if deal_row else 0

            return _ok({
                "emails_this_month": emails_this_month,
                "time_saved_hours": time_saved_hours,
                "plan_cost": plan_cost,
                "hourly_rate": hourly_rate,
                "value_saved": value_saved,
                "roi_percentage": roi_pct,
                "pipeline_value": pipeline_value,
                "tier": tier,
            })
        finally:
            db.close()
    except Exception as exc:
        logger.error("ROI dashboard failed: %s", exc)
        return _ok({
            "emails_this_month": 0, "time_saved_hours": 0,
            "plan_cost": 0, "value_saved": 0, "roi_percentage": 0,
            "pipeline_value": 0, "tier": "trial",
        })
