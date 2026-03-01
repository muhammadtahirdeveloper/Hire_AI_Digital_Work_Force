"""Agent registry for managing industry-specific agents.

Maps industry names to agent classes so the orchestrator can
dynamically route users to the correct agent.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry that maps industry names to agent classes."""

    def __init__(self) -> None:
        self.agents: dict[str, Any] = {}

    def register(self, industry: str, agent_class: Any) -> None:
        """Register an agent class for an industry.

        Args:
            industry: Industry name (e.g. 'general', 'hr').
            agent_class: The agent class to register.
        """
        self.agents[industry] = agent_class
        logger.info("AgentRegistry: Registered '%s' -> %s", industry, agent_class.__name__)

    def get_agent(self, industry: str) -> Any | None:
        """Get the agent class for an industry.

        Args:
            industry: Industry name to look up.

        Returns:
            The agent class, or None if not registered.
        """
        agent_class = self.agents.get(industry)
        if agent_class is None:
            logger.warning("AgentRegistry: No agent registered for industry '%s'.", industry)
        return agent_class

    def list_industries(self) -> list[str]:
        """List all registered industry names.

        Returns:
            List of industry name strings.
        """
        return list(self.agents.keys())
