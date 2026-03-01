"""HR-specific skills for recruitment workflows.

Extends BaseSkills with candidate search, job requirements lookup,
weekly reporting, and WhatsApp-formatted summaries.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from config.database import SessionLocal
from skills.base_skills import BaseSkills

logger = logging.getLogger(__name__)

GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")


class HRSkills(BaseSkills):
    """Recruitment-specific skills for the HR agent."""

    # ------------------------------------------------------------------
    # Google Sheets logging
    # ------------------------------------------------------------------

    def log_candidate_to_sheets(
        self,
        cv_info: dict,
        job_title: str,
        user_id: str,
    ) -> bool:
        """Log a candidate entry to Google Sheets (or Python logger).

        Args:
            cv_info: Candidate info dict from CVProcessor.
            job_title: The job title applied for.
            user_id: The recruiter/user ID.

        Returns:
            True always (graceful fallback).
        """
        if GOOGLE_SHEETS_ID:
            try:
                self._append_to_sheets(cv_info, job_title, user_id)
                logger.info(
                    "HRSkills: Logged candidate %s to Google Sheets.",
                    cv_info.get("name", "unknown"),
                )
                return True
            except Exception as exc:
                logger.warning("HRSkills: Google Sheets write failed: %s", exc)

        # Fallback: log to Python logger
        logger.info(
            "HRSkills: [Sheets Fallback] Candidate=%s, Job=%s, User=%s, Email=%s",
            cv_info.get("name"),
            job_title,
            user_id,
            cv_info.get("email"),
        )
        return True

    def _append_to_sheets(
        self,
        cv_info: dict,
        job_title: str,
        user_id: str,
    ) -> None:
        """Append a row to Google Sheets via the Sheets API."""
        import httpx

        row = [
            datetime.now(timezone.utc).isoformat(),
            user_id,
            cv_info.get("name", ""),
            cv_info.get("email", ""),
            cv_info.get("phone", ""),
            job_title,
            str(cv_info.get("experience_years", 0)),
            ", ".join(cv_info.get("skills", [])),
            cv_info.get("location", ""),
        ]

        httpx.post(
            f"https://sheets.googleapis.com/v4/spreadsheets/{GOOGLE_SHEETS_ID}"
            "/values/Sheet1!A:I:append?valueInputOption=RAW",
            json={"values": [row]},
            timeout=15,
        )

    # ------------------------------------------------------------------
    # Candidate database search
    # ------------------------------------------------------------------

    def search_candidate_database(
        self,
        user_id: str,
        query: str,
    ) -> list[dict[str, Any]]:
        """Search candidates by name, email, skills, or role.

        Args:
            user_id: The recruiter/user ID.
            query: Search term.

        Returns:
            List of matching candidate dicts.
        """
        db = SessionLocal()
        try:
            like_pattern = f"%{query}%"
            rows = db.execute(
                text("""
                    SELECT id, email, name, phone, current_role,
                           experience_years, skills, cv_score, stage,
                           job_title_applied, created_at
                    FROM candidates
                    WHERE user_id = :uid
                      AND (
                        name ILIKE :q
                        OR email ILIKE :q
                        OR current_role ILIKE :q
                        OR skills::text ILIKE :q
                      )
                    ORDER BY created_at DESC
                    LIMIT 50
                """),
                {"uid": user_id, "q": like_pattern},
            ).fetchall()

            candidates = [
                {
                    "id": row[0],
                    "email": row[1],
                    "name": row[2],
                    "phone": row[3],
                    "current_role": row[4],
                    "experience_years": row[5],
                    "skills": row[6],
                    "cv_score": row[7],
                    "stage": row[8],
                    "job_title_applied": row[9],
                    "created_at": row[10].isoformat() if row[10] else None,
                }
                for row in rows
            ]
            logger.info(
                "HRSkills: Search '%s' returned %d candidates for user=%s.",
                query, len(candidates), user_id,
            )
            return candidates

        except Exception as exc:
            logger.error("HRSkills: Candidate search failed: %s", exc)
            return []
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Job requirements
    # ------------------------------------------------------------------

    def get_job_requirements(
        self,
        user_id: str,
        job_title: str,
    ) -> dict[str, Any]:
        """Retrieve job requirements from the database.

        Args:
            user_id: The recruiter/user ID.
            job_title: The job title to look up.

        Returns:
            Job requirements dict, or empty defaults if not found.
        """
        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT id, job_title, required_skills,
                           min_experience_years, location, salary_range
                    FROM job_requirements
                    WHERE user_id = :uid
                      AND LOWER(job_title) = LOWER(:title)
                      AND is_active = TRUE
                    LIMIT 1
                """),
                {"uid": user_id, "title": job_title},
            ).fetchone()

            if row:
                skills = row[2]
                if isinstance(skills, str):
                    skills = json.loads(skills)

                return {
                    "id": row[0],
                    "job_title": row[1],
                    "required_skills": skills or [],
                    "min_experience_years": row[3] or 0,
                    "location": row[4] or "",
                    "salary_range": row[5] or "",
                }

            logger.info(
                "HRSkills: No job requirements found for '%s', returning defaults.",
                job_title,
            )
            return {
                "job_title": job_title,
                "required_skills": [],
                "min_experience_years": 0,
                "location": "",
                "salary_range": "",
            }

        except Exception as exc:
            logger.error("HRSkills: Error fetching job requirements: %s", exc)
            return {
                "job_title": job_title,
                "required_skills": [],
                "min_experience_years": 0,
                "location": "",
                "salary_range": "",
            }
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Weekly recruitment report
    # ------------------------------------------------------------------

    def generate_weekly_recruitment_report(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Generate a comprehensive weekly HR recruitment report.

        Queries the last 7 days of candidates, interviews, and action logs.

        Args:
            user_id: The recruiter/user ID.

        Returns:
            Report dict with all metrics.
        """
        db = SessionLocal()
        try:
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            now = datetime.now(timezone.utc).isoformat()

            # New candidates this week
            new_candidates = db.execute(
                text("""
                    SELECT COUNT(*) FROM candidates
                    WHERE user_id = :uid AND created_at >= :since
                """),
                {"uid": user_id, "since": week_ago},
            ).scalar() or 0

            # Candidates per stage
            stage_rows = db.execute(
                text("""
                    SELECT stage, COUNT(*) FROM candidates
                    WHERE user_id = :uid
                    GROUP BY stage
                """),
                {"uid": user_id},
            ).fetchall()
            pipeline = {row[0]: row[1] for row in stage_rows}

            # Interviews this week
            interviews_scheduled = db.execute(
                text("""
                    SELECT COUNT(*) FROM interviews
                    WHERE user_id = :uid
                      AND created_at >= :since
                      AND status = 'scheduled'
                """),
                {"uid": user_id, "since": week_ago},
            ).scalar() or 0

            interviews_completed = db.execute(
                text("""
                    SELECT COUNT(*) FROM interviews
                    WHERE user_id = :uid
                      AND created_at >= :since
                      AND status = 'completed'
                """),
                {"uid": user_id, "since": week_ago},
            ).scalar() or 0

            # Emails processed this week
            emails_processed = db.execute(
                text("""
                    SELECT COUNT(*) FROM action_logs
                    WHERE user_id = :uid AND timestamp >= :since
                """),
                {"uid": user_id, "since": week_ago},
            ).scalar() or 0

            # Hires and rejections this week
            hires = db.execute(
                text("""
                    SELECT COUNT(*) FROM candidates
                    WHERE user_id = :uid
                      AND stage = 'hired'
                      AND updated_at >= :since
                """),
                {"uid": user_id, "since": week_ago},
            ).scalar() or 0

            rejections = db.execute(
                text("""
                    SELECT COUNT(*) FROM candidates
                    WHERE user_id = :uid
                      AND stage = 'rejected'
                      AND updated_at >= :since
                """),
                {"uid": user_id, "since": week_ago},
            ).scalar() or 0

            report = {
                "user_id": user_id,
                "period": "weekly",
                "generated_at": now,
                "week_start": week_ago,
                "new_candidates": new_candidates,
                "pipeline": pipeline,
                "interviews_scheduled": interviews_scheduled,
                "interviews_completed": interviews_completed,
                "emails_processed": emails_processed,
                "hires": hires,
                "rejections": rejections,
                "shortlisted": pipeline.get("screened", 0) + pipeline.get("interview", 0),
            }

            logger.info(
                "HRSkills: Generated weekly report for user=%s: %d new CVs, %d interviews.",
                user_id, new_candidates, interviews_scheduled,
            )
            return report

        except Exception as exc:
            logger.error("HRSkills: Error generating weekly report: %s", exc)
            return {
                "user_id": user_id,
                "period": "weekly",
                "generated_at": now,
                "error": str(exc),
            }
        finally:
            db.close()

    # ------------------------------------------------------------------
    # WhatsApp formatting
    # ------------------------------------------------------------------

    def format_report_for_whatsapp(self, report: dict) -> str:
        """Format a recruitment report as a WhatsApp-friendly message.

        Args:
            report: Report dict from generate_weekly_recruitment_report.

        Returns:
            Formatted string with emojis for WhatsApp.
        """
        pipeline = report.get("pipeline", {})

        pipeline_flow = (
            f"Applied({pipeline.get('applied', 0)}) → "
            f"Screened({pipeline.get('screened', 0)}) → "
            f"Interview({pipeline.get('interview', 0)}) → "
            f"Offer({pipeline.get('offer', 0)})"
        )

        msg = (
            "📊 HR Weekly Report\n"
            "═══════════════════\n"
            f"📧 Emails processed: {report.get('emails_processed', 0)}\n"
            f"👤 New CVs: {report.get('new_candidates', 0)}\n"
            f"⭐ Shortlisted: {report.get('shortlisted', 0)}\n"
            f"📅 Interviews scheduled: {report.get('interviews_scheduled', 0)}\n"
            f"✅ Hires: {report.get('hires', 0)}\n"
            f"❌ Rejections: {report.get('rejections', 0)}\n"
            "═══════════════════\n"
            f"📈 Pipeline: {pipeline_flow}"
        )

        return msg
