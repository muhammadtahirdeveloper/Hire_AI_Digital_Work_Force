"""WhatsApp messaging tools via Twilio API.

Sends WhatsApp messages, alerts, and formatted reports to users.
Falls back gracefully if Twilio is not configured.

Usage::

    from tools.whatsapp_tools import send_whatsapp_message, send_whatsapp_alert

    send_whatsapp_message(to_phone="+923001234567", message="Hello!")
    send_whatsapp_alert(to_phone="+923001234567", message="Server down", urgency="critical")
"""

import logging
from datetime import datetime, timezone

from config.settings import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Core message sender
# ============================================================================


def send_whatsapp_message(to_phone: str, message: str) -> bool:
    """Send a WhatsApp message via Twilio.

    Args:
        to_phone: Recipient phone number (e.g. '+923001234567').
                  Will be prefixed with 'whatsapp:' if not already.
        message: The message text to send.

    Returns:
        True on success, False on failure or if Twilio is not configured.
    """
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM]):
        logger.warning(
            "WhatsApp: Twilio not configured (missing SID/TOKEN/FROM). "
            "Message not sent."
        )
        return False

    # Ensure whatsapp: prefix
    if not to_phone.startswith("whatsapp:"):
        to_phone = f"whatsapp:{to_phone}"

    whatsapp_from = TWILIO_WHATSAPP_FROM
    if not whatsapp_from.startswith("whatsapp:"):
        whatsapp_from = f"whatsapp:{whatsapp_from}"

    try:
        import httpx

        url = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{TWILIO_ACCOUNT_SID}/Messages.json"
        )

        response = httpx.post(
            url,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            data={
                "From": whatsapp_from,
                "To": to_phone,
                "Body": message,
            },
            timeout=30,
        )
        response.raise_for_status()

        sid = response.json().get("sid", "unknown")
        logger.info("WhatsApp: Message sent to %s (SID: %s)", to_phone, sid)
        return True

    except Exception as exc:
        logger.error("WhatsApp: Failed to send message to %s: %s", to_phone, exc)
        return False


# ============================================================================
# Alert sender
# ============================================================================

_URGENCY_ICONS = {
    "critical": "\U0001f6a8",  # 🚨
    "high": "\u26a0\ufe0f",     # ⚠️
    "medium": "\u2139\ufe0f",   # ℹ️
    "low": "\U0001f4ac",        # 💬
}


def send_whatsapp_alert(
    to_phone: str,
    message: str,
    urgency: str = "medium",
) -> bool:
    """Send a formatted WhatsApp alert with urgency icon.

    Args:
        to_phone: Recipient phone number.
        message: Alert message text.
        urgency: One of 'critical', 'high', 'medium', 'low'.

    Returns:
        True on success, False on failure.
    """
    icon = _URGENCY_ICONS.get(urgency, _URGENCY_ICONS["medium"])
    formatted = f"{icon} GmailMind Alert\n{message}"

    logger.info("WhatsApp: Sending %s alert to %s", urgency, to_phone)
    return send_whatsapp_message(to_phone, formatted)


# ============================================================================
# Report sender
# ============================================================================


def send_whatsapp_report(
    to_phone: str,
    report: dict,
    report_type: str = "daily",
) -> bool:
    """Send a formatted report as a WhatsApp message.

    Args:
        to_phone: Recipient phone number.
        report: Report dict (from ReportGenerator or HRSkills).
        report_type: 'daily' or 'weekly'.

    Returns:
        True on success, False on failure.
    """
    if report_type == "daily":
        message = _format_daily_report(report)
    else:
        message = _format_weekly_hr_report(report)

    logger.info("WhatsApp: Sending %s report to %s", report_type, to_phone)
    return send_whatsapp_message(to_phone, message)


def _format_daily_report(report: dict) -> str:
    """Format a daily report for WhatsApp."""
    date = report.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    msg = (
        "\U0001f4ca GmailMind Daily Report\n"
        f"Date: {date}\n"
        "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"
        "\u2500\u2500\u2500\u2500\u2500\u2500\n"
        f"\U0001f4e7 Emails processed: {report.get('emails_processed', report.get('total_actions', 0))}\n"
        f"\U0001f3f7\ufe0f  Labels applied: {report.get('labeled', 0)}\n"
        f"\U0001f4c1 Archived: {report.get('archived', 0)}\n"
        f"\U0001f6a8 Escalations: {report.get('escalated', 0)}\n"
        "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"
        "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
        "\u2705 Agent running smoothly"
    )

    # Append HR data if present
    if report.get("hr_data"):
        hr = report["hr_data"]
        msg += (
            "\n\n\U0001f464 HR Summary\n"
            f"  New CVs: {hr.get('new_candidates', 0)}\n"
            f"  Interviews: {hr.get('interviews_scheduled', 0)}\n"
            f"  Hires: {hr.get('hires', 0)}"
        )

    return msg


def _format_weekly_hr_report(report: dict) -> str:
    """Format a weekly HR report for WhatsApp."""
    pipeline = report.get("pipeline", {})

    pipeline_flow = (
        f"Applied({pipeline.get('applied', 0)}) \u2192 "
        f"Screened({pipeline.get('screened', 0)}) \u2192 "
        f"Interview({pipeline.get('interview', 0)})"
    )

    msg = (
        "\U0001f4ca HR Weekly Report\n"
        f"Week: {report.get('week_start', 'N/A')[:10]}\n"
        "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"
        "\u2500\u2500\u2500\u2500\u2500\u2500\n"
        f"\U0001f464 New CVs: {report.get('new_candidates', 0)}\n"
        f"\u2b50 Shortlisted: {report.get('shortlisted', 0)}\n"
        f"\U0001f4c5 Interviews: {report.get('interviews_scheduled', 0)}\n"
        f"\u2705 Hired: {report.get('hires', 0)}\n"
        f"\u274c Rejected: {report.get('rejections', 0)}\n"
        "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"
        "\u2500\u2500\u2500\u2500\u2500\u2500\n"
        f"\U0001f4c8 Pipeline: {pipeline_flow}"
    )

    return msg
