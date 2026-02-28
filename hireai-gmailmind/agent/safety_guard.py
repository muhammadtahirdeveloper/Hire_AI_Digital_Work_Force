"""Safety guard that wraps every agent tool call.

The ``SafetyGuard`` enforces a set of hard rules that **cannot** be
overridden at runtime.  Before any tool is executed the guard's
``check_action`` method is called; if any rule is violated a
``SafetyViolationError`` is raised and the action is blocked.

Usage::

    from agent.safety_guard import safety_guard, SafetyViolationError

    allowed, reason = safety_guard.check_action("send_email", {
        "to": "user@example.com",
        "subject": "Hello",
        "body": "...",
    })
    if not allowed:
        raise SafetyViolationError(reason)

    # … proceed with the tool call
"""

import logging
import re
from typing import Any

from config.settings import DAILY_ACTION_LIMIT, MAX_RECIPIENTS_PER_SEND
from memory.short_term import session_memory

logger = logging.getLogger(__name__)


# ===========================================================================
# Custom exception
# ===========================================================================


class SafetyViolationError(Exception):
    """Raised when an agent action violates a hard safety rule."""

    def __init__(self, rule: str, reason: str) -> None:
        self.rule = rule
        self.reason = reason
        super().__init__(f"[SAFETY VIOLATION — {rule}] {reason}")


# ===========================================================================
# SafetyGuard
# ===========================================================================


class SafetyGuard:
    """Enforces hard safety rules on every agent action.

    Attributes:
        HARD_RULES: The immutable list of rule identifiers.
    """

    HARD_RULES: list[str] = [
        "never_delete_email_permanently",
        "never_send_mass_email_over_50",
        "never_share_credentials",
        "never_reply_to_spam",
        "never_take_financial_actions",
        "never_impersonate",
        "stop_if_daily_limit_exceeded",
    ]

    # Patterns that signal the body/subject might contain credentials
    _CREDENTIAL_PATTERNS: list[re.Pattern] = [
        re.compile(r"password\s*[:=]\s*\S+", re.IGNORECASE),
        re.compile(r"api[_-]?key\s*[:=]\s*\S+", re.IGNORECASE),
        re.compile(r"secret\s*[:=]\s*\S+", re.IGNORECASE),
        re.compile(r"token\s*[:=]\s*\S+", re.IGNORECASE),
        re.compile(r"bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
        re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", re.IGNORECASE),
    ]

    # Keywords that should trigger human escalation
    _ESCALATION_KEYWORDS: list[str] = [
        "legal",
        "lawsuit",
        "attorney",
        "lawyer",
        "complaint",
        "urgent",
        "emergency",
        "payment dispute",
        "chargeback",
        "fraud",
        "harassment",
        "threat",
        "subpoena",
        "regulatory",
        "compliance",
        "termination",
        "data breach",
        "confidential",
    ]

    # Spam signals in sender/subject/body
    _SPAM_PATTERNS: list[re.Pattern] = [
        re.compile(r"(buy\s+now|act\s+now|limited\s+time)", re.IGNORECASE),
        re.compile(r"(click\s+here|unsubscribe)", re.IGNORECASE),
        re.compile(r"(viagra|cialis|lottery|winner|prince)", re.IGNORECASE),
        re.compile(r"(earn\s+money|make\s+\$|free\s+gift)", re.IGNORECASE),
        re.compile(r"(nigerian|inheritance|million\s+dollars)", re.IGNORECASE),
        re.compile(r"\b(win|won|congratulations)\b", re.IGNORECASE),
        re.compile(r"\bfree\b.*\b(money|cash|prize|offer)\b", re.IGNORECASE),
        re.compile(r"\bnoreply@", re.IGNORECASE),
    ]

    # Financial action verbs to block
    _FINANCIAL_KEYWORDS: list[str] = [
        "wire transfer",
        "bank transfer",
        "send money",
        "payment",
        "invoice payment",
        "pay now",
        "bitcoin",
        "crypto",
        "wallet address",
        "routing number",
        "account number",
    ]

    # Actions that permanently delete data
    _DESTRUCTIVE_ACTIONS: set[str] = {
        "delete_email",
        "delete_email_permanently",
        "trash_email_permanently",
        "purge",
        "expunge",
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_action(self, action: str, params: dict[str, Any]) -> tuple[bool, str]:
        """Run ALL hard rules against the proposed action.

        This method must be called before every tool invocation.

        Args:
            action: The tool / function name about to be executed.
            params: The keyword arguments being passed to the tool.

        Returns:
            A ``(is_safe, reason)`` tuple.  ``is_safe`` is True when the
            action is permitted; when False, ``reason`` explains which rule
            was violated.

        Raises:
            SafetyViolationError: If a hard rule is violated (in addition
                to returning False, the error is raised so callers that
                forget to check the tuple are still protected).
        """
        logger.info("SafetyGuard.check_action: action=%s, params_keys=%s", action, list(params.keys()))

        # 1. Daily limit
        violation = self._check_daily_limit()
        if violation:
            return violation

        # 2. Permanent deletion
        violation = self._check_permanent_deletion(action)
        if violation:
            return violation

        # 3. Mass email
        violation = self._check_mass_email(action, params)
        if violation:
            return violation

        # 4. Credential leakage
        violation = self._check_credential_leakage(action, params)
        if violation:
            return violation

        # 5. Replying to spam
        violation = self._check_spam_reply(action, params)
        if violation:
            return violation

        # 6. Financial actions
        violation = self._check_financial_action(action, params)
        if violation:
            return violation

        # 7. Impersonation
        violation = self._check_impersonation(action, params)
        if violation:
            return violation

        logger.info("SafetyGuard.check_action: All rules passed for action=%s.", action)
        return (True, "")

    def is_daily_limit_exceeded(self) -> bool:
        """Check whether today's action count exceeds the configured limit.

        Returns:
            True if the daily limit has been reached or exceeded.
        """
        count = session_memory.action_count()
        exceeded = count >= DAILY_ACTION_LIMIT
        if exceeded:
            logger.warning(
                "SafetyGuard: Daily action limit reached (%d/%d).",
                count,
                DAILY_ACTION_LIMIT,
            )
        return exceeded

    def contains_escalation_keywords(self, text: str) -> bool:
        """Check if the text contains keywords that require human escalation.

        Args:
            text: Email body, subject, or snippet to analyse.

        Returns:
            True if one or more escalation keywords are detected.
        """
        text_lower = text.lower()
        found = [kw for kw in self._ESCALATION_KEYWORDS if kw in text_lower]
        if found:
            logger.info(
                "SafetyGuard: Escalation keywords detected: %s", found
            )
            return True
        return False

    def is_spam(self, email: dict[str, Any]) -> bool:
        """Heuristic spam detector for an email dict.

        Checks the ``subject``, ``body``, ``snippet``, and ``sender`` fields
        against known spam patterns.

        Args:
            email: A dict with at least some of: subject, body, snippet,
                   sender (str or dict with 'email' key).

        Returns:
            True if the email is likely spam.
        """
        text_parts: list[str] = []
        for key in ("subject", "body", "snippet"):
            val = email.get(key, "")
            if val:
                text_parts.append(str(val))

        sender = email.get("sender", "") or email.get("from", "")
        if isinstance(sender, dict):
            sender = sender.get("email", "")
        text_parts.append(str(sender))

        combined = " ".join(text_parts)

        matches = 0
        for pattern in self._SPAM_PATTERNS:
            if pattern.search(combined):
                matches += 1

        is_spam = matches >= 2
        if is_spam:
            logger.warning(
                "SafetyGuard: Email flagged as spam (%d pattern matches).", matches
            )
        return is_spam

    # ------------------------------------------------------------------
    # Decorator for wrapping tool calls
    # ------------------------------------------------------------------

    def guard(self, action: str, params: dict[str, Any]) -> None:
        """Convenience method that raises on violation.

        Call this as the first line inside every tool wrapper::

            safety_guard.guard("send_email", {"to": to, ...})

        Args:
            action: Tool / function name.
            params: Tool arguments.

        Raises:
            SafetyViolationError: If any hard rule is violated.
        """
        is_safe, reason = self.check_action(action, params)
        if not is_safe:
            raise SafetyViolationError(rule=reason.split(":")[0].strip(), reason=reason)

    # ------------------------------------------------------------------
    # Internal rule checks — each returns None (pass) or (False, reason)
    # ------------------------------------------------------------------

    def _check_daily_limit(self) -> tuple[bool, str] | None:
        """Rule: stop_if_daily_limit_exceeded."""
        if self.is_daily_limit_exceeded():
            reason = (
                f"stop_if_daily_limit_exceeded: Daily action limit of "
                f"{DAILY_ACTION_LIMIT} has been reached. No further actions "
                f"are permitted this session."
            )
            logger.warning("SafetyGuard: %s", reason)
            return (False, reason)
        return None

    def _check_permanent_deletion(self, action: str) -> tuple[bool, str] | None:
        """Rule: never_delete_email_permanently."""
        if action in self._DESTRUCTIVE_ACTIONS:
            reason = (
                f"never_delete_email_permanently: Action '{action}' would "
                f"permanently delete data. This is prohibited."
            )
            logger.warning("SafetyGuard: %s", reason)
            return (False, reason)
        return None

    def _check_mass_email(
        self, action: str, params: dict[str, Any]
    ) -> tuple[bool, str] | None:
        """Rule: never_send_mass_email_over_50."""
        if action not in ("send_email", "create_draft"):
            return None

        to = params.get("to", "")
        recipients: list[str] = []

        if isinstance(to, str):
            recipients = [addr.strip() for addr in to.split(",") if addr.strip()]
        elif isinstance(to, list):
            recipients = to

        if len(recipients) > MAX_RECIPIENTS_PER_SEND:
            reason = (
                f"never_send_mass_email_over_50: Attempted to send to "
                f"{len(recipients)} recipients (limit: {MAX_RECIPIENTS_PER_SEND})."
            )
            logger.warning("SafetyGuard: %s", reason)
            return (False, reason)
        return None

    def _check_credential_leakage(
        self, action: str, params: dict[str, Any]
    ) -> tuple[bool, str] | None:
        """Rule: never_share_credentials."""
        if action not in ("send_email", "reply_to_email", "create_draft"):
            return None

        body = str(params.get("body", ""))
        subject = str(params.get("subject", ""))
        text_to_check = f"{subject} {body}"

        for pattern in self._CREDENTIAL_PATTERNS:
            match = pattern.search(text_to_check)
            if match:
                reason = (
                    f"never_share_credentials: Outgoing message appears to "
                    f"contain credentials or secrets (matched: {pattern.pattern!r})."
                )
                logger.warning("SafetyGuard: %s", reason)
                return (False, reason)
        return None

    def _check_spam_reply(
        self, action: str, params: dict[str, Any]
    ) -> tuple[bool, str] | None:
        """Rule: never_reply_to_spam."""
        if action != "reply_to_email":
            return None

        email_context = params.get("email_context", {})
        if email_context and self.is_spam(email_context):
            reason = (
                "never_reply_to_spam: The original email has been flagged "
                "as spam. Replying is prohibited."
            )
            logger.warning("SafetyGuard: %s", reason)
            return (False, reason)
        return None

    def _check_financial_action(
        self, action: str, params: dict[str, Any]
    ) -> tuple[bool, str] | None:
        """Rule: never_take_financial_actions."""
        if action not in ("send_email", "reply_to_email", "create_draft"):
            return None

        body = str(params.get("body", "")).lower()
        subject = str(params.get("subject", "")).lower()
        combined = f"{subject} {body}"

        for keyword in self._FINANCIAL_KEYWORDS:
            if keyword in combined:
                reason = (
                    f"never_take_financial_actions: Outgoing message references "
                    f"financial action '{keyword}'. Agent cannot commit to "
                    f"financial transactions — escalate to human."
                )
                logger.warning("SafetyGuard: %s", reason)
                return (False, reason)
        return None

    def _check_impersonation(
        self, action: str, params: dict[str, Any]
    ) -> tuple[bool, str] | None:
        """Rule: never_impersonate."""
        if action not in ("send_email", "reply_to_email", "create_draft"):
            return None

        body = str(params.get("body", "")).lower()

        impersonation_phrases = [
            "i am the ceo",
            "i am the owner",
            "this is the ceo",
            "speaking on behalf of the board",
            "as the legal representative",
            "i am authorized to sign",
            "i have authority to",
            "acting as director",
        ]

        for phrase in impersonation_phrases:
            if phrase in body:
                reason = (
                    f"never_impersonate: Outgoing message contains "
                    f"impersonation phrase '{phrase}'. The agent must not "
                    f"represent itself as a human authority figure."
                )
                logger.warning("SafetyGuard: %s", reason)
                return (False, reason)
        return None


# ===========================================================================
# Module-level singleton — import and use directly.
# ===========================================================================

safety_guard = SafetyGuard()
