"""HR recruitment management endpoints.

Routes:
  GET  /hr/{user_id}/candidates                        — List candidates (filterable by stage).
  GET  /hr/{user_id}/candidates/{candidate_email}      — Get full candidate profile.
  PUT  /hr/{user_id}/candidates/{candidate_email}/stage — Update candidate pipeline stage.
  GET  /hr/{user_id}/pipeline                           — Pipeline summary (count per stage).
  GET  /hr/{user_id}/interviews                         — Upcoming interviews.
  GET  /hr/{user_id}/report/weekly                      — Weekly recruitment report.
  POST /hr/{user_id}/jobs                               — Create a job requirement.
  GET  /hr/{user_id}/jobs                               — List active job requirements.
"""

import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Body, Query
from sqlalchemy import text

from agents.hr.candidate_tracker import CandidateTracker
from agents.hr.interview_scheduler import InterviewScheduler
from config.database import SessionLocal
from skills.hr_skills import HRSkills

logger = logging.getLogger(__name__)

router = APIRouter()

# Shared instances
_tracker = CandidateTracker()
_scheduler = InterviewScheduler()
_hr_skills = HRSkills()


# ============================================================================
# Helpers
# ============================================================================


def _ok(data: Any = None) -> dict:
    return {"success": True, "data": data, "error": None}


def _err(message: str) -> dict:
    return {"success": False, "data": None, "error": message}


# ============================================================================
# GET /hr/{user_id}/candidates
# ============================================================================


@router.get("/{user_id}/candidates", tags=["HR"])
async def list_candidates(
    user_id: str,
    stage: Optional[str] = Query(None, description="Filter by pipeline stage"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List candidates for a user, optionally filtered by stage."""
    db = SessionLocal()
    try:
        offset = (page - 1) * page_size

        if stage:
            # Validate stage
            if stage not in _tracker.STAGES:
                return _err(f"Invalid stage '{stage}'. Valid: {_tracker.STAGES}")

            rows = db.execute(
                text("""
                    SELECT id, email, name, phone, current_role,
                           experience_years, cv_score, stage,
                           job_title_applied, notes, created_at, updated_at
                    FROM candidates
                    WHERE user_id = :uid AND stage = :stage
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """),
                {"uid": user_id, "stage": stage, "limit": page_size, "offset": offset},
            ).fetchall()

            total_row = db.execute(
                text("SELECT COUNT(*) FROM candidates WHERE user_id = :uid AND stage = :stage"),
                {"uid": user_id, "stage": stage},
            ).scalar() or 0
        else:
            rows = db.execute(
                text("""
                    SELECT id, email, name, phone, current_role,
                           experience_years, cv_score, stage,
                           job_title_applied, notes, created_at, updated_at
                    FROM candidates
                    WHERE user_id = :uid
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """),
                {"uid": user_id, "limit": page_size, "offset": offset},
            ).fetchall()

            total_row = db.execute(
                text("SELECT COUNT(*) FROM candidates WHERE user_id = :uid"),
                {"uid": user_id},
            ).scalar() or 0

        candidates = [
            {
                "id": r[0],
                "email": r[1],
                "name": r[2],
                "phone": r[3],
                "current_role": r[4],
                "experience_years": r[5],
                "cv_score": r[6],
                "stage": r[7],
                "job_title_applied": r[8],
                "notes": r[9],
                "created_at": r[10].isoformat() if r[10] else None,
                "updated_at": r[11].isoformat() if r[11] else None,
            }
            for r in rows
        ]

        return _ok({
            "candidates": candidates,
            "page": page,
            "page_size": page_size,
            "total": total_row,
        })

    except Exception as exc:
        logger.exception("Failed to list candidates for user %s", user_id)
        return _err(f"Failed to list candidates: {exc}")
    finally:
        db.close()


# ============================================================================
# GET /hr/{user_id}/candidates/{candidate_email}
# ============================================================================


@router.get("/{user_id}/candidates/{candidate_email}", tags=["HR"])
async def get_candidate(user_id: str, candidate_email: str):
    """Get full candidate profile."""
    try:
        candidate = _tracker.get_candidate(user_id, candidate_email)
        if not candidate:
            return _err(f"Candidate '{candidate_email}' not found.")
        return _ok(candidate)

    except Exception as exc:
        logger.exception("Failed to get candidate %s", candidate_email)
        return _err(f"Failed to get candidate: {exc}")


# ============================================================================
# PUT /hr/{user_id}/candidates/{candidate_email}/stage
# ============================================================================


@router.put("/{user_id}/candidates/{candidate_email}/stage", tags=["HR"])
async def update_candidate_stage(
    user_id: str,
    candidate_email: str,
    body: dict = Body(...),
):
    """Update a candidate's pipeline stage.

    Body:
        {"stage": "interview", "notes": "Passed phone screening"}
    """
    stage = body.get("stage", "")
    notes = body.get("notes", "")

    if stage not in _tracker.STAGES:
        return _err(f"Invalid stage '{stage}'. Valid: {_tracker.STAGES}")

    try:
        success = _tracker.update_stage(user_id, candidate_email, stage, notes)
        if not success:
            return _err(f"Candidate '{candidate_email}' not found or update failed.")

        return _ok({
            "success": True,
            "candidate_email": candidate_email,
            "new_stage": stage,
        })

    except Exception as exc:
        logger.exception("Failed to update stage for %s", candidate_email)
        return _err(f"Failed to update stage: {exc}")


# ============================================================================
# GET /hr/{user_id}/pipeline
# ============================================================================


@router.get("/{user_id}/pipeline", tags=["HR"])
async def get_pipeline(user_id: str):
    """Get pipeline summary — count of candidates per stage."""
    try:
        summary = _tracker.get_pipeline_summary(user_id)
        return _ok(summary)

    except Exception as exc:
        logger.exception("Failed to get pipeline for user %s", user_id)
        return _err(f"Failed to get pipeline: {exc}")


# ============================================================================
# GET /hr/{user_id}/interviews
# ============================================================================


@router.get("/{user_id}/interviews", tags=["HR"])
async def get_interviews(
    user_id: str,
    days_ahead: int = Query(7, ge=1, le=90),
):
    """Get upcoming scheduled interviews."""
    try:
        interviews = _scheduler.get_upcoming_interviews(user_id, days=days_ahead)
        return _ok({
            "interviews": interviews,
            "count": len(interviews),
            "days_ahead": days_ahead,
        })

    except Exception as exc:
        logger.exception("Failed to get interviews for user %s", user_id)
        return _err(f"Failed to get interviews: {exc}")


# ============================================================================
# GET /hr/{user_id}/report/weekly
# ============================================================================


@router.get("/{user_id}/report/weekly", tags=["HR"])
async def weekly_report(user_id: str):
    """Generate weekly recruitment report."""
    try:
        report = _hr_skills.generate_weekly_recruitment_report(user_id)
        whatsapp_formatted = _hr_skills.format_report_for_whatsapp(report)

        return _ok({
            "report": report,
            "whatsapp_format": whatsapp_formatted,
        })

    except Exception as exc:
        logger.exception("Failed to generate weekly report for user %s", user_id)
        return _err(f"Failed to generate report: {exc}")


# ============================================================================
# POST /hr/{user_id}/jobs
# ============================================================================


@router.post("/{user_id}/jobs", tags=["HR"])
async def create_job(
    user_id: str,
    body: dict = Body(...),
):
    """Create a new job requirement.

    Body:
        {
            "job_title": "Senior Python Developer",
            "required_skills": ["Python", "Django", "PostgreSQL"],
            "min_experience_years": 3,
            "location": "Remote"
        }
    """
    job_title = body.get("job_title", "")
    if not job_title:
        return _err("job_title is required.")

    required_skills = body.get("required_skills", [])
    min_experience = body.get("min_experience_years", 0)
    location = body.get("location", "")
    salary_range = body.get("salary_range", "")

    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                INSERT INTO job_requirements
                    (user_id, job_title, required_skills, min_experience_years,
                     location, salary_range, is_active, created_at)
                VALUES
                    (:uid, :title, :skills, :exp, :loc, :salary, TRUE, NOW())
                RETURNING id
            """),
            {
                "uid": user_id,
                "title": job_title,
                "skills": json.dumps(required_skills),
                "exp": min_experience,
                "loc": location,
                "salary": salary_range,
            },
        )
        db.commit()
        job_id = result.fetchone()[0]

        logger.info("Created job requirement id=%d for user %s: %s", job_id, user_id, job_title)

        return _ok({
            "success": True,
            "job_id": job_id,
            "job_title": job_title,
        })

    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create job for user %s", user_id)
        return _err(f"Failed to create job: {exc}")
    finally:
        db.close()


# ============================================================================
# GET /hr/{user_id}/jobs
# ============================================================================


@router.get("/{user_id}/jobs", tags=["HR"])
async def list_jobs(user_id: str):
    """List active job requirements for a user."""
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT id, job_title, required_skills, min_experience_years,
                       location, salary_range, is_active, created_at
                FROM job_requirements
                WHERE user_id = :uid AND is_active = TRUE
                ORDER BY created_at DESC
            """),
            {"uid": user_id},
        ).fetchall()

        jobs = [
            {
                "id": r[0],
                "job_title": r[1],
                "required_skills": r[2] if isinstance(r[2], list) else json.loads(r[2] or "[]"),
                "min_experience_years": r[3],
                "location": r[4],
                "salary_range": r[5],
                "is_active": r[6],
                "created_at": r[7].isoformat() if r[7] else None,
            }
            for r in rows
        ]

        return _ok({
            "jobs": jobs,
            "count": len(jobs),
        })

    except Exception as exc:
        logger.exception("Failed to list jobs for user %s", user_id)
        return _err(f"Failed to list jobs: {exc}")
    finally:
        db.close()
