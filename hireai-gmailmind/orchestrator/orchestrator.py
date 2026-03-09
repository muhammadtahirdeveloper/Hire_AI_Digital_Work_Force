"""GmailMind Orchestrator — Master Brain.

Routes users to the correct specialist agent based on their
subscription tier and industry. Enforces feature gates and
daily usage limits before dispatching work.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import text

from config.database import SessionLocal
from orchestrator.agent_registry import AgentRegistry
from orchestrator.feature_gates import FeatureGate
from orchestrator.user_router import UserRouter

logger = logging.getLogger(__name__)


class GmailMindOrchestrator:
    """Master orchestrator that routes users to specialist agents."""

    def __init__(self) -> None:
        self.registry = AgentRegistry()
        self.router = UserRouter()
        self.gates = FeatureGate()

        # Register known agents (GeneralAgent is always available).
        self._register_default_agents()

    def _register_default_agents(self) -> None:
        """Register all available agent classes."""
        try:
            from agents.general.general_agent import GeneralAgent
            self.registry.register("general", GeneralAgent)
        except ImportError:
            logger.warning("Orchestrator: GeneralAgent not available yet.")

        try:
            from agents.hr.hr_agent import HRAgent
            self.registry.register("hr", HRAgent)
        except ImportError:
            logger.info("Orchestrator: HRAgent not available yet (Phase 2 Prompt 13).")

        try:
            from agents.real_estate.real_estate_agent import RealEstateAgent
            self.registry.register("real_estate", RealEstateAgent)
            logger.info("Orchestrator: RealEstateAgent registered successfully.")
        except ImportError:
            logger.info("Orchestrator: RealEstateAgent not available yet (Phase 3 Prompt 27).")

        try:
            from agents.ecommerce.ecommerce_agent import EcommerceAgent
            self.registry.register("ecommerce", EcommerceAgent)
            logger.info("Orchestrator: EcommerceAgent registered successfully.")
        except ImportError:
            logger.info("Orchestrator: EcommerceAgent not available yet (Phase 3 Prompt 28).")

    def process_user(self, user_id: str) -> dict:
        """Process a user through the full orchestration pipeline.

        Steps:
            1. Get user tier and check limits.
            2. Get user industry and route to correct agent.
            3. Return routing info with available features.

        The caller (scheduler task) uses the routing info to decide
        which execution path to take:
        - ``general`` industry → existing reasoning_loop
        - ``hr`` industry → HRAgent.process_email pipeline

        Args:
            user_id: The user ID to process.

        Returns:
            Dict with routing result (status, industry, tier, features, etc.).
        """
        logger.info("Orchestrator: Processing user=%s", user_id)

        # Step 1: Get tier and check limits
        tier = self.gates.get_user_tier(user_id)

        if not self.gates.check_daily_limit(user_id):
            logger.warning(
                "Orchestrator: Daily limit exceeded for user=%s tier=%s. Skipping.",
                user_id, tier,
            )
            return {"status": "skipped", "reason": "daily_limit_exceeded"}

        # Step 2: Get industry and route
        industry = self.router.get_user_industry(user_id)

        agent_class = self.registry.get_agent(industry)
        if agent_class is None:
            logger.info(
                "Orchestrator: No agent for industry '%s', falling back to 'general'.",
                industry,
            )
            industry = "general"
            agent_class = self.registry.get_agent("general")

        # Step 3: Log routing
        agent_name = agent_class.__name__ if agent_class else "Unknown"
        logger.info(
            "Orchestrator: Routing user=%s to %s agent (industry=%s, tier=%s)",
            user_id, agent_name, industry, tier,
        )

        # Step 4: Get available features
        features = self.gates.TIER_FEATURES.get(tier, {}).get("features", [])

        return {
            "status": "routed",
            "user_id": user_id,
            "industry": industry,
            "tier": tier,
            "agent": agent_name,
            "features": features,
        }

    def get_platform_stats(self) -> dict:
        """Get platform-wide statistics.

        Returns:
            Dict with active_users count and emails_processed_today count.
        """
        db = SessionLocal()
        try:
            # Count active users
            active_row = db.execute(
                text("SELECT COUNT(*) FROM user_subscriptions WHERE status = 'active'")
            ).fetchone()
            active_users = active_row[0] if active_row else 0

            # Count emails processed today
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            emails_row = db.execute(
                text("SELECT COUNT(*) FROM action_logs WHERE timestamp::date = :today"),
                {"today": today},
            ).fetchone()
            emails_today = emails_row[0] if emails_row else 0

            stats = {
                "active_users": active_users,
                "emails_processed_today": emails_today,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            logger.info("Orchestrator: Platform stats: %s", stats)
            return stats
        except Exception as exc:
            logger.warning("Orchestrator: Error getting platform stats: %s", exc)
            return {
                "active_users": 0,
                "emails_processed_today": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        finally:
            db.close()
