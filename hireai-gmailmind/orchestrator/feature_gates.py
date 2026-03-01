"""Feature gating based on subscription tiers.

Controls which features each user can access based on their
subscription tier (tier1/tier2/tier3). Reads tier info from
the user_subscriptions table and usage from action_logs.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import text

from config.database import SessionLocal

logger = logging.getLogger(__name__)


class FeatureGate:
    """Manages feature access based on subscription tiers."""

    TIER_FEATURES = {
        "tier1": {
            "price": 19,
            "max_accounts": 1,
            "max_emails_per_day": 200,
            "features": ["read", "label", "archive", "basic_email_report"],
        },
        "tier2": {
            "price": 49,
            "max_accounts": 3,
            "max_emails_per_day": 500,
            "features": [
                "read", "label", "archive", "auto_reply",
                "escalation", "follow_up", "whatsapp_report",
                "cv_processing", "interview_scheduler",
                "candidate_tracker", "basic_crm", "basic_email_report",
            ],
        },
        "tier3": {
            "price": 99,
            "max_accounts": 9999,
            "max_emails_per_day": 999999,
            "features": ["all"],
        },
    }

    def get_user_tier(self, user_id: str) -> str:
        """Read user tier from user_subscriptions table.

        Args:
            user_id: The user ID to look up.

        Returns:
            Tier string (tier1/tier2/tier3). Defaults to 'tier2' if not found.
        """
        db = SessionLocal()
        try:
            row = db.execute(
                text("SELECT tier FROM user_subscriptions WHERE user_id = :uid"),
                {"uid": user_id},
            ).fetchone()

            if row and row[0]:
                tier = row[0]
                logger.info("FeatureGate: user=%s tier=%s", user_id, tier)
                return tier

            logger.info("FeatureGate: No tier found for user=%s, defaulting to tier2.", user_id)
            return "tier2"
        except Exception as exc:
            logger.warning("FeatureGate: Error reading tier for user=%s: %s. Defaulting to tier2.", user_id, exc)
            return "tier2"
        finally:
            db.close()

    def can_use_feature(self, user_id: str, feature_name: str) -> bool:
        """Check if a user's tier allows a specific feature.

        Args:
            user_id: The user ID.
            feature_name: The feature to check (e.g. 'auto_reply', 'cv_processing').

        Returns:
            True if the feature is available, False otherwise.
        """
        tier = self.get_user_tier(user_id)
        tier_config = self.TIER_FEATURES.get(tier, {})
        features = tier_config.get("features", [])

        # tier3 has access to everything
        if "all" in features:
            return True

        allowed = feature_name in features
        if not allowed:
            logger.info(
                "FeatureGate: Feature '%s' blocked for user=%s (tier=%s).",
                feature_name, user_id, tier,
            )
        return allowed

    def get_usage_today(self, user_id: str) -> int:
        """Count today's action_logs entries for this user.

        Args:
            user_id: The user ID.

        Returns:
            Number of actions taken today.
        """
        db = SessionLocal()
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            row = db.execute(
                text("""
                    SELECT COUNT(*) FROM action_logs
                    WHERE timestamp::date = :today
                """),
                {"today": today},
            ).fetchone()

            count = row[0] if row else 0
            logger.info("FeatureGate: user=%s usage_today=%d", user_id, count)
            return count
        except Exception as exc:
            logger.warning("FeatureGate: Error reading usage for user=%s: %s", user_id, exc)
            return 0
        finally:
            db.close()

    def check_daily_limit(self, user_id: str) -> bool:
        """Check if user is under their daily email limit.

        Args:
            user_id: The user ID.

        Returns:
            True if under limit, False if exceeded.
        """
        tier = self.get_user_tier(user_id)
        tier_config = self.TIER_FEATURES.get(tier, {})
        max_emails = tier_config.get("max_emails_per_day", 200)

        usage = self.get_usage_today(user_id)
        under_limit = usage < max_emails

        if not under_limit:
            logger.warning(
                "FeatureGate: Daily limit exceeded for user=%s (tier=%s, usage=%d/%d).",
                user_id, tier, usage, max_emails,
            )
        return under_limit

    def get_upgrade_message(self, current_tier: str, blocked_feature: str) -> str:
        """Return a friendly upgrade suggestion message.

        Args:
            current_tier: The user's current tier.
            blocked_feature: The feature that was blocked.

        Returns:
            Upgrade suggestion string.
        """
        # Find which tier has the feature
        for tier_name, tier_config in self.TIER_FEATURES.items():
            features = tier_config.get("features", [])
            if "all" in features or blocked_feature in features:
                if tier_name != current_tier:
                    price = tier_config.get("price", "??")
                    return (
                        f"The '{blocked_feature}' feature requires {tier_name} "
                        f"(${price}/month). You are currently on {current_tier}. "
                        f"Upgrade to unlock this feature!"
                    )

        return (
            f"The '{blocked_feature}' feature is not available on your "
            f"current plan ({current_tier}). Please contact support for upgrade options."
        )
