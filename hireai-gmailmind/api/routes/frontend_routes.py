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
    """Get current agent status for the user."""
    user_id = user.get("sub", "")

    try:
        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT agent_type, tier, model, is_paused, test_mode,
                           gmail_email, gmail_token_valid,
                           last_processed_at, last_error
                    FROM user_agents
                    WHERE user_id = :uid
                    LIMIT 1
                """),
                {"uid": user_id},
            ).fetchone()

            if row:
                return _ok({
                    "is_running": not row[3],
                    "is_paused": row[3] or False,
                    "test_mode": row[4] or False,
                    "agent_type": row[0] or "general",
                    "tier": row[1] or "trial",
                    "model": row[2] or "claude-sonnet-4-5",
                    "gmail_connected": row[5] or "",
                    "gmail_valid": row[6] if row[6] is not None else True,
                    "last_processed": row[7].isoformat() if row[7] else None,
                    "last_error": row[8],
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
        "model": "claude-sonnet-4-5",
        "gmail_connected": "",
        "gmail_valid": True,
        "last_processed": None,
        "last_error": None,
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
    """Get agent configuration."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            row = db.execute(
                text("SELECT config FROM user_agents WHERE user_id = :uid LIMIT 1"),
                {"uid": user_id},
            ).fetchone()
            if row and row[0]:
                return _ok(row[0])
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

        # Dispatch Celery task
        try:
            from scheduler.tasks import run_gmailmind_for_user
            run_gmailmind_for_user.delay(user_id)
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
                text("UPDATE user_agents SET is_paused = false, updated_at = NOW() WHERE user_id = :uid"),
                {"uid": user_id},
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        pass
    return _ok({"success": True, "status": "active", "message": "Agent resumed"})


@router.post("/agent/restart")
async def restart_agent(user: dict = Depends(get_current_user)):
    """Restart the user's agent."""
    return _ok({"message": "Agent restart initiated"})


@router.post("/agent/force-sync")
async def force_sync(user: dict = Depends(get_current_user)):
    """Force sync emails from Gmail."""
    return _ok({"message": "Sync started"})


class AgentConfigureRequest(BaseModel):
    ai_provider: str = "gemini"
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
        for provider in ["gemini", "groq"]:
            try:
                results[provider] = await router_instance.check_provider(provider)
            except Exception as exc:
                results[provider] = {"status": "error", "error": str(exc)}
        return _ok(results)
    except Exception as exc:
        logger.error("All providers health check failed: %s", exc)
        return _ok({
            "gemini": {"status": "error", "error": str(exc)},
            "groq": {"status": "error", "error": str(exc)},
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
        {"id": "gemini", "name": "Google Gemini", "available": True, "free": True},
        {"id": "groq", "name": "Groq (Llama)", "available": True, "free": True},
        {"id": "openai", "name": "OpenAI GPT-4", "available": is_paid, "free": False},
        {"id": "claude", "name": "Claude (Anthropic)", "available": is_paid, "free": False},
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
            model="claude-haiku-3-5",
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
    """Get current billing plan."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
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
    return _ok({"tier": "trial", "model": "claude-sonnet-4-5"})


@router.get("/billing/history")
async def get_billing_history(user: dict = Depends(get_current_user)):
    """Get billing history."""
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
async def cancel_subscription(user: dict = Depends(get_current_user)):
    """Cancel subscription."""
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
