"""Lemon Squeezy billing routes.

Provides:
  - POST /api/billing/checkout      — Create a checkout URL for a plan
  - POST /api/webhooks/lemonsqueezy — Receive and process LS webhook events
  - GET  /api/billing/subscription  — Get current subscription details
  - POST /api/billing/cancel        — Cancel subscription via LS API
  - GET  /api/billing/portal        — Get customer portal URL
  - GET  /api/billing/history       — Get payment history from subscriptions table
"""

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import text

from api.middleware import get_current_user
from config.database import SessionLocal
from config.lemonsqueezy import (
    cancel_subscription as ls_cancel_subscription,
    create_checkout,
    get_customer_portal_url,
    get_subscription,
)
from config.settings import LEMON_SQUEEZY_WEBHOOK_SECRET

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request / Response Models
# ============================================================================


class CheckoutRequest(BaseModel):
    plan: str  # "starter", "professional", "enterprise"
    success_url: str = ""


# ============================================================================
# CHECKOUT — Create Lemon Squeezy checkout URL
# ============================================================================


@router.post("/billing/checkout")
async def billing_checkout(
    body: CheckoutRequest,
    user: dict = Depends(get_current_user),
):
    """Create a Lemon Squeezy hosted checkout URL for the requested plan."""
    user_id = user.get("sub", "")
    email = user.get("email", "")
    name = user.get("name", user.get("user_metadata", {}).get("full_name", ""))

    checkout_url = await create_checkout(
        plan=body.plan,
        user_email=email,
        user_id=user_id,
        user_name=name,
        success_url=body.success_url,
    )

    if not checkout_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create checkout session. Please try again.",
        )

    return {"success": True, "data": {"checkout_url": checkout_url}, "error": None}


# ============================================================================
# SUBSCRIPTION — Get current subscription details
# ============================================================================


@router.get("/billing/subscription")
async def get_billing_subscription(user: dict = Depends(get_current_user)):
    """Get the user's current subscription details from the local DB."""
    user_id = user.get("sub", "")

    try:
        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT ls_subscription_id, ls_customer_id, plan_name, tier,
                           status, current_period_start, current_period_end,
                           cancel_at_period_end, created_at, updated_at
                    FROM subscriptions
                    WHERE user_id = :uid
                    ORDER BY created_at DESC
                    LIMIT 1
                """),
                {"uid": user_id},
            ).fetchone()

            if not row:
                return {
                    "success": True,
                    "data": {"subscription": None},
                    "error": None,
                }

            subscription = {
                "ls_subscription_id": row[0],
                "ls_customer_id": row[1],
                "plan_name": row[2],
                "tier": row[3],
                "status": row[4],
                "current_period_start": row[5].isoformat() if row[5] else None,
                "current_period_end": row[6].isoformat() if row[6] else None,
                "cancel_at_period_end": row[7],
                "created_at": row[8].isoformat() if row[8] else None,
                "updated_at": row[9].isoformat() if row[9] else None,
            }

            return {
                "success": True,
                "data": {"subscription": subscription},
                "error": None,
            }
        finally:
            db.close()
    except Exception as exc:
        logger.error("Failed to get subscription: %s", exc)
        return {"success": True, "data": {"subscription": None}, "error": None}


# ============================================================================
# CANCEL — Cancel subscription via Lemon Squeezy API
# ============================================================================


@router.post("/billing/cancel")
async def cancel_billing(user: dict = Depends(get_current_user)):
    """Cancel the user's active subscription."""
    user_id = user.get("sub", "")

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
    finally:
        db.close()

    if not row or not row[0]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found.",
        )

    ls_sub_id = row[0]
    cancelled = await ls_cancel_subscription(ls_sub_id)

    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to cancel subscription. Please try again.",
        )

    # Mark locally as cancelled (webhook will also update, but do it eagerly)
    db = SessionLocal()
    try:
        db.execute(
            text("""
                UPDATE subscriptions
                SET status = 'cancelled', cancel_at_period_end = true, updated_at = NOW()
                WHERE ls_subscription_id = :sid
            """),
            {"sid": ls_sub_id},
        )
        db.commit()
    finally:
        db.close()

    return {
        "success": True,
        "data": {"message": "Subscription cancelled. Access continues until period end."},
        "error": None,
    }


# ============================================================================
# PORTAL — Get Lemon Squeezy customer portal URL
# ============================================================================


@router.get("/billing/portal")
async def get_billing_portal(user: dict = Depends(get_current_user)):
    """Get the Lemon Squeezy customer portal URL for managing billing."""
    user_id = user.get("sub", "")

    db = SessionLocal()
    try:
        row = db.execute(
            text("""
                SELECT ls_customer_id FROM subscriptions
                WHERE user_id = :uid
                ORDER BY created_at DESC LIMIT 1
            """),
            {"uid": user_id},
        ).fetchone()
    finally:
        db.close()

    if not row or not row[0]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No billing account found. Subscribe first.",
        )

    portal_url = await get_customer_portal_url(row[0])
    if not portal_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to get customer portal URL.",
        )

    return {"success": True, "data": {"portal_url": portal_url}, "error": None}


# ============================================================================
# HISTORY — Payment history from subscriptions table
# ============================================================================


@router.get("/billing/history")
async def get_billing_history(user: dict = Depends(get_current_user)):
    """Get billing / subscription history for the user."""
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

            history = [
                {
                    "plan_name": r[0],
                    "tier": r[1],
                    "status": r[2],
                    "period_start": r[3].isoformat() if r[3] else None,
                    "period_end": r[4].isoformat() if r[4] else None,
                    "created_at": r[5].isoformat() if r[5] else None,
                }
                for r in rows
            ]

            return {"success": True, "data": history, "error": None}
        finally:
            db.close()
    except Exception as exc:
        logger.error("Failed to get billing history: %s", exc)
        return {"success": True, "data": [], "error": None}


# ============================================================================
# WEBHOOK — Lemon Squeezy event handler (NO AUTH — verified via HMAC signature)
# ============================================================================


def _verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify the X-Signature header using the webhook secret."""
    if not LEMON_SQUEEZY_WEBHOOK_SECRET:
        logger.warning("LEMON_SQUEEZY_WEBHOOK_SECRET not set — skipping verification")
        return True  # Allow in dev when secret isn't configured

    digest = hmac.new(
        LEMON_SQUEEZY_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(digest, signature)


@router.post("/webhooks/lemonsqueezy")
async def lemonsqueezy_webhook(request: Request):
    """Handle Lemon Squeezy webhook events.

    Events handled:
      - subscription_created
      - subscription_updated
      - subscription_cancelled
      - subscription_payment_success
      - subscription_payment_failed
    """
    body = await request.body()
    signature = request.headers.get("X-Signature", "")

    if not _verify_webhook_signature(body, signature):
        logger.warning("Webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid signature")

    import json

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_name = data.get("meta", {}).get("event_name", "")
    custom_data = data.get("meta", {}).get("custom_data", {})
    user_id = custom_data.get("user_id", "")

    attrs = data.get("data", {}).get("attributes", {})
    ls_subscription_id = str(data.get("data", {}).get("id", ""))
    ls_customer_id = str(attrs.get("customer_id", ""))
    ls_order_id = str(attrs.get("order_id", ""))
    sub_status = attrs.get("status", "")
    plan_name = attrs.get("product_name", "") or attrs.get("variant_name", "")

    # Parse date fields
    renews_at = attrs.get("renews_at")
    ends_at = attrs.get("ends_at")
    created_at = attrs.get("created_at")

    logger.info(
        "LS webhook: event=%s user=%s sub=%s status=%s",
        event_name, user_id, ls_subscription_id, sub_status,
    )

    # Determine tier from variant/product name
    tier = _resolve_tier(plan_name)

    if event_name in (
        "subscription_created",
        "subscription_updated",
        "subscription_payment_success",
    ):
        _upsert_subscription(
            user_id=user_id,
            ls_subscription_id=ls_subscription_id,
            ls_customer_id=ls_customer_id,
            ls_order_id=ls_order_id,
            plan_name=plan_name,
            tier=tier,
            status=sub_status if sub_status else "active",
            renews_at=renews_at,
            ends_at=ends_at,
        )

        # Also update user tier in users + user_agents tables
        if user_id and tier:
            _update_user_tier(user_id, tier)

    elif event_name in ("subscription_cancelled", "subscription_expired"):
        _upsert_subscription(
            user_id=user_id,
            ls_subscription_id=ls_subscription_id,
            ls_customer_id=ls_customer_id,
            ls_order_id=ls_order_id,
            plan_name=plan_name,
            tier=tier,
            status="cancelled",
            renews_at=renews_at,
            ends_at=ends_at,
        )

    elif event_name == "subscription_payment_failed":
        _upsert_subscription(
            user_id=user_id,
            ls_subscription_id=ls_subscription_id,
            ls_customer_id=ls_customer_id,
            ls_order_id=ls_order_id,
            plan_name=plan_name,
            tier=tier,
            status="past_due",
            renews_at=renews_at,
            ends_at=ends_at,
        )

    return {"success": True}


# ============================================================================
# Helpers
# ============================================================================


def _resolve_tier(plan_name: str) -> str:
    """Map a Lemon Squeezy product/variant name to our internal tier."""
    name = (plan_name or "").lower()
    if "enterprise" in name:
        return "tier3"
    if "professional" in name or "pro" in name:
        return "tier2"
    if "starter" in name:
        return "tier1"
    return "tier1"  # Default to starter


def _upsert_subscription(
    user_id: str,
    ls_subscription_id: str,
    ls_customer_id: str,
    ls_order_id: str,
    plan_name: str,
    tier: str,
    status: str,
    renews_at: Optional[str] = None,
    ends_at: Optional[str] = None,
) -> None:
    """Insert or update subscription record."""
    db = SessionLocal()
    try:
        # Check if subscription already exists
        existing = db.execute(
            text("SELECT id FROM subscriptions WHERE ls_subscription_id = :sid LIMIT 1"),
            {"sid": ls_subscription_id},
        ).fetchone()

        if existing:
            db.execute(
                text("""
                    UPDATE subscriptions
                    SET status = :status,
                        plan_name = :plan_name,
                        tier = :tier,
                        ls_customer_id = :ls_customer_id,
                        ls_order_id = :ls_order_id,
                        current_period_end = :renews_at,
                        cancel_at_period_end = :cancel,
                        updated_at = NOW()
                    WHERE ls_subscription_id = :sid
                """),
                {
                    "status": status,
                    "plan_name": plan_name,
                    "tier": tier,
                    "ls_customer_id": ls_customer_id,
                    "ls_order_id": ls_order_id,
                    "renews_at": renews_at,
                    "cancel": status == "cancelled",
                    "sid": ls_subscription_id,
                },
            )
        else:
            db.execute(
                text("""
                    INSERT INTO subscriptions
                        (user_id, ls_subscription_id, ls_customer_id, ls_order_id,
                         plan_name, tier, status, current_period_start,
                         current_period_end, cancel_at_period_end)
                    VALUES
                        (:user_id, :ls_sub, :ls_cust, :ls_order,
                         :plan_name, :tier, :status, NOW(),
                         :renews_at, false)
                """),
                {
                    "user_id": user_id,
                    "ls_sub": ls_subscription_id,
                    "ls_cust": ls_customer_id,
                    "ls_order": ls_order_id,
                    "plan_name": plan_name,
                    "tier": tier,
                    "status": status,
                    "renews_at": renews_at,
                },
            )

        db.commit()
    except Exception as exc:
        logger.error("Failed to upsert subscription: %s", exc)
        db.rollback()
    finally:
        db.close()


def _update_user_tier(user_id: str, tier: str) -> None:
    """Update user tier in users and user_agents tables."""
    db = SessionLocal()
    try:
        db.execute(
            text("UPDATE users SET tier = :tier WHERE id = :uid"),
            {"tier": tier, "uid": user_id},
        )
        db.execute(
            text("UPDATE user_agents SET tier = :tier, updated_at = NOW() WHERE user_id = :uid"),
            {"tier": tier, "uid": user_id},
        )
        db.commit()
    except Exception as exc:
        logger.error("Failed to update user tier: %s", exc)
        db.rollback()
    finally:
        db.close()
