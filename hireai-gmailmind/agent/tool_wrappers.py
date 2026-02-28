"""Safety-guarded tool wrappers for the OpenAI Agents SDK.

Every tool that the GmailMind agent can invoke is defined here as a
plain ``async`` function wrapped with ``SafetyGuard.guard()`` so that
hard safety rules are enforced *before* the real tool executes.

These wrappers bridge the gap between the Agents SDK ``FunctionTool``
interface (JSON-serialisable params in, JSON-serialisable result out)
and the concrete tool implementations in ``tools/``.

The Gmail and Calendar services are resolved at call time from a
module-level ``services`` dict that the reasoning loop populates once
OAuth credentials are available.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from agents import function_tool

from agent.safety_guard import safety_guard
from memory.short_term import session_memory
from tools import gmail_tools, calendar_tools, crm_tools, alert_tools

logger = logging.getLogger(__name__)

# Populated by the reasoning loop after OAuth authentication.
services: dict[str, Any] = {
    "gmail": None,
    "calendar": None,
}


def _svc(name: str) -> Any:
    """Retrieve a Google API service, raising if not initialised."""
    svc = services.get(name)
    if svc is None:
        raise RuntimeError(
            f"Google {name} service not initialised. "
            f"Call set_services() before running the agent."
        )
    return svc


def set_services(gmail_service: Any, calendar_service: Any = None) -> None:
    """Inject authenticated Google API service objects.

    Args:
        gmail_service: Authenticated Gmail API Resource.
        calendar_service: Authenticated Calendar API Resource (optional).
    """
    services["gmail"] = gmail_service
    services["calendar"] = calendar_service
    logger.info("tool_wrappers: Services injected (gmail=%s, calendar=%s).",
                bool(gmail_service), bool(calendar_service))


def _log(tool: str, desc: str, **extra: Any) -> None:
    """Record an action in short-term memory."""
    session_memory.log_action(tool, desc, **extra)


# ===========================================================================
# Gmail tools (1-6)
# ===========================================================================


@function_tool
def read_emails(
    max_results: int = 10,
    filter: str = "is:unread",
    include_thread: bool = False,
) -> str:
    """Fetch emails from the user's Gmail inbox.

    Args:
        max_results: Maximum number of emails to return.
        filter: Gmail search filter (e.g. 'is:unread', 'in:inbox').
        include_thread: If True, also fetch the full thread for each email.

    Returns:
        JSON array of email objects.
    """
    safety_guard.guard("read_emails", {
        "max_results": max_results, "filter": filter,
    })
    result = gmail_tools.read_emails(
        _svc("gmail"), max_results=max_results,
        filter=filter, include_thread=include_thread,
    )
    _log("read_emails", f"Fetched {len(result)} emails (filter={filter})")
    return json.dumps([e.model_dump(mode="json") for e in result])


@function_tool
def send_email(
    to: str,
    subject: str,
    body: str,
    reply_to_thread_id: str = "",
) -> str:
    """Send a new email via Gmail.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
        reply_to_thread_id: Optional thread ID to send into an existing thread.

    Returns:
        JSON with message_id, thread_id, and status.
    """
    safety_guard.guard("send_email", {
        "to": to, "subject": subject, "body": body,
    })
    result = gmail_tools.send_email(
        _svc("gmail"), to=to, subject=subject, body=body,
        reply_to_thread_id=reply_to_thread_id or None,
    )
    _log("send_email", f"Sent email to {to}: {subject}")
    return result.model_dump_json()


@function_tool
def reply_to_email(
    thread_id: str,
    body: str,
    email_context: str = "{}",
) -> str:
    """Reply to an existing email thread.

    Args:
        thread_id: The Gmail thread ID to reply to.
        body: Plain-text reply body.
        email_context: JSON string of original email data (for spam check).

    Returns:
        JSON with message_id, thread_id, and status.
    """
    ctx = json.loads(email_context) if email_context else {}
    safety_guard.guard("reply_to_email", {
        "thread_id": thread_id, "body": body, "email_context": ctx,
    })
    result = gmail_tools.reply_to_email(
        _svc("gmail"), thread_id=thread_id, body=body,
    )
    _log("reply_to_email", f"Replied to thread {thread_id}")
    return result.model_dump_json()


@function_tool
def label_email(
    email_id: str,
    labels: str,
    archive: bool = False,
) -> str:
    """Add labels to an email and optionally archive it.

    Args:
        email_id: The Gmail message ID.
        labels: Comma-separated label IDs to add.
        archive: If true, remove the email from inbox.

    Returns:
        JSON with labelling result.
    """
    label_list = [l.strip() for l in labels.split(",") if l.strip()]
    safety_guard.guard("label_email", {
        "email_id": email_id, "labels": label_list, "archive": archive,
    })
    result = gmail_tools.label_email(
        _svc("gmail"), email_id=email_id, labels=label_list, archive=archive,
    )
    _log("label_email", f"Labeled {email_id} with {label_list}, archive={archive}")
    return result.model_dump_json()


@function_tool
def search_emails(query: str, max_results: int = 10) -> str:
    """Search Gmail using a query string (same syntax as Gmail search box).

    Args:
        query: Gmail search query (e.g. 'from:alice subject:meeting').
        max_results: Maximum number of results.

    Returns:
        JSON array of matching email objects.
    """
    safety_guard.guard("search_emails", {"query": query})
    result = gmail_tools.search_emails(
        _svc("gmail"), query=query, max_results=max_results,
    )
    _log("search_emails", f"Searched '{query}' — {len(result)} results")
    return json.dumps([e.model_dump(mode="json") for e in result])


@function_tool
def create_draft(to: str, subject: str, body: str) -> str:
    """Create a draft email for the user to review before sending.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.

    Returns:
        JSON with draft_id, message_id, and status.
    """
    safety_guard.guard("create_draft", {
        "to": to, "subject": subject, "body": body,
    })
    result = gmail_tools.create_draft(
        _svc("gmail"), to=to, subject=subject, body=body,
    )
    _log("create_draft", f"Created draft to {to}: {subject}")
    return result.model_dump_json()


# ===========================================================================
# Calendar tools (7-9)
# ===========================================================================


@function_tool
def check_calendar_availability(
    date_range_start: str,
    date_range_end: str,
    slot_duration_minutes: int = 30,
) -> str:
    """Check Google Calendar for available time slots in a date range.

    Args:
        date_range_start: ISO-format start datetime (UTC).
        date_range_end: ISO-format end datetime (UTC).
        slot_duration_minutes: Minimum slot length in minutes.

    Returns:
        JSON array of free slot objects.
    """
    safety_guard.guard("check_calendar_availability", {
        "date_range_start": date_range_start,
        "date_range_end": date_range_end,
    })
    start = datetime.fromisoformat(date_range_start)
    end = datetime.fromisoformat(date_range_end)
    result = calendar_tools.check_calendar_availability(
        _svc("calendar"), start, end, slot_duration_minutes,
    )
    _log("check_calendar_availability",
         f"Checked availability {date_range_start} to {date_range_end}")
    return json.dumps([s.model_dump(mode="json") for s in result])


@function_tool
def create_calendar_event(
    title: str,
    start_time: str,
    end_time: str,
    attendees: str = "",
    description: str = "",
) -> str:
    """Create a new event on Google Calendar.

    Args:
        title: Event title.
        start_time: ISO-format start datetime (UTC).
        end_time: ISO-format end datetime (UTC).
        attendees: Comma-separated attendee email addresses.
        description: Event description.

    Returns:
        JSON with event_id, html_link, and status.
    """
    safety_guard.guard("create_calendar_event", {
        "title": title, "attendees": attendees,
    })
    att_list = [a.strip() for a in attendees.split(",") if a.strip()] if attendees else None
    result = calendar_tools.create_calendar_event(
        _svc("calendar"),
        title=title,
        start_time=datetime.fromisoformat(start_time),
        end_time=datetime.fromisoformat(end_time),
        attendees=att_list,
        description=description,
    )
    _log("create_calendar_event", f"Created event: {title}")
    return result.model_dump_json()


@function_tool
def schedule_followup(
    email_id: str,
    follow_up_after_hours: float,
    note: str = "",
    sender_email: str = "",
) -> str:
    """Schedule a follow-up reminder for an email.

    The reminder is saved to the database. The background scheduler will
    trigger the follow-up action when the due time arrives.

    Args:
        email_id: Gmail message ID.
        follow_up_after_hours: Hours from now until the follow-up is due.
        note: Reminder note.
        sender_email: Sender's email address.

    Returns:
        JSON with follow_up_id, due_time, and success status.
    """
    safety_guard.guard("schedule_followup", {
        "email_id": email_id,
        "follow_up_after_hours": follow_up_after_hours,
    })
    result = calendar_tools.schedule_followup(
        email_id=email_id,
        follow_up_after_hours=follow_up_after_hours,
        note=note,
        sender_email=sender_email,
    )
    _log("schedule_followup", f"Follow-up scheduled for {email_id} in {follow_up_after_hours}h")
    return result.model_dump_json()


# ===========================================================================
# CRM tools (10-11)
# ===========================================================================


@function_tool
def get_crm_contact(email: str) -> str:
    """Look up a contact by email in the CRM (HubSpot or local DB).

    Args:
        email: Contact email address.

    Returns:
        JSON contact profile or "null" if not found.
    """
    safety_guard.guard("get_crm_contact", {"email": email})
    result = crm_tools.get_crm_contact(email)
    _log("get_crm_contact", f"Looked up CRM contact: {email}")
    if result is None:
        return "null"
    return result.model_dump_json()


@function_tool
def update_crm(email: str, action: str, data: str = "{}") -> str:
    """Update a contact record in the CRM.

    Args:
        email: Contact email address.
        action: Action description (e.g. 'tag_updated', 'note_added').
        data: JSON string of key-value pairs to update.

    Returns:
        JSON with success status, source, and reason.
    """
    parsed_data = json.loads(data) if data else {}
    safety_guard.guard("update_crm", {
        "email": email, "action": action, "data": parsed_data,
    })
    result = crm_tools.update_crm(email, action, parsed_data)
    _log("update_crm", f"Updated CRM for {email}: {action}")
    return result.model_dump_json()


# ===========================================================================
# Alert tools (12)
# ===========================================================================


@function_tool
def send_escalation_alert(
    channel: str,
    message: str,
    urgency: str = "normal",
) -> str:
    """Send an escalation alert to a human operator via Slack or WhatsApp.

    Args:
        channel: Target channel — "slack" or "whatsapp".
        message: Alert message body.
        urgency: Urgency level — "low", "normal", "high", "critical".

    Returns:
        JSON with success status and channel.
    """
    safety_guard.guard("send_escalation_alert", {
        "channel": channel, "message": message, "urgency": urgency,
    })
    result = alert_tools.send_escalation_alert(channel, message, urgency)
    _log("send_escalation_alert", f"Escalation via {channel} ({urgency})")
    return result.model_dump_json()


# ===========================================================================
# Collect all tools for the agent
# ===========================================================================

ALL_TOOLS = [
    read_emails,
    send_email,
    reply_to_email,
    label_email,
    search_emails,
    create_draft,
    check_calendar_availability,
    create_calendar_event,
    schedule_followup,
    get_crm_contact,
    update_crm,
    send_escalation_alert,
]
