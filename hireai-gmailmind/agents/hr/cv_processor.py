"""CV / resume processing for HR agent.

Extracts candidate information from emails, detects CV-related emails,
and scores candidates against job requirements.
"""

import json
import logging
import re
from typing import Any

from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Keywords that indicate an email contains a CV or job application
_CV_KEYWORDS = [
    "cv", "resume", "application", "applying", "candidate",
    "portfolio", "cover letter", "job application", "position",
    "apply", "applicant", "attached my resume", "attached my cv",
]


class CVProcessor:
    """Processes CV/resume emails and scores candidates."""

    def is_cv_email(self, email: dict) -> bool:
        """Check if an email contains CV/resume keywords.

        Args:
            email: Email dict with 'subject' and 'body' keys.

        Returns:
            True if the email appears to be a CV/application.
        """
        subject = (email.get("subject", "") or "").lower()
        body = (email.get("body", "") or email.get("snippet", "") or "").lower()
        text = f"{subject} {body}"

        for keyword in _CV_KEYWORDS:
            if keyword in text:
                logger.info("CVProcessor: CV keyword '%s' found in email.", keyword)
                return True

        return False

    def extract_cv_info(self, email_body: str, subject: str) -> dict[str, Any]:
        """Extract candidate information from email body using GPT-4o.

        Falls back to regex extraction if OpenAI is not available.

        Args:
            email_body: The email body text.
            subject: The email subject line.

        Returns:
            Dict with candidate info fields.
        """
        # Try GPT-4o extraction first
        if OPENAI_API_KEY:
            try:
                return self._extract_with_gpt(email_body, subject)
            except Exception as exc:
                logger.warning("CVProcessor: GPT extraction failed, falling back to regex: %s", exc)

        # Fallback to regex extraction
        return self._extract_with_regex(email_body, subject)

    def _extract_with_gpt(self, email_body: str, subject: str) -> dict[str, Any]:
        """Extract candidate info using GPT-4o."""
        import httpx

        prompt = (
            "Extract candidate info from this email. Return JSON only with these keys: "
            "name (str or null), email (str or null), phone (str or null), "
            "experience_years (int or 0), skills (list of str), "
            "current_role (str or null), location (str or null), "
            "education (str or null), has_cv_attachment (bool).\n\n"
            f"Subject: {subject}\n\n"
            f"Body:\n{email_body[:3000]}"
        )

        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 500,
            },
            timeout=30,
        )
        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        # Strip markdown code blocks if present
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\n?", "", content)
            content = re.sub(r"\n?```$", "", content)

        result = json.loads(content)
        logger.info("CVProcessor: GPT extracted candidate info: %s", result.get("name"))
        return self._normalize_cv_info(result)

    def _extract_with_regex(self, email_body: str, subject: str) -> dict[str, Any]:
        """Extract candidate info using regex patterns (fallback)."""
        text = f"{subject}\n{email_body}"

        # Extract email
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        email = email_match.group(0) if email_match else None

        # Extract phone
        phone_match = re.search(r"[\+]?[\d\s\-\(\)]{7,15}", text)
        phone = phone_match.group(0).strip() if phone_match else None

        # Extract name from subject (common pattern: "Application - Name")
        name = None
        name_match = re.search(r"(?:application|cv|resume)\s*[-–:]\s*(.+)", subject, re.IGNORECASE)
        if name_match:
            name = name_match.group(1).strip()

        # Extract experience years
        exp_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience)?", text, re.IGNORECASE)
        experience_years = int(exp_match.group(1)) if exp_match else 0

        # Check for attachment keywords
        has_attachment = any(
            kw in text.lower()
            for kw in ["attached", "attachment", "enclosed", "find my cv", "find my resume"]
        )

        result = {
            "name": name,
            "email": email,
            "phone": phone,
            "experience_years": experience_years,
            "skills": [],
            "current_role": None,
            "location": None,
            "education": None,
            "has_cv_attachment": has_attachment,
        }
        logger.info("CVProcessor: Regex extracted candidate info: name=%s", name)
        return result

    def _normalize_cv_info(self, raw: dict) -> dict[str, Any]:
        """Ensure all expected fields are present with correct types."""
        return {
            "name": raw.get("name"),
            "email": raw.get("email"),
            "phone": raw.get("phone"),
            "experience_years": int(raw.get("experience_years", 0) or 0),
            "skills": list(raw.get("skills", []) or []),
            "current_role": raw.get("current_role"),
            "location": raw.get("location"),
            "education": raw.get("education"),
            "has_cv_attachment": bool(raw.get("has_cv_attachment", False)),
        }

    def score_candidate(self, cv_info: dict, job_requirements: dict) -> int:
        """Score a candidate 0-100 against job requirements.

        Scoring:
            - Skills match: up to 50 points
            - Experience match: up to 30 points
            - Location match: up to 20 points

        Args:
            cv_info: Candidate info dict from extract_cv_info.
            job_requirements: Job requirements dict with required_skills,
                              min_experience_years, location.

        Returns:
            Integer score 0-100.
        """
        score = 0

        # Skills match (up to 50 points)
        required_skills = [s.lower() for s in (job_requirements.get("required_skills") or [])]
        candidate_skills = [s.lower() for s in (cv_info.get("skills") or [])]

        if required_skills:
            matched = sum(1 for s in required_skills if s in candidate_skills)
            score += int((matched / len(required_skills)) * 50)
        else:
            # No required skills specified — give benefit of the doubt
            score += 25

        # Experience match (up to 30 points)
        min_exp = int(job_requirements.get("min_experience_years", 0) or 0)
        candidate_exp = int(cv_info.get("experience_years", 0) or 0)

        if min_exp == 0:
            score += 30
        elif candidate_exp >= min_exp:
            score += 30
        elif candidate_exp > 0:
            score += int((candidate_exp / min_exp) * 30)

        # Location match (up to 20 points)
        req_location = (job_requirements.get("location") or "").lower()
        cand_location = (cv_info.get("location") or "").lower()

        if not req_location or req_location == "remote":
            score += 20
        elif cand_location and (req_location in cand_location or cand_location in req_location):
            score += 20
        elif cand_location == "remote":
            score += 15

        final_score = min(score, 100)
        logger.info(
            "CVProcessor: Scored candidate %s = %d/100",
            cv_info.get("name", "unknown"), final_score,
        )
        return final_score
