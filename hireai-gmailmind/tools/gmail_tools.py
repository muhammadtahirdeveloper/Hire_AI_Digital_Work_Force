"""Gmail tools for the GmailMind agent.

Provides six core operations against the Gmail API:
  1. read_emails     — Fetch inbox messages with optional filters
  2. send_email      — Send a new email (optionally into an existing thread)
  3. reply_to_email  — Reply to a specific thread
  4. label_email     — Add/remove labels and optionally archive
  5. search_emails   — Search Gmail with a query string
  6. create_draft    — Create a draft email

All functions expect a pre-authenticated ``googleapiclient.discovery.Resource``
(Gmail service) built from OAuth2 credentials managed in config/credentials.py.
"""

import base64
import logging
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime
from typing import Optional

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from models.gmail_models import (
    DraftResponse,
    Email,
    EmailAddress,
    LabelResult,
    SendEmailResponse,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_date(raw: str):
    """Parse an RFC 2822 date string into a datetime, or return None."""
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw)
    except Exception:
        return None


def _parse_email_address(raw: str) -> EmailAddress:
    """Parse a 'Display Name <email@example.com>' string into an EmailAddress.

    Args:
        raw: Raw header value, e.g. 'John Doe <john@example.com>' or 'john@example.com'.

    Returns:
        An EmailAddress instance.
    """
    if "<" in raw and ">" in raw:
        name = raw[: raw.index("<")].strip().strip('"')
        email = raw[raw.index("<") + 1 : raw.index(">")].strip()
        return EmailAddress(email=email, name=name or None)
    return EmailAddress(email=raw.strip())


def _get_header(headers: list[dict], name: str) -> str:
    """Extract a header value by name from the Gmail message headers list.

    Args:
        headers: List of {'name': ..., 'value': ...} dicts from the API.
        name: Header name to look up (case-insensitive).

    Returns:
        The header value, or an empty string if not found.
    """
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def _decode_body(payload: dict) -> str:
    """Recursively extract plain-text body from a Gmail message payload.

    Args:
        payload: The 'payload' dict from a Gmail message resource.

    Returns:
        Decoded plain-text body string.
    """
    # Direct body data
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    # Multipart — recurse into parts
    for part in payload.get("parts", []):
        text = _decode_body(part)
        if text:
            return text

    return ""


def _message_to_email(msg: dict) -> Email:
    """Convert a raw Gmail API message resource into an Email model.

    Args:
        msg: Full message resource from the Gmail API.

    Returns:
        A populated Email Pydantic model.
    """
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])

    sender_raw = _get_header(headers, "From")
    to_raw = _get_header(headers, "To")
    to_list = [_parse_email_address(addr) for addr in to_raw.split(",") if addr.strip()] if to_raw else []

    label_ids = msg.get("labelIds", [])
    is_read = "UNREAD" not in label_ids

    return Email(
        id=msg["id"],
        thread_id=msg.get("threadId", ""),
        subject=_get_header(headers, "Subject"),
        sender=_parse_email_address(sender_raw) if sender_raw else EmailAddress(email="unknown"),
        to=to_list,
        date=_parse_date(_get_header(headers, "Date")),
        snippet=msg.get("snippet", ""),
        body=_decode_body(payload),
        labels=label_ids,
        is_read=is_read,
    )


# ---------------------------------------------------------------------------
# 1. read_emails
# ---------------------------------------------------------------------------

def read_emails(
    service: Resource,
    max_results: int = 10,
    filter: Optional[str] = None,
    include_thread: bool = False,
) -> list[Email]:
    """Fetch emails from the user's Gmail inbox.

    Args:
        service: Authenticated Gmail API service resource.
        max_results: Maximum number of emails to return (default 10).
        filter: Optional Gmail search filter (e.g. 'is:unread').
        include_thread: If True, fetch the full thread for each message.

    Returns:
        A list of Email models.

    Raises:
        HttpError: If the Gmail API request fails.
    """
    logger.info(
        "read_emails called — max_results=%d, filter=%s, include_thread=%s",
        max_results,
        filter,
        include_thread,
    )

    try:
        query = filter or "in:inbox"
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

        messages = response.get("messages", [])
        if not messages:
            logger.info("read_emails: No messages matched the query.")
            return []

        emails: list[Email] = []
        for msg_ref in messages:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_ref["id"], format="full")
                .execute()
            )
            email = _message_to_email(msg)

            if include_thread and email.thread_id:
                thread = (
                    service.users()
                    .threads()
                    .get(userId="me", id=email.thread_id, format="full")
                    .execute()
                )
                thread_msgs = thread.get("messages", [])
                logger.info(
                    "read_emails: Fetched thread %s with %d messages.",
                    email.thread_id,
                    len(thread_msgs),
                )

            emails.append(email)

        logger.info("read_emails: Returning %d emails.", len(emails))
        return emails

    except HttpError as exc:
        logger.error("read_emails failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# 2. send_email
# ---------------------------------------------------------------------------

def send_email(
    service: Resource,
    to: str,
    subject: str,
    body: str,
    reply_to_thread_id: Optional[str] = None,
) -> SendEmailResponse:
    """Send a new email via Gmail.

    Args:
        service: Authenticated Gmail API service resource.
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
        reply_to_thread_id: Optional thread ID to send this message into.

    Returns:
        A SendEmailResponse with the sent message and thread IDs.

    Raises:
        HttpError: If the Gmail API request fails.
    """
    logger.info(
        "send_email called — to=%s, subject=%s, thread=%s",
        to,
        subject,
        reply_to_thread_id,
    )

    try:
        mime_message = MIMEText(body)
        mime_message["to"] = to
        mime_message["subject"] = subject

        raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")

        send_body: dict = {"raw": raw}
        if reply_to_thread_id:
            send_body["threadId"] = reply_to_thread_id

        sent = (
            service.users()
            .messages()
            .send(userId="me", body=send_body)
            .execute()
        )

        logger.info("send_email: Message sent — id=%s, threadId=%s", sent["id"], sent.get("threadId"))

        return SendEmailResponse(
            message_id=sent["id"],
            thread_id=sent.get("threadId", ""),
            status="sent",
        )

    except HttpError as exc:
        logger.error("send_email failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# 3. reply_to_email
# ---------------------------------------------------------------------------

def reply_to_email(
    service: Resource,
    thread_id: str,
    body: str,
) -> SendEmailResponse:
    """Reply to an existing email thread.

    Fetches the latest message in the thread to determine the recipient and
    subject, then sends a reply into the same thread.

    Args:
        service: Authenticated Gmail API service resource.
        thread_id: The Gmail thread ID to reply to.
        body: Plain-text reply body.

    Returns:
        A SendEmailResponse with the sent reply details.

    Raises:
        HttpError: If the Gmail API request fails.
        ValueError: If the thread contains no messages.
    """
    logger.info("reply_to_email called — thread_id=%s", thread_id)

    try:
        thread = (
            service.users()
            .threads()
            .get(userId="me", id=thread_id, format="full")
            .execute()
        )

        thread_messages = thread.get("messages", [])
        if not thread_messages:
            raise ValueError(f"Thread {thread_id} contains no messages.")

        last_msg = thread_messages[-1]
        headers = last_msg.get("payload", {}).get("headers", [])

        original_sender = _get_header(headers, "From")
        original_subject = _get_header(headers, "Subject")
        message_id_header = _get_header(headers, "Message-Id")

        reply_subject = original_subject if original_subject.lower().startswith("re:") else f"Re: {original_subject}"

        mime_message = MIMEText(body)
        mime_message["to"] = original_sender
        mime_message["subject"] = reply_subject
        if message_id_header:
            mime_message["In-Reply-To"] = message_id_header
            mime_message["References"] = message_id_header

        raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")

        sent = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw, "threadId": thread_id})
            .execute()
        )

        logger.info(
            "reply_to_email: Reply sent — id=%s, threadId=%s",
            sent["id"],
            sent.get("threadId"),
        )

        return SendEmailResponse(
            message_id=sent["id"],
            thread_id=sent.get("threadId", ""),
            status="sent",
        )

    except HttpError as exc:
        logger.error("reply_to_email failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# 4. label_email
# ---------------------------------------------------------------------------

def label_email(
    service: Resource,
    email_id: str,
    labels: list[str],
    archive: bool = False,
) -> LabelResult:
    """Add labels to an email and optionally archive it.

    Args:
        service: Authenticated Gmail API service resource.
        email_id: The Gmail message ID to modify.
        labels: List of label IDs to add to the message.
        archive: If True, remove the INBOX label (archive the message).

    Returns:
        A LabelResult indicating what was changed.

    Raises:
        HttpError: If the Gmail API request fails.
    """
    logger.info(
        "label_email called — email_id=%s, labels=%s, archive=%s",
        email_id,
        labels,
        archive,
    )

    try:
        modify_body: dict = {
            "addLabelIds": labels,
            "removeLabelIds": [],
        }

        if archive:
            modify_body["removeLabelIds"].append("INBOX")

        service.users().messages().modify(
            userId="me",
            id=email_id,
            body=modify_body,
        ).execute()

        logger.info(
            "label_email: Modified email %s — added=%s, removed=%s, archived=%s",
            email_id,
            labels,
            modify_body["removeLabelIds"],
            archive,
        )

        return LabelResult(
            email_id=email_id,
            labels_added=labels,
            labels_removed=modify_body["removeLabelIds"],
            archived=archive,
            success=True,
        )

    except HttpError as exc:
        logger.error("label_email failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# 5. search_emails
# ---------------------------------------------------------------------------

def search_emails(
    service: Resource,
    query: str,
    max_results: int = 10,
) -> list[Email]:
    """Search Gmail using a query string.

    Supports the same query syntax as the Gmail search box
    (e.g. 'from:alice subject:meeting after:2025/01/01').

    Args:
        service: Authenticated Gmail API service resource.
        query: Gmail search query string.
        max_results: Maximum number of results to return (default 10).

    Returns:
        A list of Email models matching the query.

    Raises:
        HttpError: If the Gmail API request fails.
    """
    logger.info("search_emails called — query=%s, max_results=%d", query, max_results)

    try:
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

        messages = response.get("messages", [])
        if not messages:
            logger.info("search_emails: No results for query '%s'.", query)
            return []

        emails: list[Email] = []
        for msg_ref in messages:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_ref["id"], format="full")
                .execute()
            )
            emails.append(_message_to_email(msg))

        logger.info("search_emails: Returning %d results.", len(emails))
        return emails

    except HttpError as exc:
        logger.error("search_emails failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# 6. create_draft
# ---------------------------------------------------------------------------

def create_draft(
    service: Resource,
    to: str,
    subject: str,
    body: str,
) -> DraftResponse:
    """Create a draft email in Gmail.

    Args:
        service: Authenticated Gmail API service resource.
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.

    Returns:
        A DraftResponse with the draft and message IDs.

    Raises:
        HttpError: If the Gmail API request fails.
    """
    logger.info("create_draft called — to=%s, subject=%s", to, subject)

    try:
        mime_message = MIMEText(body)
        mime_message["to"] = to
        mime_message["subject"] = subject

        raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")

        draft = (
            service.users()
            .drafts()
            .create(userId="me", body={"message": {"raw": raw}})
            .execute()
        )

        draft_id = draft["id"]
        message_id = draft.get("message", {}).get("id", "")

        logger.info(
            "create_draft: Draft created — draft_id=%s, message_id=%s",
            draft_id,
            message_id,
        )

        return DraftResponse(
            draft_id=draft_id,
            message_id=message_id,
            status="created",
        )

    except HttpError as exc:
        logger.error("create_draft failed: %s", exc)
        raise
