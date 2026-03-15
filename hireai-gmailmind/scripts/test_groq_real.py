"""
Real integration test: Groq processes an email.
Requires: GROQ_API_KEY env var set.

Usage:
    GROQ_API_KEY=your-key python scripts/test_groq_real.py
"""

import asyncio
import os
import sys

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.ai_router import AIRouter
from agents.general.general_agent import GeneralAgent


async def test_groq_classification():
    """Test that Groq can classify an email correctly."""
    router = AIRouter()

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

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        print("ERROR: GROQ_API_KEY env var not set")
        sys.exit(1)

    model = router._get_model("groq", "trial")

    result = await router._call_groq(
        system_prompt, user_message,
        api_key, model, 512, 0.3,
    )

    print("Provider:", result["provider"])
    print("Model:", result["model"])
    print("Response:", result["content"][:500])

    assert result["provider"] == "groq"
    assert len(result["content"]) > 10
    print("\nGroq classification test PASSED")


async def test_groq_all_categories():
    """Test Groq with different email types."""
    router = AIRouter()
    api_key = os.environ["GROQ_API_KEY"]
    model = router._get_model("groq", "trial")

    categories = [
        {"subject": "Invoice #123", "body": "Please find attached invoice for $500."},
        {"subject": "Meeting tomorrow", "body": "Can we schedule a call for 3pm?"},
        {"subject": "URGENT: Server down", "body": "Production server is not responding!"},
        {"subject": "Newsletter - March 2024", "body": "Here are this month's updates..."},
    ]

    print("\nMulti-category classification:")
    for cat in categories:
        result = await router._call_groq(
            "Classify this email as: BUSINESS, URGENT, NEWSLETTER, or PERSONAL. Respond with just the category.",
            f"Subject: {cat['subject']}\nBody: {cat['body']}",
            api_key, model, 50, 0.1,
        )
        print(f"  {cat['subject']} -> {result['content'].strip()}")

    print("\nGroq multi-category test PASSED")


async def test_groq_action_parsing():
    """Test that Groq returns parseable ACTION format."""
    router = AIRouter()
    api_key = os.environ["GROQ_API_KEY"]
    model = router._get_model("groq", "trial")

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

    result = await router._call_groq(system, user, api_key, model, 256, 0.3)

    print("\nAction parsing test:")
    print(f"  Response: {result['content'][:300]}")

    content = result["content"]
    has_action = "ACTION:" in content
    print(f"  Contains ACTION: {has_action}")
    assert has_action, "Response should contain ACTION: marker"

    print("\nGroq action parsing test PASSED")


async def test_groq_retry_mechanism():
    """Verify the retry wrapper works (calls succeed without rate limit)."""
    router = AIRouter()
    api_key = os.environ["GROQ_API_KEY"]
    model = router._get_model("groq", "trial")

    result = await router._call_groq_with_retry(
        "Say hello.", "Hello!",
        api_key, model, 20, 0.1,
    )

    assert result["provider"] == "groq"
    assert len(result["content"]) > 0
    print("\nGroq retry mechanism test PASSED")


async def main():
    print("=" * 60)
    print("GROQ REAL INTEGRATION TESTS")
    print("=" * 60)
    await test_groq_classification()
    await test_groq_all_categories()
    await test_groq_action_parsing()
    await test_groq_retry_mechanism()
    print("\n" + "=" * 60)
    print("ALL GROQ TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
