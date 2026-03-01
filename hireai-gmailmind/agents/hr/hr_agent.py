"""HR Specialist Agent — handles recruitment email workflows.

Classifies HR-related emails (CV applications, interview requests,
candidate follow-ups, etc.) and processes them through the appropriate
pipeline using CVProcessor, CandidateTracker, and InterviewScheduler.
"""

import logging
import re
from typing import Any

from agents.base_agent import BaseAgent
from agents.hr.candidate_tracker import CandidateTracker
from agents.hr.cv_processor import CVProcessor
from agents.hr.hr_templates import HR_TEMPLATES
from agents.hr.interview_scheduler import InterviewScheduler

logger = logging.getLogger(__name__)


class HRAgent(BaseAgent):
    """HR recruitment email management agent."""

    agent_name = "GmailMind HR Agent"
    industry = "hr"
    supported_tiers = ["tier2", "tier3"]

    def __init__(self) -> None:
        self.cv_processor = CVProcessor()
        self.candidate_tracker = CandidateTracker()
        self.interview_scheduler = InterviewScheduler()

    # ------------------------------------------------------------------
    # Classification keywords per HR category
    # ------------------------------------------------------------------

    _HR_CATEGORIES = {
        "cv_application": [
            r"cv", r"resume", r"application", r"applying",
            r"candidate", r"portfolio", r"cover letter",
            r"job application", r"apply", r"applicant",
        ],
        "interview_request": [
            r"interview", r"meeting", r"schedule",
            r"availability", r"slot", r"time for",
        ],
        "candidate_followup": [
            r"follow.?up", r"status", r"update",
            r"any news", r"checking in", r"heard back",
        ],
        "offer_acceptance": [
            r"accept", r"accepting", r"happy to join",
            r"pleased to accept", r"looking forward to joining",
        ],
        "offer_rejection": [
            r"decline", r"declining", r"other opportunity",
            r"not able to accept", r"regret to inform",
        ],
        "job_inquiry": [
            r"open position", r"hiring", r"vacancy",
            r"job opening", r"looking for work", r"opportunities",
        ],
        "client_update": [
            r"requirement", r"mandate", r"position update",
            r"client", r"headcount",
        ],
    }

    # ------------------------------------------------------------------
    # Abstract method implementations
    # ------------------------------------------------------------------

    def get_system_prompt(self, tier: str) -> str:
        """Return the HR-specific system prompt."""
        return (
            "You are an expert HR recruitment email assistant. "
            "You help recruiters manage candidate applications, "
            "schedule interviews, and communicate professionally. "
            "Always be warm, professional, and encouraging to candidates. "
            "For internal client emails, be concise and data-driven."
        )

    def get_available_tools(self, tier: str) -> list[str]:
        """Return HR-specific tools based on tier."""
        if tier == "tier2":
            return [
                "read_emails", "label_email", "search_emails",
                "reply_to_email", "create_draft", "send_escalation_alert",
                "schedule_followup", "cv_processing", "interview_scheduler",
                "candidate_tracker",
            ]
        # tier3 — everything
        return [
            "read_emails", "label_email", "search_emails",
            "reply_to_email", "create_draft", "send_email",
            "send_escalation_alert", "schedule_followup",
            "create_calendar_event", "get_crm_contact", "update_crm",
            "cv_processing", "interview_scheduler", "candidate_tracker",
        ]

    def classify_email(self, email: dict) -> str:
        """Classify an email into an HR-specific category.

        Categories: cv_application, interview_request, candidate_followup,
                    client_update, job_inquiry, offer_acceptance,
                    offer_rejection, other.

        Args:
            email: Email dict with 'subject' and 'body' keys.

        Returns:
            Category string.
        """
        subject = (email.get("subject", "") or "").lower()
        body = (email.get("body", "") or email.get("snippet", "") or "").lower()
        text = f"{subject} {body}"

        for category, patterns in self._HR_CATEGORIES.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    logger.info(
                        "%s: Classified email as '%s' (matched: %s)",
                        self.agent_name, category, pattern,
                    )
                    return category

        logger.info("%s: Classified email as 'other' (no HR keyword match).", self.agent_name)
        return "other"

    # ------------------------------------------------------------------
    # Main email processing pipeline
    # ------------------------------------------------------------------

    def process_email(
        self,
        email: dict,
        user_config: dict,
        tier: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Process an email through the HR pipeline.

        Args:
            email: Email dict.
            user_config: Business configuration.
            tier: User's subscription tier.
            user_id: The recruiter/user ID.

        Returns:
            Dict with action taken and details.
        """
        category = self.classify_email(email)
        company_name = user_config.get("business_name", "Our Company")
        sender_email = self._get_sender_email(email)

        logger.info(
            "%s: Processing %s email from %s for user=%s",
            self.agent_name, category, sender_email, user_id,
        )

        if category == "cv_application":
            return self._handle_cv_application(email, user_id, company_name)

        if category == "interview_request":
            return self._handle_interview_request(email, user_id, company_name)

        if category == "candidate_followup":
            return self._handle_candidate_followup(email, user_id, sender_email, company_name)

        if category == "job_inquiry":
            return {
                "action": "draft_reply",
                "category": category,
                "details": "Drafted reply about open positions.",
            }

        if category in ("offer_acceptance", "offer_rejection"):
            return self._handle_offer_response(email, user_id, sender_email, category)

        # Default: label and archive
        return {
            "action": "label_and_archive",
            "category": category,
            "details": "Labeled and archived (no HR action needed).",
        }

    # ------------------------------------------------------------------
    # Category handlers
    # ------------------------------------------------------------------

    def _handle_cv_application(
        self,
        email: dict,
        user_id: str,
        company_name: str,
    ) -> dict[str, Any]:
        """Handle a CV/application email."""
        subject = email.get("subject", "")
        body = email.get("body", "") or email.get("snippet", "")
        sender_email = self._get_sender_email(email)

        # Step 1: Extract CV info
        cv_info = self.cv_processor.extract_cv_info(body, subject)
        if not cv_info.get("email"):
            cv_info["email"] = sender_email

        # Step 2: Determine job title from subject
        job_title = self._extract_job_title(subject) or "General Application"

        # Step 3: Create/update candidate in tracker
        candidate_id = self.candidate_tracker.create_candidate(
            user_id=user_id,
            cv_info=cv_info,
            job_title=job_title,
            source_email_id=email.get("id", ""),
        )

        # Step 4: Score candidate (use empty requirements if none found)
        score = self.cv_processor.score_candidate(cv_info, {})

        # Step 5: Update score in DB
        if candidate_id:
            db = SessionLocal()
            try:
                from sqlalchemy import text as sa_text
                db.execute(
                    sa_text("UPDATE candidates SET cv_score = :score WHERE id = :cid"),
                    {"score": score, "cid": candidate_id},
                )
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()

        # Step 6: Decide action based on score
        candidate_name = cv_info.get("name") or sender_email

        if score >= 70:
            # High score — draft interview invite
            self.candidate_tracker.update_stage(user_id, cv_info["email"], "screened", "Auto-screened: high score")
            template = HR_TEMPLATES["interview_invite"].format(
                candidate_name=candidate_name,
                job_title=job_title,
                available_slots="(slots will be shared separately)",
                duration=60,
                interview_type="video",
                company_name=company_name,
            )
            action = "draft_interview_invite"
        elif score < 40:
            # Low score — draft polite rejection
            self.candidate_tracker.update_stage(user_id, cv_info["email"], "rejected", "Auto-screened: low score")
            template = HR_TEMPLATES["rejection_polite"].format(
                candidate_name=candidate_name,
                job_title=job_title,
                company_name=company_name,
            )
            action = "draft_rejection"
        else:
            # Mid score — acknowledge and mark as screened
            self.candidate_tracker.update_stage(user_id, cv_info["email"], "screened", "Auto-screened: mid score")
            template = HR_TEMPLATES["cv_received"].format(
                candidate_name=candidate_name,
                job_title=job_title,
                company_name=company_name,
            )
            action = "send_acknowledgment"

        self.log_action(user_id, action, f"CV from {sender_email}, score={score}")

        return {
            "action": action,
            "category": "cv_application",
            "candidate_id": candidate_id,
            "cv_score": score,
            "draft_body": template,
            "details": f"Processed CV from {candidate_name} (score: {score}/100).",
        }

    def _handle_interview_request(
        self,
        email: dict,
        user_id: str,
        company_name: str,
    ) -> dict[str, Any]:
        """Handle an interview scheduling request."""
        sender_email = self._get_sender_email(email)

        slots = self.interview_scheduler.find_available_slots(user_id)
        slots_text = "\n".join(f"  - {s}" for s in slots[:5]) if slots else "  (No slots available)"

        self.log_action(user_id, "find_interview_slots", f"Found {len(slots)} slots for {sender_email}")

        return {
            "action": "reply_with_slots",
            "category": "interview_request",
            "available_slots": slots[:5],
            "details": f"Found {len(slots)} available interview slots.",
        }

    def _handle_candidate_followup(
        self,
        email: dict,
        user_id: str,
        sender_email: str,
        company_name: str,
    ) -> dict[str, Any]:
        """Handle a candidate follow-up inquiry."""
        candidate = self.candidate_tracker.get_candidate(user_id, sender_email)

        if candidate:
            stage = candidate.get("stage", "applied")
            candidate_name = candidate.get("name") or sender_email
            job_title = candidate.get("job_title_applied", "the position")

            template = HR_TEMPLATES["follow_up_candidate"].format(
                candidate_name=candidate_name,
                job_title=job_title,
                company_name=company_name,
            )

            return {
                "action": "reply_with_status",
                "category": "candidate_followup",
                "current_stage": stage,
                "draft_body": template,
                "details": f"Candidate {candidate_name} is at stage '{stage}'.",
            }

        return {
            "action": "draft_generic_reply",
            "category": "candidate_followup",
            "details": "Candidate not found in database, drafting generic reply.",
        }

    def _handle_offer_response(
        self,
        email: dict,
        user_id: str,
        sender_email: str,
        category: str,
    ) -> dict[str, Any]:
        """Handle offer acceptance or rejection."""
        if category == "offer_acceptance":
            self.candidate_tracker.update_stage(user_id, sender_email, "hired", "Offer accepted")
            action = "mark_hired"
        else:
            self.candidate_tracker.update_stage(user_id, sender_email, "rejected", "Offer declined")
            action = "mark_rejected"

        self.log_action(user_id, action, f"{category} from {sender_email}")

        return {
            "action": action,
            "category": category,
            "details": f"Candidate {sender_email}: {category}.",
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_sender_email(self, email: dict) -> str:
        """Extract sender email string from email dict."""
        sender = email.get("sender", {})
        if isinstance(sender, dict):
            return sender.get("email", sender.get("name", "unknown"))
        return str(sender)

    def _extract_job_title(self, subject: str) -> str | None:
        """Try to extract a job title from the email subject."""
        patterns = [
            r"(?:application|applying|cv|resume)\s*(?:for|[-–:])\s*(.+)",
            r"(.+?)\s*(?:application|position|role|vacancy)",
        ]
        for pattern in patterns:
            match = re.search(pattern, subject, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None


# Needed for _handle_cv_application DB update
from config.database import SessionLocal  # noqa: E402
