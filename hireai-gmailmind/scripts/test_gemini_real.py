"""
Real integration test: Gemini processes an email.
Requires: GEMINI_API_KEY env var set.

Usage:
    GEMINI_API_KEY=your-key python scripts/test_gemini_real.py
"""

import asyncio
import os
import sys

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.ai_router import AIRouter
from agents.general.general_agent import GeneralAgent


async def test_gemini_classification():
    """Test that Gemini can classify an email correctly."""
    router = AIRouter()

    # Simulate an email
    test_email = {
        "from": "john@example.com",
        "subject": "Interested in your services",
        "body": (
            "Hi, I saw your website and I'm interested in learning more "
            "about your consulting services. Can you send me your pricing?"
        ),
        "date": "2024-01-15",
    }

    agent = GeneralAgent()
    system_prompt = agent.get_system_prompt("trial")
    user_message = agent.format_email_summary(test_email)
    user_message += "\n\nDecide: AUTO_REPLY, DRAFT_REPLY, LABEL_ARCHIVE, SCHEDULE_FOLLOWUP, or ESCALATE"
    user_message += "\nACTION: <action>\nREPLY: <reply text>\nREASON: <reason>"

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: GEMINI_API_KEY env var not set")
        sys.exit(1)

    model = router._get_model("gemini", "trial")

    result = await router._call_gemini(
        system_prompt, user_message,
        api_key, model, 512, 0.3,
    )

    print("Provider:", result["provider"])
    print("Model:", result["model"])
    print("Response:", result["content"][:500])

    assert result["provider"] == "gemini"
    assert len(result["content"]) > 10
    print("\nGemini classification test PASSED")


async def test_gemini_all_categories():
    """Test Gemini with different email types."""
    router = AIRouter()
    api_key = os.environ["GEMINI_API_KEY"]
    model = router._get_model("gemini", "trial")

    categories = [
        {"subject": "Invoice #123", "body": "Please find attached invoice for $500."},
        {"subject": "Meeting tomorrow", "body": "Can we schedule a call for 3pm?"},
        {"subject": "URGENT: Server down", "body": "Production server is not responding!"},
        {"subject": "Newsletter - March 2024", "body": "Here are this month's updates..."},
    ]

    print("\nMulti-category classification:")
    for cat in categories:
        result = await router._call_gemini(
            "Classify this email as: BUSINESS, URGENT, NEWSLETTER, or PERSONAL. Respond with just the category.",
            f"Subject: {cat['subject']}\nBody: {cat['body']}",
            api_key, model, 50, 0.1,
        )
        print(f"  {cat['subject']} -> {result['content'].strip()}")

    print("\nGemini multi-category test PASSED")


async def test_gemini_action_parsing():
    """Test that Gemini returns parseable ACTION format."""
    router = AIRouter()
    api_key = os.environ["GEMINI_API_KEY"]
    model = router._get_model("gemini", "trial")

    system = (
        "You are an email assistant. For each email, respond in this exact format:\n"
        "ACTION: <one of AUTO_REPLY, DRAFT_REPLY, LABEL_ARCHIVE, ESCALATE>\n"
        "REPLY: <reply text if applicable>\n"
        "REASON: <brief reason>"
    )
    user = (
        "From: angry_customer@example.com\n"
        "Subject: This is unacceptable!\n"
        "Body: I've been waiting 2 weeks for my order. I want a full refund immediately."
    )

    result = await router._call_gemini(system, user, api_key, model, 256, 0.3)

    print("\nAction parsing test:")
    print(f"  Response: {result['content'][:300]}")

    # Check the response contains ACTION:
    content = result["content"]
    has_action = "ACTION:" in content
    print(f"  Contains ACTION: {has_action}")
    assert has_action, "Response should contain ACTION: marker"

    print("\nGemini action parsing test PASSED")


async def main():
    print("=" * 60)
    print("GEMINI REAL INTEGRATION TESTS")
    print("=" * 60)
    await test_gemini_classification()
    await test_gemini_all_categories()
    await test_gemini_action_parsing()
    print("\n" + "=" * 60)
    print("ALL GEMINI TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
