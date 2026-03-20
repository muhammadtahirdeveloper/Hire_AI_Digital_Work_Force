"""Calendar tools for the GmailMind agent.

Provides calendar-related operations:
  1. build_calendar_service       — Build Calendar API service from user credentials
  2. check_calendar_availability  — Query Google Calendar for free slots
  3. get_available_slots          — Higher-level slot finder with working hours
  4. create_calendar_event        — Create a new event with attendees
  5. cancel_event                 — Cancel / delete a calendar event
  6. list_upcoming_events         — List upcoming events for next N days
  7. schedule_followup            — Save a follow-up reminder to DB (Celery picks it up)

All Google Calendar calls require a pre-authenticated
``googleapiclient.discovery.Resource`` built from the same OAuth2 credentials
used for Gmail (with the calendar scope added).
"""

import logging
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

        credentials = refresh_credentials(creds_data, user_id=user_id)
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
# 3. get_available_slots (higher-level helper)
# ---------------------------------------------------------------------------


def get_available_slots(
    service: Resource,
    date_range_start: datetime,
    date_range_end: datetime,
    duration_minutes: int = 30,
    working_hours: tuple[int, int] = (9, 17),
) -> list[dict[str, Any]]:
    """Find available appointment slots within working hours.

    Wraps check_calendar_availability and filters to working hours only.

    Args:
        service: Authenticated Google Calendar API service.
        date_range_start: Start of the search window (UTC).
        date_range_end: End of the search window (UTC).
        duration_minutes: Required slot duration in minutes.
        working_hours: Tuple of (start_hour, end_hour) in UTC.

    Returns:
        List of dicts with 'start', 'end', 'duration_minutes' keys.
    """
    free_slots = check_calendar_availability(
        service, date_range_start, date_range_end, duration_minutes,
    )

    wh_start, wh_end = working_hours
    available = []
    for slot in free_slots:
        # Filter to working hours
        if slot.start.hour < wh_start or slot.start.hour >= wh_end:
            continue
        # Skip weekends
        if slot.start.weekday() in (5, 6):
            continue
        available.append({
            "start": slot.start.isoformat(),
            "end": slot.end.isoformat(),
            "duration_minutes": slot.duration_minutes,
        })

    logger.info("get_available_slots: Found %d working-hour slots.", len(available))
    return available


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
