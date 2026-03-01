"""User routing — determines tier and industry for each user.

Reads from user_subscriptions and user_configs tables to route
users to the correct agent with the correct feature set.
"""

import logging

from sqlalchemy import text

from config.database import SessionLocal
from orchestrator.feature_gates import FeatureGate

logger = logging.getLogger(__name__)


class UserRouter:
    """Routes users to the correct agent based on tier and industry."""

    def __init__(self) -> None:
        self.gates = FeatureGate()

    def get_user_tier(self, user_id: str) -> str:
        """Read user tier from user_subscriptions table.

        Args:
            user_id: The user ID.

        Returns:
            Tier string. Defaults to 'tier2'.
        """
        return self.gates.get_user_tier(user_id)

    def get_user_industry(self, user_id: str) -> str:
        """Read user industry from user_configs table.

        Args:
            user_id: The user ID.

        Returns:
            Industry string (e.g. 'general', 'hr'). Defaults to 'general'.
        """
        db = SessionLocal()
        try:
            row = db.execute(
                text("SELECT industry FROM user_configs WHERE user_id = :uid"),
                {"uid": user_id},
            ).fetchone()

            if row and row[0]:
                industry = row[0]
                logger.info("UserRouter: user=%s industry=%s", user_id, industry)
                return industry

            logger.info("UserRouter: No industry found for user=%s, defaulting to 'general'.", user_id)
            return "general"
        except Exception as exc:
            logger.warning("UserRouter: Error reading industry for user=%s: %s. Defaulting to 'general'.", user_id, exc)
            return "general"
        finally:
            db.close()

    def route_user(self, user_id: str) -> dict:
        """Route a user by determining their tier, industry, and available features.

        Args:
            user_id: The user ID.

        Returns:
            Dict with keys: industry, tier, features_available.
        """
        tier = self.get_user_tier(user_id)
        industry = self.get_user_industry(user_id)

        tier_config = self.gates.TIER_FEATURES.get(tier, {})
        features = tier_config.get("features", [])

        result = {
            "industry": industry,
            "tier": tier,
            "features_available": features,
        }
        logger.info("UserRouter: Routed user=%s -> %s", user_id, result)
        return result
