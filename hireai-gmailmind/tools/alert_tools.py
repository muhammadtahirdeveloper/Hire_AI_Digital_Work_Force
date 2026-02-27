"""Escalation alert tools for the GmailMind agent.

Provides one main function:
  send_escalation_alert — Notify a human via Slack webhook or WhatsApp (Twilio).

Both channels are optional. If the required credentials are not configured
the function returns a clear failure with a descriptive reason instead of
crashing.
"""

import logging

import httpx

from config.settings import (
    ESCALATION_WHATSAPP_TO,
    SLACK_WEBHOOK_URL,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM,
)
from models.tool_models import EscalationAlertResponse

logger = logging.getLogger(__name__)


def _slack_configured() -> bool:
    """Return True if the Slack webhook URL is set."""
    return bool(SLACK_WEBHOOK_URL)


def _twilio_configured() -> bool:
    """Return True if all Twilio WhatsApp credentials are present."""
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM)


# ===========================================================================
# Main entry point
# ===========================================================================


def send_escalation_alert(
    channel: str,
    message: str,
    urgency: str = "normal",
) -> EscalationAlertResponse:
    """Send an escalation alert to a human operator.

    Args:
        channel: Target channel — ``"slack"`` or ``"whatsapp"``.
        message: The alert message body.
        urgency: Urgency level — ``"low"``, ``"normal"``, ``"high"``, ``"critical"``.
                 Used to format the message prefix.

    Returns:
        An EscalationAlertResponse indicating success or failure.
    """
    logger.info(
        "send_escalation_alert: channel=%s, urgency=%s, message_len=%d",
        channel,
        urgency,
        len(message),
    )

    channel_lower = channel.strip().lower()

    if channel_lower == "slack":
        return _send_slack_alert(message, urgency)
    elif channel_lower == "whatsapp":
        return _send_whatsapp_alert(message, urgency)
    else:
        reason = f"Unsupported channel: {channel!r}. Use 'slack' or 'whatsapp'."
        logger.warning("send_escalation_alert: %s", reason)
        return EscalationAlertResponse(
            success=False, channel=channel, reason=reason
        )


# ===========================================================================
# Slack
# ===========================================================================

_URGENCY_EMOJI = {
    "low": ":large_blue_circle:",
    "normal": ":white_circle:",
    "high": ":warning:",
    "critical": ":rotating_light:",
}


def _send_slack_alert(message: str, urgency: str) -> EscalationAlertResponse:
    """Post an alert to a Slack channel via incoming webhook.

    Args:
        message: Alert body.
        urgency: Urgency level for emoji prefix.

    Returns:
        EscalationAlertResponse.
    """
    if not _slack_configured():
        reason = "Slack integration not configured — SLACK_WEBHOOK_URL is empty."
        logger.warning("_send_slack_alert: %s", reason)
        return EscalationAlertResponse(success=False, channel="slack", reason=reason)

    emoji = _URGENCY_EMOJI.get(urgency, ":white_circle:")
    formatted = f"{emoji} *GmailMind Escalation [{urgency.upper()}]*\n{message}"

    logger.info("_send_slack_alert: Posting to Slack webhook.")

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                SLACK_WEBHOOK_URL,
                json={"text": formatted},
            )
            resp.raise_for_status()

        logger.info("_send_slack_alert: Slack alert sent successfully.")
        return EscalationAlertResponse(success=True, channel="slack")

    except httpx.HTTPStatusError as exc:
        reason = f"Slack webhook error {exc.response.status_code}: {exc.response.text}"
        logger.error("_send_slack_alert: %s", reason)
        return EscalationAlertResponse(success=False, channel="slack", reason=reason)
    except Exception as exc:
        reason = f"Slack alert failed: {exc}"
        logger.error("_send_slack_alert: %s", reason)
        return EscalationAlertResponse(success=False, channel="slack", reason=reason)


# ===========================================================================
# WhatsApp (Twilio)
# ===========================================================================


def _send_whatsapp_alert(message: str, urgency: str) -> EscalationAlertResponse:
    """Send a WhatsApp message via the Twilio API.

    Args:
        message: Alert body.
        urgency: Urgency level for message prefix.

    Returns:
        EscalationAlertResponse.
    """
    if not _twilio_configured():
        reason = (
            "Twilio WhatsApp integration not configured — "
            "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, or TWILIO_WHATSAPP_FROM is empty."
        )
        logger.warning("_send_whatsapp_alert: %s", reason)
        return EscalationAlertResponse(success=False, channel="whatsapp", reason=reason)

    if not ESCALATION_WHATSAPP_TO:
        reason = "ESCALATION_WHATSAPP_TO is not set — no recipient for WhatsApp alert."
        logger.warning("_send_whatsapp_alert: %s", reason)
        return EscalationAlertResponse(success=False, channel="whatsapp", reason=reason)

    formatted = f"[GmailMind {urgency.upper()}] {message}"

    logger.info(
        "_send_whatsapp_alert: Sending WhatsApp via Twilio to %s.",
        ESCALATION_WHATSAPP_TO,
    )

    try:
        url = (
            f"https://api.twilio.com/2010-04-01"
            f"/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
        )

        with httpx.Client(timeout=15) as client:
            resp = client.post(
                url,
                data={
                    "From": TWILIO_WHATSAPP_FROM,
                    "To": ESCALATION_WHATSAPP_TO,
                    "Body": formatted,
                },
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            )
            resp.raise_for_status()

        logger.info("_send_whatsapp_alert: WhatsApp alert sent successfully.")
        return EscalationAlertResponse(success=True, channel="whatsapp")

    except httpx.HTTPStatusError as exc:
        reason = f"Twilio API error {exc.response.status_code}: {exc.response.text}"
        logger.error("_send_whatsapp_alert: %s", reason)
        return EscalationAlertResponse(success=False, channel="whatsapp", reason=reason)
    except Exception as exc:
        reason = f"WhatsApp alert failed: {exc}"
        logger.error("_send_whatsapp_alert: %s", reason)
        return EscalationAlertResponse(success=False, channel="whatsapp", reason=reason)
