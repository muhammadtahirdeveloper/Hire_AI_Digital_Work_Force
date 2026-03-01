"""Candidate pipeline tracker for HR agent.

Manages candidate lifecycle from 'applied' through 'hired' or 'rejected'
using the candidates table in the database.
"""

import logging
from typing import Any, Optional

from sqlalchemy import text

from config.database import SessionLocal

logger = logging.getLogger(__name__)


class CandidateTracker:
    """Tracks candidates through the recruitment pipeline."""

    STAGES = ["applied", "screened", "interview", "offer", "hired", "rejected"]

    def get_candidate(self, user_id: str, email: str) -> Optional[dict[str, Any]]:
        """Get a candidate by user_id and email.

        Args:
            user_id: The recruiter/user ID.
            email: The candidate's email address.

        Returns:
            Candidate dict or None if not found.
        """
        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT id, user_id, email, name, phone, current_role,
                           experience_years, skills, education, location,
                           cv_score, stage, job_title_applied, notes,
                           source_email_id, created_at, updated_at
                    FROM candidates
                    WHERE user_id = :uid AND email = :email
                """),
                {"uid": user_id, "email": email},
            ).fetchone()

            if not row:
                return None

            return {
                "id": row[0],
                "user_id": row[1],
                "email": row[2],
                "name": row[3],
                "phone": row[4],
                "current_role": row[5],
                "experience_years": row[6],
                "skills": row[7],
                "education": row[8],
                "location": row[9],
                "cv_score": row[10],
                "stage": row[11],
                "job_title_applied": row[12],
                "notes": row[13],
                "source_email_id": row[14],
                "created_at": row[15].isoformat() if row[15] else None,
                "updated_at": row[16].isoformat() if row[16] else None,
            }
        except Exception as exc:
            logger.error("CandidateTracker: Error getting candidate %s: %s", email, exc)
            return None
        finally:
            db.close()

    def create_candidate(
        self,
        user_id: str,
        cv_info: dict[str, Any],
        job_title: str,
        source_email_id: str = "",
    ) -> Optional[int]:
        """Insert a new candidate into the database.

        If the candidate already exists (same user_id + email), updates instead.

        Args:
            user_id: The recruiter/user ID.
            cv_info: Candidate info dict from CVProcessor.
            job_title: The job title applied for.
            source_email_id: The email ID that originated this candidate.

        Returns:
            Candidate ID, or None on failure.
        """
        import json

        db = SessionLocal()
        try:
            # Check if already exists
            existing = db.execute(
                text("SELECT id FROM candidates WHERE user_id = :uid AND email = :email"),
                {"uid": user_id, "email": cv_info.get("email", "")},
            ).fetchone()

            if existing:
                # Update existing candidate
                db.execute(
                    text("""
                        UPDATE candidates SET
                            name = COALESCE(:name, name),
                            phone = COALESCE(:phone, phone),
                            current_role = COALESCE(:current_role, current_role),
                            experience_years = :experience_years,
                            skills = :skills,
                            education = COALESCE(:education, education),
                            location = COALESCE(:location, location),
                            updated_at = NOW()
                        WHERE user_id = :uid AND email = :email
                    """),
                    {
                        "uid": user_id,
                        "email": cv_info.get("email", ""),
                        "name": cv_info.get("name"),
                        "phone": cv_info.get("phone"),
                        "current_role": cv_info.get("current_role"),
                        "experience_years": cv_info.get("experience_years", 0),
                        "skills": json.dumps(cv_info.get("skills", [])),
                        "education": cv_info.get("education"),
                        "location": cv_info.get("location"),
                    },
                )
                db.commit()
                logger.info("CandidateTracker: Updated existing candidate %s", cv_info.get("email"))
                return existing[0]

            # Insert new candidate
            result = db.execute(
                text("""
                    INSERT INTO candidates
                        (user_id, email, name, phone, current_role,
                         experience_years, skills, education, location,
                         job_title_applied, source_email_id, stage)
                    VALUES
                        (:uid, :email, :name, :phone, :current_role,
                         :experience_years, :skills, :education, :location,
                         :job_title, :source_email_id, 'applied')
                    RETURNING id
                """),
                {
                    "uid": user_id,
                    "email": cv_info.get("email", ""),
                    "name": cv_info.get("name"),
                    "phone": cv_info.get("phone"),
                    "current_role": cv_info.get("current_role"),
                    "experience_years": cv_info.get("experience_years", 0),
                    "skills": json.dumps(cv_info.get("skills", [])),
                    "education": cv_info.get("education"),
                    "location": cv_info.get("location"),
                    "job_title": job_title,
                    "source_email_id": source_email_id,
                },
            )
            db.commit()
            candidate_id = result.fetchone()[0]
            logger.info(
                "CandidateTracker: Created candidate id=%d email=%s job=%s",
                candidate_id, cv_info.get("email"), job_title,
            )
            return candidate_id

        except Exception as exc:
            db.rollback()
            logger.error("CandidateTracker: Error creating candidate: %s", exc)
            return None
        finally:
            db.close()

    def update_stage(
        self,
        user_id: str,
        email: str,
        stage: str,
        notes: str = "",
    ) -> bool:
        """Update a candidate's pipeline stage.

        Args:
            user_id: The recruiter/user ID.
            email: The candidate's email address.
            stage: New stage (must be one of STAGES).
            notes: Optional notes about the stage change.

        Returns:
            True on success, False on failure.
        """
        if stage not in self.STAGES:
            logger.error("CandidateTracker: Invalid stage '%s'. Valid: %s", stage, self.STAGES)
            return False

        db = SessionLocal()
        try:
            result = db.execute(
                text("""
                    UPDATE candidates
                    SET stage = :stage, notes = :notes, updated_at = NOW()
                    WHERE user_id = :uid AND email = :email
                """),
                {"uid": user_id, "email": email, "stage": stage, "notes": notes},
            )
            db.commit()

            if result.rowcount == 0:
                logger.warning("CandidateTracker: No candidate found for %s/%s", user_id, email)
                return False

            logger.info("CandidateTracker: Updated %s to stage '%s'", email, stage)
            return True
        except Exception as exc:
            db.rollback()
            logger.error("CandidateTracker: Error updating stage: %s", exc)
            return False
        finally:
            db.close()

    def get_pipeline_summary(self, user_id: str) -> dict[str, int]:
        """Get count of candidates per pipeline stage.

        Args:
            user_id: The recruiter/user ID.

        Returns:
            Dict like {'applied': 5, 'screened': 3, 'interview': 2, ...}
        """
        summary = {stage: 0 for stage in self.STAGES}

        db = SessionLocal()
        try:
            rows = db.execute(
                text("""
                    SELECT stage, COUNT(*) as cnt
                    FROM candidates
                    WHERE user_id = :uid
                    GROUP BY stage
                """),
                {"uid": user_id},
            ).fetchall()

            for row in rows:
                if row[0] in summary:
                    summary[row[0]] = row[1]

            logger.info("CandidateTracker: Pipeline summary for user=%s: %s", user_id, summary)
            return summary
        except Exception as exc:
            logger.error("CandidateTracker: Error getting pipeline summary: %s", exc)
            return summary
        finally:
            db.close()

    def get_candidates_by_stage(self, user_id: str, stage: str) -> list[dict[str, Any]]:
        """Get all candidates at a given pipeline stage.

        Args:
            user_id: The recruiter/user ID.
            stage: The pipeline stage to filter by.

        Returns:
            List of candidate dicts.
        """
        db = SessionLocal()
        try:
            rows = db.execute(
                text("""
                    SELECT id, email, name, phone, current_role,
                           experience_years, cv_score, job_title_applied,
                           notes, created_at
                    FROM candidates
                    WHERE user_id = :uid AND stage = :stage
                    ORDER BY created_at DESC
                """),
                {"uid": user_id, "stage": stage},
            ).fetchall()

            candidates = [
                {
                    "id": row[0],
                    "email": row[1],
                    "name": row[2],
                    "phone": row[3],
                    "current_role": row[4],
                    "experience_years": row[5],
                    "cv_score": row[6],
                    "job_title_applied": row[7],
                    "notes": row[8],
                    "created_at": row[9].isoformat() if row[9] else None,
                }
                for row in rows
            ]
            logger.info(
                "CandidateTracker: Found %d candidates at stage '%s' for user=%s",
                len(candidates), stage, user_id,
            )
            return candidates
        except Exception as exc:
            logger.error("CandidateTracker: Error getting candidates by stage: %s", exc)
            return []
        finally:
            db.close()
