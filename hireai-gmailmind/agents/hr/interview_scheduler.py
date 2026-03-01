"""Interview scheduling for HR agent.

Uses Google Calendar (via existing tools) to find available slots
and schedules interviews with candidates, storing records in the
interviews table.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import text

from config.database import SessionLocal

logger = logging.getLogger(__name__)


class InterviewScheduler:
    """Schedules and tracks candidate interviews."""

    def find_available_slots(
        self,
        user_id: str,
        duration_minutes: int = 60,
        days_ahead: int = 7,
    ) -> list[str]:
        """Find available calendar slots for interviews.

        Uses existing check_calendar_availability from tools/calendar_tools.py.
        Falls back to generating default slots if calendar is not configured.

        Args:
            user_id: The recruiter/user ID.
            duration_minutes: Interview duration in minutes.
            days_ahead: Number of days ahead to search.

        Returns:
            List of available datetime strings (ISO format).
        """
        try:
            from tools.calendar_tools import check_calendar_availability

            start = datetime.now(timezone.utc)
            end = start + timedelta(days=days_ahead)

            slots = check_calendar_availability(
                date_range_start=start.isoformat(),
                date_range_end=end.isoformat(),
            )

            if slots:
                available = [s.start_time for s in slots if hasattr(s, "start_time")]
                logger.info(
                    "InterviewScheduler: Found %d available slots for user=%s",
                    len(available), user_id,
                )
                return available
        except Exception as exc:
            logger.warning("InterviewScheduler: Calendar not available, using defaults: %s", exc)

        # Fallback: generate default weekday slots (10:00, 14:00, 16:00)
        return self._generate_default_slots(days_ahead)

    def _generate_default_slots(self, days_ahead: int) -> list[str]:
        """Generate default interview time slots for upcoming weekdays."""
        slots = []
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        for day_offset in range(1, days_ahead + 1):
            day = today + timedelta(days=day_offset)
            # Skip weekends (5=Saturday, 6=Sunday)
            if day.weekday() in (5, 6):
                continue
            for hour in (10, 14, 16):
                slot = day.replace(hour=hour, minute=0)
                slots.append(slot.isoformat())

        logger.info("InterviewScheduler: Generated %d default slots.", len(slots))
        return slots

    def schedule_interview(
        self,
        user_id: str,
        candidate_email: str,
        slot: str,
        job_title: str,
        interview_type: str = "video",
    ) -> dict[str, Any]:
        """Schedule an interview for a candidate.

        Creates a calendar event (if available) and inserts a record
        in the interviews table.

        Args:
            user_id: The recruiter/user ID.
            candidate_email: The candidate's email.
            slot: ISO datetime string for the interview.
            job_title: Job title for the interview.
            interview_type: 'video', 'phone', or 'in_person'.

        Returns:
            Dict with calendar_event_id and interview_id.
        """
        calendar_event_id = None

        # Try to create a calendar event
        try:
            from tools.calendar_tools import create_calendar_event

            scheduled_dt = datetime.fromisoformat(slot)
            end_dt = scheduled_dt + timedelta(minutes=60)

            calendar_event_id = create_calendar_event(
                title=f"Interview: {job_title} - {candidate_email}",
                start_time=scheduled_dt.isoformat(),
                end_time=end_dt.isoformat(),
                attendees=[candidate_email],
                description=f"Interview for {job_title} position. Type: {interview_type}",
            )
            logger.info("InterviewScheduler: Created calendar event: %s", calendar_event_id)
        except Exception as exc:
            logger.warning("InterviewScheduler: Calendar event creation failed: %s", exc)

        # Insert into interviews table
        db = SessionLocal()
        try:
            result = db.execute(
                text("""
                    INSERT INTO interviews
                        (user_id, candidate_email, scheduled_at, duration_minutes,
                         interview_type, calendar_event_id, status)
                    VALUES
                        (:uid, :email, :scheduled_at, :duration, :itype, :cal_id, 'scheduled')
                    RETURNING id
                """),
                {
                    "uid": user_id,
                    "email": candidate_email,
                    "scheduled_at": slot,
                    "duration": 60,
                    "itype": interview_type,
                    "cal_id": calendar_event_id or "",
                },
            )
            db.commit()
            interview_id = result.fetchone()[0]

            logger.info(
                "InterviewScheduler: Scheduled interview id=%d for %s at %s",
                interview_id, candidate_email, slot,
            )
            return {
                "calendar_event_id": calendar_event_id,
                "interview_id": interview_id,
            }
        except Exception as exc:
            db.rollback()
            logger.error("InterviewScheduler: Error scheduling interview: %s", exc)
            return {"calendar_event_id": None, "interview_id": None}
        finally:
            db.close()

    def get_upcoming_interviews(
        self,
        user_id: str,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """Get upcoming scheduled interviews.

        Args:
            user_id: The recruiter/user ID.
            days: Number of days ahead to look.

        Returns:
            List of interview dicts.
        """
        db = SessionLocal()
        try:
            cutoff = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
            now = datetime.now(timezone.utc).isoformat()

            rows = db.execute(
                text("""
                    SELECT id, candidate_email, scheduled_at, duration_minutes,
                           interview_type, calendar_event_id, status, notes, created_at
                    FROM interviews
                    WHERE user_id = :uid
                      AND scheduled_at >= :now
                      AND scheduled_at <= :cutoff
                      AND status = 'scheduled'
                    ORDER BY scheduled_at ASC
                """),
                {"uid": user_id, "now": now, "cutoff": cutoff},
            ).fetchall()

            interviews = [
                {
                    "id": row[0],
                    "candidate_email": row[1],
                    "scheduled_at": row[2].isoformat() if row[2] else None,
                    "duration_minutes": row[3],
                    "interview_type": row[4],
                    "calendar_event_id": row[5],
                    "status": row[6],
                    "notes": row[7],
                    "created_at": row[8].isoformat() if row[8] else None,
                }
                for row in rows
            ]
            logger.info(
                "InterviewScheduler: Found %d upcoming interviews for user=%s",
                len(interviews), user_id,
            )
            return interviews
        except Exception as exc:
            logger.error("InterviewScheduler: Error fetching interviews: %s", exc)
            return []
        finally:
            db.close()
