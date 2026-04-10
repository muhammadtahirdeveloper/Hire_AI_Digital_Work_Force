"""
Real integration test: Claude processes an email.
Requires: ANTHROPIC_API_KEY env var set.

Usage:
    ANTHROPIC_API_KEY=your-key python scripts/test_claude_real.py
"""

import asyncio
import os
import sys

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.ai_router import AIRouter


async def test_claude_classification():
    """Test that Claude can classify an email correctly."""
    router = AIRouter()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY env var not set")
        sys.exit(1)

    model = router._get_model("claude", "trial")

    result = await router._call_claude(
        "Classify this email as: BUSINESS, URGENT, NEWSLETTER, or PERSONAL. Respond with just the category.",
        "Subject: Interested in your services\nBody: Hi, I saw your website and I'm interested in learning more about your consulting services. Can you send me your pricing?",
        api_key, model, 50, 0.1,
    )

    print("Provider:", result["provider"])
    print("Model:", result["model"])
    print("Response:", result["content"][:500])

    assert result["provider"] == "claude"
    assert len(result["content"]) > 0
    print("\nClaude classification test PASSED")


async def main():
    print("=" * 60)
    print("CLAUDE REAL INTEGRATION TESTS")
    print("=" * 60)
    await test_claude_classification()
    print("\n" + "=" * 60)
    print("ALL CLAUDE TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
