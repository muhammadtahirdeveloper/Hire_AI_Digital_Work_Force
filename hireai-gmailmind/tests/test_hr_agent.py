"""Tests for the HR Specialist Agent components.

Covers:
  - CVProcessor: email detection, regex extraction, candidate scoring
  - CandidateTracker: stage validation
  - HRAgent: email classification
  - HRSkills: WhatsApp report formatting
  - BaseSkills: urgency detection, contact extraction, follow-up dates
"""

import pytest
from datetime import datetime, timezone

from agents.hr.cv_processor import CVProcessor
from agents.hr.candidate_tracker import CandidateTracker
from agents.hr.hr_agent import HRAgent
from agents.hr.hr_templates import HR_TEMPLATES
from skills.base_skills import BaseSkills
from skills.hr_skills import HRSkills


# ============================================================================
# CVProcessor — Email detection
# ============================================================================


class TestCVEmailDetection:
    def test_cv_email_detected(self):
        processor = CVProcessor()
        cv_email = {
            "subject": "Job Application - Software Engineer",
            "body": "Please find attached my resume for the position.",
        }
        assert processor.is_cv_email(cv_email) is True

    def test_resume_keyword_detected(self):
        processor = CVProcessor()
        email = {
            "subject": "Resume Submission",
            "body": "I am applying for the open role.",
        }
        assert processor.is_cv_email(email) is True

    def test_non_cv_email_not_detected(self):
        processor = CVProcessor()
        regular_email = {
            "subject": "Meeting Tomorrow",
            "body": "Can we meet tomorrow at 3pm?",
        }
        assert processor.is_cv_email(regular_email) is False

    def test_cv_in_body_only(self):
        processor = CVProcessor()
        email = {
            "subject": "Hello",
            "body": "I am attaching my cv for your review",
        }
        assert processor.is_cv_email(email) is True


# ============================================================================
# CVProcessor — Regex extraction
# ============================================================================


class TestCVRegexExtraction:
    def test_extract_email_from_body(self):
        processor = CVProcessor()
        result = processor._extract_with_regex(
            email_body="Contact me at john@example.com",
            subject="Application - John Doe",
        )
        assert result["email"] == "john@example.com"

    def test_extract_name_from_subject(self):
        processor = CVProcessor()
        result = processor._extract_with_regex(
            email_body="Please find my resume attached",
            subject="Application - Jane Smith",
        )
        assert result["name"] == "Jane Smith"

    def test_extract_experience_years(self):
        processor = CVProcessor()
        result = processor._extract_with_regex(
            email_body="I have 5 years of experience in Python development",
            subject="Application",
        )
        assert result["experience_years"] == 5

    def test_extract_attachment_keyword(self):
        processor = CVProcessor()
        result = processor._extract_with_regex(
            email_body="Please find attached my resume",
            subject="Job Application",
        )
        assert result["has_cv_attachment"] is True

    def test_missing_fields_default(self):
        processor = CVProcessor()
        result = processor._extract_with_regex(
            email_body="Hello",
            subject="Hi",
        )
        assert result["name"] is None
        assert result["experience_years"] == 0
        assert result["skills"] == []
        assert result["has_cv_attachment"] is False


# ============================================================================
# CVProcessor — Candidate scoring
# ============================================================================


class TestCandidateScoring:
    def test_high_score_full_match(self):
        processor = CVProcessor()
        cv_info = {
            "skills": ["Python", "Django", "PostgreSQL"],
            "experience_years": 5,
            "location": "Remote",
        }
        job_req = {
            "required_skills": ["Python", "Django"],
            "min_experience_years": 3,
            "location": "Remote",
        }
        score = processor.score_candidate(cv_info, job_req)
        assert score >= 70

    def test_low_score_no_match(self):
        processor = CVProcessor()
        cv_info = {
            "skills": ["Java"],
            "experience_years": 1,
            "location": "Tokyo",
        }
        job_req = {
            "required_skills": ["Python", "Django", "React"],
            "min_experience_years": 5,
            "location": "London",
        }
        score = processor.score_candidate(cv_info, job_req)
        assert score < 40

    def test_mid_score_partial_match(self):
        processor = CVProcessor()
        cv_info = {
            "skills": ["Python"],
            "experience_years": 2,
            "location": "Remote",
        }
        job_req = {
            "required_skills": ["Python", "Django"],
            "min_experience_years": 3,
            "location": "Remote",
        }
        score = processor.score_candidate(cv_info, job_req)
        assert 40 <= score <= 80

    def test_empty_requirements_generous(self):
        processor = CVProcessor()
        cv_info = {
            "skills": ["Python"],
            "experience_years": 2,
            "location": "Anywhere",
        }
        score = processor.score_candidate(cv_info, {})
        # Should give benefit of the doubt
        assert score >= 50

    def test_score_max_100(self):
        processor = CVProcessor()
        cv_info = {
            "skills": ["Python", "Django", "React", "AWS", "Docker"],
            "experience_years": 10,
            "location": "Remote",
        }
        job_req = {
            "required_skills": ["Python", "Django"],
            "min_experience_years": 2,
            "location": "Remote",
        }
        score = processor.score_candidate(cv_info, job_req)
        assert score <= 100


# ============================================================================
# CandidateTracker — Stage validation
# ============================================================================


class TestPipelineStages:
    def test_all_stages_present(self):
        tracker = CandidateTracker()
        valid_stages = tracker.STAGES
        assert "applied" in valid_stages
        assert "screened" in valid_stages
        assert "interview" in valid_stages
        assert "offer" in valid_stages
        assert "hired" in valid_stages
        assert "rejected" in valid_stages

    def test_stage_count(self):
        tracker = CandidateTracker()
        assert len(tracker.STAGES) == 6

    def test_invalid_stage_rejected(self):
        tracker = CandidateTracker()
        # update_stage validates stage before DB call
        result = tracker.update_stage("user1", "test@test.com", "invalid_stage")
        assert result is False


# ============================================================================
# HRAgent — Email classification
# ============================================================================


class TestHREmailClassification:
    def test_cv_application(self):
        agent = HRAgent()
        email = {
            "subject": "Application for Developer Role",
            "body": "Please find my CV attached",
        }
        assert agent.classify_email(email) == "cv_application"

    def test_interview_request(self):
        agent = HRAgent()
        email = {
            "subject": "Re: Interview Schedule",
            "body": "I am available for interview",
        }
        assert agent.classify_email(email) == "interview_request"

    def test_candidate_followup(self):
        agent = HRAgent()
        email = {
            "subject": "Any news?",
            "body": "Just checking in, have you heard back yet?",
        }
        assert agent.classify_email(email) == "candidate_followup"

    def test_offer_acceptance(self):
        agent = HRAgent()
        email = {
            "subject": "Re: Offer",
            "body": "I am pleased to accept the position",
        }
        assert agent.classify_email(email) == "offer_acceptance"

    def test_offer_rejection(self):
        agent = HRAgent()
        email = {
            "subject": "Re: Offer",
            "body": "I regret to inform you that I have chosen another opportunity",
        }
        assert agent.classify_email(email) == "offer_rejection"

    def test_job_inquiry(self):
        agent = HRAgent()
        email = {
            "subject": "Open Positions",
            "body": "Are you hiring for any new positions?",
        }
        assert agent.classify_email(email) == "job_inquiry"

    def test_other_email(self):
        agent = HRAgent()
        email = {
            "subject": "Lunch plans",
            "body": "Want to grab lunch?",
        }
        assert agent.classify_email(email) == "other"


# ============================================================================
# HR Templates
# ============================================================================


class TestHRTemplates:
    def test_all_templates_present(self):
        expected = [
            "cv_received", "interview_invite", "interview_confirmation",
            "rejection_polite", "follow_up_candidate", "client_position_update",
        ]
        for key in expected:
            assert key in HR_TEMPLATES

    def test_cv_received_has_placeholders(self):
        template = HR_TEMPLATES["cv_received"]
        assert "{candidate_name}" in template
        assert "{job_title}" in template
        assert "{company_name}" in template

    def test_template_formatting(self):
        body = HR_TEMPLATES["cv_received"].format(
            candidate_name="John Doe",
            job_title="Software Engineer",
            company_name="Acme Corp",
        )
        assert "John Doe" in body
        assert "Software Engineer" in body
        assert "Acme Corp" in body


# ============================================================================
# BaseSkills — Urgency detection
# ============================================================================


class TestUrgencyDetection:
    def test_critical_urgency(self):
        skills = BaseSkills()
        email = {"subject": "URGENT: Server down", "body": "Fix immediately"}
        assert skills.detect_urgency(email) == "critical"

    def test_high_urgency(self):
        skills = BaseSkills()
        email = {"subject": "Important deadline", "body": "Due tomorrow"}
        assert skills.detect_urgency(email) == "high"

    def test_medium_urgency(self):
        skills = BaseSkills()
        email = {"subject": "Follow up", "body": "Please reply soon"}
        assert skills.detect_urgency(email) == "medium"

    def test_low_urgency(self):
        skills = BaseSkills()
        email = {"subject": "Hello", "body": "Just wanted to say hi"}
        assert skills.detect_urgency(email) == "low"


# ============================================================================
# BaseSkills — Contact extraction
# ============================================================================


class TestContactExtraction:
    def test_extract_email(self):
        skills = BaseSkills()
        result = skills.extract_contact_info("Contact me at alice@example.com")
        assert result["email"] == "alice@example.com"

    def test_extract_phone(self):
        skills = BaseSkills()
        result = skills.extract_contact_info("Call me at +1 555-123-4567")
        assert result["phone"] is not None

    def test_no_contact_info(self):
        skills = BaseSkills()
        result = skills.extract_contact_info("Hello world")
        assert result["email"] is None
        assert result["name"] is None


# ============================================================================
# BaseSkills — Follow-up date
# ============================================================================


class TestFollowUpDate:
    def test_follow_up_is_future(self):
        skills = BaseSkills()
        date_str = skills.suggest_follow_up_date()
        follow_up = datetime.fromisoformat(date_str).date()
        today = datetime.now(timezone.utc).date()
        assert follow_up > today

    def test_follow_up_is_weekday(self):
        skills = BaseSkills()
        date_str = skills.suggest_follow_up_date()
        follow_up = datetime.fromisoformat(date_str)
        # 0=Monday ... 4=Friday are weekdays
        assert follow_up.weekday() < 5


# ============================================================================
# HRSkills — WhatsApp report formatting
# ============================================================================


class TestWhatsAppFormatting:
    def test_format_report(self):
        skills = HRSkills()
        report = {
            "new_candidates": 5,
            "shortlisted": 3,
            "interviews_scheduled": 2,
            "hires": 1,
            "rejections": 1,
            "emails_processed": 50,
            "pipeline": {
                "applied": 10,
                "screened": 5,
                "interview": 3,
                "offer": 1,
            },
        }
        msg = skills.format_report_for_whatsapp(report)
        assert "HR Weekly Report" in msg
        assert "New CVs: 5" in msg
        assert "Hires: 1" in msg
        assert "Pipeline:" in msg
