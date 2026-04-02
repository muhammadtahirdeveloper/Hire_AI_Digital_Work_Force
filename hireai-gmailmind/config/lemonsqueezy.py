"""Lemon Squeezy API client wrapper.

Provides helpers for:
  - Creating checkout sessions
  - Managing subscriptions
  - Retrieving customer data
"""

import logging
from typing import Optional

import httpx

from config.settings import (
    LEMON_SQUEEZY_API_KEY,
    LEMON_SQUEEZY_STORE_ID,
    LEMON_SQUEEZY_STARTER_VARIANT_ID,
    LEMON_SQUEEZY_PRO_VARIANT_ID,
    LEMON_SQUEEZY_ENTERPRISE_VARIANT_ID,
)

logger = logging.getLogger(__name__)

LS_BASE_URL = "https://api.lemonsqueezy.com/v1"

PLAN_VARIANT_MAP = {
    "starter": LEMON_SQUEEZY_STARTER_VARIANT_ID,
    "tier1": LEMON_SQUEEZY_STARTER_VARIANT_ID,
    "professional": LEMON_SQUEEZY_PRO_VARIANT_ID,
    "tier2": LEMON_SQUEEZY_PRO_VARIANT_ID,
    "enterprise": LEMON_SQUEEZY_ENTERPRISE_VARIANT_ID,
    "tier3": LEMON_SQUEEZY_ENTERPRISE_VARIANT_ID,
}


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {LEMON_SQUEEZY_API_KEY}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }


async def create_checkout(
    plan: str,
    user_email: str,
    user_id: str,
    user_name: str = "",
    success_url: str = "",
) -> Optional[str]:
    """Create a Lemon Squeezy checkout URL for the given plan.

    Returns:
        The checkout URL string, or None if creation failed.
    """
    variant_id = PLAN_VARIANT_MAP.get(plan)
    if not variant_id:
        logger.error("No variant ID configured for plan: %s", plan)
        return None

    if not LEMON_SQUEEZY_API_KEY or not LEMON_SQUEEZY_STORE_ID:
        logger.error("Lemon Squeezy API key or store ID not configured")
        return None

    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "email": user_email,
                    "name": user_name,
                    "custom": {
                        "user_id": user_id,
                    },
                },
                "product_options": {
                    "redirect_url": success_url or "",
                },
            },
            "relationships": {
                "store": {
                    "data": {
                        "type": "stores",
                        "id": LEMON_SQUEEZY_STORE_ID,
                    }
                },
                "variant": {
                    "data": {
                        "type": "variants",
                        "id": variant_id,
                    }
                },
            },
        }
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{LS_BASE_URL}/checkouts",
            headers=_headers(),
            json=payload,
            timeout=15.0,
        )

    if res.status_code in (200, 201):
        data = res.json()
        checkout_url = data.get("data", {}).get("attributes", {}).get("url")
        logger.info("Checkout created for user %s, plan %s", user_id, plan)
        return checkout_url

    logger.error("Checkout creation failed: %s %s", res.status_code, res.text)
    return None


async def cancel_subscription(subscription_id: str) -> bool:
    """Cancel a Lemon Squeezy subscription."""
    async with httpx.AsyncClient() as client:
        res = await client.delete(
            f"{LS_BASE_URL}/subscriptions/{subscription_id}",
            headers=_headers(),
            timeout=15.0,
        )

    if res.status_code in (200, 204):
        logger.info("Subscription %s cancelled", subscription_id)
        return True

    logger.error("Cancel failed: %s %s", res.status_code, res.text)
    return False


async def get_subscription(subscription_id: str) -> Optional[dict]:
    """Retrieve subscription details from Lemon Squeezy."""
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{LS_BASE_URL}/subscriptions/{subscription_id}",
            headers=_headers(),
            timeout=15.0,
        )

    if res.status_code == 200:
        return res.json().get("data", {})
    return None


async def get_customer_portal_url(customer_id: str) -> Optional[str]:
    """Get the Lemon Squeezy customer portal URL for managing subscriptions."""
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{LS_BASE_URL}/customers/{customer_id}",
            headers=_headers(),
            timeout=15.0,
        )

    if res.status_code == 200:
        return res.json().get("data", {}).get("attributes", {}).get("urls", {}).get("customer_portal")
    return None
