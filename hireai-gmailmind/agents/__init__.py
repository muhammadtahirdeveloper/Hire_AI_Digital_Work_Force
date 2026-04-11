# Standalone Agent SDK stubs for HireAI (Claude-only, no OpenAI SDK).
#
# The local agents/ directory contains industry-specific agent classes
# (GeneralAgent, HRAgent, etc.).  The agent/gmailmind.py and
# agent/tool_wrappers.py modules import `Agent` and `function_tool`
# which were originally from the openai-agents SDK.  Since HireAI uses
# Claude exclusively, we provide lightweight stand-ins here.

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Agent:
    """Minimal Agent container used by agent/gmailmind.py."""

    name: str = "GmailMind"
    instructions: str = ""
    tools: list = field(default_factory=list)
    model: str = "claude-haiku-4-5-20251001"


def function_tool(fn: Callable) -> Callable:
    """Decorator that marks a function as an agent tool.

    This is a no-op decorator — it simply returns the original function
    unchanged.  The function is collected into ``ALL_TOOLS`` and invoked
    directly by the orchestrator / reasoning loop.
    """
    fn._is_tool = True  # type: ignore[attr-defined]
    return fn
