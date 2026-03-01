"""HR email templates for candidate communication.

Each template uses Python str.format() placeholders.
Usage::

    from agents.hr.hr_templates import HR_TEMPLATES
    body = HR_TEMPLATES['cv_received'].format(
        candidate_name="John",
        job_title="Software Engineer",
        company_name="Acme Corp",
    )
"""

HR_TEMPLATES = {
    "cv_received": (
        "Dear {candidate_name},\n"
        "\n"
        "Thank you for applying for the {job_title} position.\n"
        "We have received your application and will review it shortly.\n"
        "We will be in touch within 3-5 business days.\n"
        "\n"
        "Best regards,\n"
        "{company_name} HR Team"
    ),
    "interview_invite": (
        "Dear {candidate_name},\n"
        "\n"
        "We are pleased to invite you for an interview for the {job_title} position.\n"
        "Please let us know your availability for the following slots:\n"
        "{available_slots}\n"
        "\n"
        "Interview Duration: {duration} minutes\n"
        "Format: {interview_type}\n"
        "\n"
        "Best regards,\n"
        "{company_name} HR Team"
    ),
    "interview_confirmation": (
        "Dear {candidate_name},\n"
        "\n"
        "Your interview has been confirmed:\n"
        "Date: {interview_date}\n"
        "Time: {interview_time}\n"
        "Format: {interview_type}\n"
        "{location_or_link}\n"
        "\n"
        "Please let us know if you need to reschedule.\n"
        "\n"
        "Best regards,\n"
        "{company_name} HR Team"
    ),
    "rejection_polite": (
        "Dear {candidate_name},\n"
        "\n"
        "Thank you for your interest in the {job_title} position\n"
        "and for taking the time to apply.\n"
        "\n"
        "After careful consideration, we have decided to move forward\n"
        "with other candidates whose experience more closely matches\n"
        "our current needs.\n"
        "\n"
        "We will keep your profile on file for future opportunities.\n"
        "\n"
        "Best regards,\n"
        "{company_name} HR Team"
    ),
    "follow_up_candidate": (
        "Dear {candidate_name},\n"
        "\n"
        "I wanted to follow up regarding your application for {job_title}.\n"
        "We are still reviewing candidates and will update you soon.\n"
        "\n"
        "Best regards,\n"
        "{company_name} HR Team"
    ),
    "client_position_update": (
        "Dear {client_name},\n"
        "\n"
        "Update on your {job_title} requirement:\n"
        "- CVs received: {cv_count}\n"
        "- Shortlisted: {shortlisted_count}\n"
        "- Interviews scheduled: {interview_count}\n"
        "\n"
        "We will share candidate profiles by {expected_date}.\n"
        "\n"
        "Best regards,\n"
        "{recruiter_name}"
    ),
}
