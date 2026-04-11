"""Calendar tools for the GmailMind agent.

Provides calendar-related operations:
  1. build_calendar_service       — Build Calendar API service from user credentials
  2. check_calendar_availability  — Query Google Calendar for free slots
  3. get_available_slots          — Higher-level slot finder with working hours + buffer
  4. create_calendar_event        — Create a new event with attendees
  5. cancel_event                 — Cancel / delete a calendar event
  6. list_upcoming_events         — List upcoming events for next N days
  7. detect_meeting_duration      — Infer meeting length from email text
  8. get_user_scheduling_config   — Load user's working hours / blocked days
  9. schedule_followup            — Save a follow-up reminder to DB (Celery picks it up)

All Google Calendar calls require a pre-authenticated
``googleapiclient.discovery.Resource`` built from the same OAuth2 credentials
used for Gmail (with the calendar scope added).
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from config.database import SessionLocal
from config.settings import GOOGLE_CALENDAR_ID
from memory.long_term import create_follow_up
from memory.schemas import FollowUpCreate
from models.tool_models import (
    CalendarEventResponse,
    FollowUpScheduleResponse,
    FreeSlot,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 0. Build Calendar Service
# ---------------------------------------------------------------------------


def build_calendar_service(user_id: str) -> Optional[Resource]:
    """Build an authenticated Google Calendar API service for a user.

    Uses the same OAuth2 credentials stored for Gmail.

    Args:
        user_id: The user identifier.

    Returns:
        A Google Calendar API service resource, or None if unavailable.
    """
    try:
        from memory.long_term import get_user_credentials
        from config.credentials import refresh_credentials
        from googleapiclient.discovery import build

        creds_data = get_user_credentials(user_id)
        if not creds_data:
            logger.warning("build_calendar_service: No credentials for user=%s", user_id)
            return None

        # creds_data is a dict — convert to a Credentials object first
        from config.credentials import build_credentials
        from datetime import datetime as _dt

        expiry = None
        if creds_data.get("expiry"):
            try:
                expiry = _dt.fromisoformat(creds_data["expiry"])
            except (ValueError, TypeError):
                pass

        credentials = build_credentials(
            token=creds_data.get("token", ""),
            refresh_token=creds_data.get("refresh_token", ""),
            token_uri=creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            expiry=expiry,
        )
        credentials = refresh_credentials(credentials, user_id=user_id)
        if not credentials:
            logger.warning("build_calendar_service: Could not refresh credentials for user=%s", user_id)
            return None

        service = build("calendar", "v3", credentials=credentials)
        logger.info("build_calendar_service: Built calendar service for user=%s", user_id)
        return service

    except Exception as exc:
        logger.error("build_calendar_service: Failed for user=%s: %s", user_id, exc)
        return None


# ---------------------------------------------------------------------------
# 1. check_calendar_availability
# ---------------------------------------------------------------------------


def check_calendar_availability(
    service: Resource,
    date_range_start: datetime,
    date_range_end: datetime,
    slot_duration_minutes: int = 30,
) -> list[FreeSlot]:
    """Query Google Calendar freebusy API and return available time slots.

    Args:
        service: Authenticated Google Calendar API service resource.
        date_range_start: Start of the window to check (UTC).
        date_range_end: End of the window to check (UTC).
        slot_duration_minutes: Minimum slot length in minutes (default 30).

    Returns:
        A list of FreeSlot models representing available windows.

    Raises:
        HttpError: If the Calendar API request fails.
    """
    logger.info(
        "check_calendar_availability: %s to %s (min %d min slots)",
        date_range_start.isoformat(),
        date_range_end.isoformat(),
        slot_duration_minutes,
    )

    try:
        body = {
            "timeMin": date_range_start.isoformat(),
            "timeMax": date_range_end.isoformat(),
            "timeZone": "UTC",
            "items": [{"id": GOOGLE_CALENDAR_ID}],
        }

        result = service.freebusy().query(body=body).execute()

        busy_periods = result.get("calendars", {}).get(
            GOOGLE_CALENDAR_ID, {}
        ).get("busy", [])

        logger.info(
            "check_calendar_availability: Found %d busy periods.", len(busy_periods)
        )

        # Build a sorted list of busy (start, end) tuples
        busy = []
        for period in busy_periods:
            b_start = datetime.fromisoformat(period["start"].replace("Z", "+00:00"))
            b_end = datetime.fromisoformat(period["end"].replace("Z", "+00:00"))
            busy.append((b_start, b_end))
        busy.sort(key=lambda x: x[0])

        # Walk the range and collect gaps that are large enough
        free_slots: list[FreeSlot] = []
        cursor = date_range_start

        for b_start, b_end in busy:
            if cursor < b_start:
                gap_minutes = int((b_start - cursor).total_seconds() / 60)
                if gap_minutes >= slot_duration_minutes:
                    free_slots.append(
                        FreeSlot(
                            start=cursor,
                            end=b_start,
                            duration_minutes=gap_minutes,
                        )
                    )
            cursor = max(cursor, b_end)

        # Trailing free time after the last busy block
        if cursor < date_range_end:
            gap_minutes = int((date_range_end - cursor).total_seconds() / 60)
            if gap_minutes >= slot_duration_minutes:
                free_slots.append(
                    FreeSlot(
                        start=cursor,
                        end=date_range_end,
                        duration_minutes=gap_minutes,
                    )
                )

        logger.info(
            "check_calendar_availability: Returning %d free slots.", len(free_slots)
        )
        return free_slots

    except HttpError as exc:
        logger.error("check_calendar_availability failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# 2. create_calendar_event
# ---------------------------------------------------------------------------


def create_calendar_event(
    service: Resource,
    title: str,
    start_time: datetime,
    end_time: datetime,
    attendees: Optional[list[str]] = None,
    description: str = "",
) -> CalendarEventResponse:
    """Create a new event on Google Calendar.

    Args:
        service: Authenticated Google Calendar API service resource.
        title: Event title / summary.
        start_time: Event start time (UTC).
        end_time: Event end time (UTC).
        attendees: Optional list of attendee email addresses.
        description: Optional event description / notes.

    Returns:
        A CalendarEventResponse with the created event ID and link.

    Raises:
        HttpError: If the Calendar API request fails.
    """
    logger.info(
        "create_calendar_event: title=%r, start=%s, end=%s, attendees=%s",
        title,
        start_time.isoformat(),
        end_time.isoformat(),
        attendees,
    )

    try:
        event_body: dict = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "UTC",
            },
        }

        if attendees:
            event_body["attendees"] = [{"email": email} for email in attendees]

        created = (
            service.events()
            .insert(calendarId=GOOGLE_CALENDAR_ID, body=event_body)
            .execute()
        )

        event_id = created.get("id", "")
        html_link = created.get("htmlLink", "")

        logger.info(
            "create_calendar_event: Created event_id=%s, link=%s",
            event_id,
            html_link,
        )

        return CalendarEventResponse(
            event_id=event_id,
            html_link=html_link,
            status=created.get("status", "confirmed"),
        )

    except HttpError as exc:
        logger.error("create_calendar_event failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# 3. get_available_slots (higher-level helper with smart scheduling)
# ---------------------------------------------------------------------------


def get_user_scheduling_config(user_id: str) -> dict[str, Any]:
    """Load user's scheduling preferences from user_agents config.

    Returns a dict with:
        - working_hours: (start_hour, end_hour) tuple
        - timezone_offset: hours offset from UTC
        - blocked_days: list of weekday ints (0=Mon..6=Sun)
        - buffer_minutes: minutes between meetings

    Falls back to sensible defaults if config not set.
    """
    defaults = {
        "working_hours": (9, 17),
        "timezone_offset": 0,
        "blocked_days": [5, 6],  # Saturday, Sunday
        "buffer_minutes": 15,
    }
    try:
        from sqlalchemy import text as sa_text
        db = SessionLocal()
        try:
            row = db.execute(
                sa_text("SELECT config FROM user_agents WHERE user_id = :uid LIMIT 1"),
                {"uid": user_id},
            ).fetchone()
            if row and row[0] and isinstance(row[0], dict):
                cfg = row[0]
                wh_start = int(cfg.get("working_hours_start", 9))
                wh_end = int(cfg.get("working_hours_end", 17))
                tz_offset = int(cfg.get("timezone_offset", 0))
                blocked = cfg.get("blocked_days", [5, 6])
                buffer = int(cfg.get("buffer_minutes", 15))
                if isinstance(blocked, str):
                    blocked = [int(d.strip()) for d in blocked.split(",") if d.strip()]
                return {
                    "working_hours": (wh_start, wh_end),
                    "timezone_offset": tz_offset,
                    "blocked_days": blocked,
                    "buffer_minutes": buffer,
                }
        finally:
            db.close()
    except Exception:
        pass
    return defaults


def get_available_slots(
    service: Resource,
    date_range_start: datetime,
    date_range_end: datetime,
    duration_minutes: int = 30,
    working_hours: tuple[int, int] = (9, 17),
    blocked_days: list[int] | None = None,
    buffer_minutes: int = 15,
    timezone_offset: int = 0,
) -> list[dict[str, Any]]:
    """Find available appointment slots with smart scheduling.

    Respects working hours, blocked days, timezone, and adds buffer time
    between meetings so appointments are never back-to-back.

    Args:
        service: Authenticated Google Calendar API service.
        date_range_start: Start of the search window (UTC).
        date_range_end: End of the search window (UTC).
        duration_minutes: Required slot duration in minutes.
        working_hours: Tuple of (start_hour, end_hour) in user's local time.
        blocked_days: List of weekday ints to skip (0=Mon..6=Sun). Defaults to [5,6].
        buffer_minutes: Minutes of buffer to add between meetings. Default 15.
        timezone_offset: Hours offset from UTC for the user's timezone.

    Returns:
        List of dicts with 'start', 'end', 'duration_minutes' keys (in UTC).
    """
    if blocked_days is None:
        blocked_days = [5, 6]

    # Total slot needed = requested duration + buffer
    total_needed = duration_minutes + buffer_minutes

    free_slots = check_calendar_availability(
        service, date_range_start, date_range_end, total_needed,
    )

    wh_start, wh_end = working_hours
    available = []

    for slot in free_slots:
        # Convert slot start to user's local time for working-hours check
        local_hour = (slot.start.hour + timezone_offset) % 24

        # Filter to working hours (in user's local time)
        if local_hour < wh_start or local_hour >= wh_end:
            continue

        # Check if the slot end would exceed working hours
        local_end_hour = (slot.start.hour + timezone_offset + (duration_minutes // 60)) % 24
        if local_end_hour > wh_end:
            continue

        # Skip blocked days (check in user's local time)
        local_day = slot.start + timedelta(hours=timezone_offset)
        if local_day.weekday() in blocked_days:
            continue

        # The actual bookable slot is duration_minutes (buffer is reserved after)
        slot_end = slot.start + timedelta(minutes=duration_minutes)

        available.append({
            "start": slot.start.isoformat(),
            "end": slot_end.isoformat(),
            "duration_minutes": duration_minutes,
        })

    logger.info(
        "get_available_slots: Found %d slots (wh=%d-%d, buffer=%dmin, blocked=%s).",
        len(available), wh_start, wh_end, buffer_minutes, blocked_days,
    )
    return available


# ---------------------------------------------------------------------------
# Smart Duration Detection
# ---------------------------------------------------------------------------

# Pattern → duration in minutes
_DURATION_PATTERNS: list[tuple[str, int]] = [
    (r"quick\s*call", 15),
    (r"brief\s*(?:call|chat|meeting)", 15),
    (r"15\s*min", 15),
    (r"interview", 45),
    (r"property\s*viewing", 30),
    (r"viewing", 30),
    (r"demo", 30),
    (r"presentation", 45),
    (r"consultation", 60),
    (r"onboarding", 60),
    (r"30\s*min", 30),
    (r"45\s*min", 45),
    (r"60\s*min", 60),
    (r"one\s*hour", 60),
    (r"half\s*(?:an?\s*)?hour", 30),
]


def detect_meeting_duration(email_text: str) -> int:
    """Infer meeting duration from email content.

    Scans the email subject + body for keywords that hint at the
    type of meeting and returns an appropriate duration in minutes.

    Args:
        email_text: Combined subject and body text.

    Returns:
        Duration in minutes (default 30).
    """
    lower = email_text.lower()
    for pattern, duration in _DURATION_PATTERNS:
        if re.search(pattern, lower):
            logger.debug("detect_meeting_duration: matched '%s' → %d min", pattern, duration)
            return duration
    return 30  # Default


# ---------------------------------------------------------------------------
# 4. cancel_event
# ---------------------------------------------------------------------------


def cancel_event(service: Resource, event_id: str) -> bool:
    """Cancel (delete) a calendar event by its ID.

    Args:
        service: Authenticated Google Calendar API service.
        event_id: The Google Calendar event ID to cancel.

    Returns:
        True if successfully cancelled, False otherwise.
    """
    try:
        service.events().delete(
            calendarId=GOOGLE_CALENDAR_ID,
            eventId=event_id,
        ).execute()
        logger.info("cancel_event: Cancelled event_id=%s", event_id)
        return True
    except HttpError as exc:
        logger.error("cancel_event failed for event_id=%s: %s", event_id, exc)
        return False


# ---------------------------------------------------------------------------
# 5. list_upcoming_events
# ---------------------------------------------------------------------------


def list_upcoming_events(
    service: Resource,
    days: int = 7,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    """List upcoming calendar events for the next N days.

    Args:
        service: Authenticated Google Calendar API service.
        days: Number of days ahead to search.
        max_results: Maximum events to return.

    Returns:
        List of event dicts with id, title, start, end, attendees, link.
    """
    try:
        now = datetime.now(timezone.utc)
        time_max = now + timedelta(days=days)

        result = service.events().list(
            calendarId=GOOGLE_CALENDAR_ID,
            timeMin=now.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = []
        for item in result.get("items", []):
            start = item.get("start", {})
            end = item.get("end", {})
            events.append({
                "id": item.get("id", ""),
                "title": item.get("summary", "No title"),
                "description": item.get("description", ""),
                "start": start.get("dateTime", start.get("date", "")),
                "end": end.get("dateTime", end.get("date", "")),
                "attendees": [
                    a.get("email", "") for a in item.get("attendees", [])
                ],
                "link": item.get("htmlLink", ""),
                "status": item.get("status", "confirmed"),
            })

        logger.info("list_upcoming_events: Found %d events in next %d days.", len(events), days)
        return events

    except HttpError as exc:
        logger.error("list_upcoming_events failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# 6. schedule_followup
# ---------------------------------------------------------------------------


def schedule_followup(
    email_id: str,
    follow_up_after_hours: float,
    note: str = "",
    sender_email: str = "",
) -> FollowUpScheduleResponse:
    """Schedule a follow-up reminder in the database.

    The reminder is persisted to PostgreSQL. The Celery beat scheduler will
    pick it up and trigger the follow-up action when the due time arrives.

    Args:
        email_id: Gmail message ID this follow-up relates to.
        follow_up_after_hours: Hours from now until the follow-up is due.
        note: Optional note describing the follow-up.
        sender_email: The sender's email (used for lookups).

    Returns:
        A FollowUpScheduleResponse with success status and DB record ID.
    """
    logger.info(
        "schedule_followup: email_id=%s, after_hours=%.1f, note=%r",
        email_id,
        follow_up_after_hours,
        note,
    )

    try:
        due_time = datetime.now(timezone.utc) + timedelta(hours=follow_up_after_hours)

        follow_up_data = FollowUpCreate(
            email_id=email_id,
            sender=sender_email,
            due_time=due_time,
            note=note,
        )

        record = create_follow_up(follow_up_data)

        logger.info(
            "schedule_followup: Created follow-up id=%d, due=%s.",
            record.id,
            due_time.isoformat(),
        )

        return FollowUpScheduleResponse(
            follow_up_id=record.id,
            email_id=email_id,
            due_time=due_time,
            success=True,
        )

    except Exception as exc:
        logger.error("schedule_followup failed: %s", exc)
        return FollowUpScheduleResponse(
            follow_up_id=0,
            email_id=email_id,
            due_time=datetime.now(timezone.utc),
            success=False,
            reason=str(exc),
        )
