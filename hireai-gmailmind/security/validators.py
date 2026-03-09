"""Input validation and sanitization for GmailMind.

Prevents injection attacks and ensures data integrity.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def sanitize_string(value: str, max_length: int = 255) -> str:
    """Sanitize a string by removing dangerous characters.

    Args:
        value: String to sanitize
        max_length: Maximum allowed length

    Returns:
        str: Sanitized string
    """
    if not isinstance(value, str):
        value = str(value)

    # Remove null bytes
    value = value.replace('\x00', '')

    # Remove other control characters (except newlines and tabs which might be legitimate)
    value = re.sub(r'[\x01-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', value)

    # Strip leading/trailing whitespace (after removing control chars)
    value = value.strip()

    # Limit length
    if len(value) > max_length:
        value = value[:max_length]
        logger.debug("[sanitize_string] Truncated string to %d chars", max_length)

    return value


def validate_email(email: str) -> bool:
    """Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False

    # RFC 5322 simplified regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    # Additional checks
    if len(email) > 254:  # RFC 5321
        return False

    if '..' in email:  # No consecutive dots
        return False

    return bool(re.match(pattern, email))


def validate_user_id(user_id: str) -> bool:
    """Validate user ID format.

    Only allows alphanumeric characters, underscores, and hyphens.
    This prevents path traversal and SQL injection attempts.

    Args:
        user_id: User ID to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not user_id or not isinstance(user_id, str):
        return False

    # Max 50 characters
    if len(user_id) > 50:
        return False

    # Only alphanumeric, underscore, hyphen
    pattern = r'^[a-zA-Z0-9_-]+$'

    return bool(re.match(pattern, user_id))


def validate_phone(phone: str) -> bool:
    """Validate phone number format.

    Accepts various formats: +1234567890, (123) 456-7890, etc.

    Args:
        phone: Phone number to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not phone or not isinstance(phone, str):
        return False

    # Remove common separators
    cleaned = re.sub(r'[\s\(\)\-\.]', '', phone)

    # Optional + prefix, then 10-15 digits
    pattern = r'^\+?[0-9]{10,15}$'

    return bool(re.match(pattern, cleaned))


def sanitize_dict(data: dict, allowed_keys: list) -> dict:
    """Sanitize dictionary by keeping only allowed keys and sanitizing values.

    Args:
        data: Dictionary to sanitize
        allowed_keys: List of allowed key names

    Returns:
        dict: Sanitized dictionary with only allowed keys
    """
    if not isinstance(data, dict):
        logger.warning("[sanitize_dict] Input is not a dict: %s", type(data))
        return {}

    sanitized = {}

    for key in allowed_keys:
        if key in data:
            value = data[key]

            # Sanitize string values
            if isinstance(value, str):
                sanitized[key] = sanitize_string(value)
            # Keep other types as-is (with logging)
            elif isinstance(value, (int, float, bool, list, dict)):
                sanitized[key] = value
            # Convert other types to string and sanitize
            else:
                sanitized[key] = sanitize_string(str(value))
                logger.debug("[sanitize_dict] Converted %s to string", type(value))

    # Log if keys were removed
    removed_keys = set(data.keys()) - set(allowed_keys)
    if removed_keys:
        logger.info("[sanitize_dict] Removed unauthorized keys: %s", removed_keys)

    return sanitized


def validate_url(url: str) -> bool:
    """Validate URL format.

    Args:
        url: URL to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    # Must start with http:// or https://
    pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'

    return bool(re.match(pattern, url))


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing dangerous characters.

    Prevents path traversal attacks.

    Args:
        filename: Filename to sanitize

    Returns:
        str: Safe filename
    """
    if not filename:
        return "unnamed"

    # Remove directory separators
    filename = filename.replace('/', '_').replace('\\', '_')

    # Remove parent directory references
    filename = filename.replace('..', '')

    # Keep only safe characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

    # Limit length
    if len(filename) > 255:
        filename = filename[:255]

    return filename or "unnamed"


def validate_json_safe(value: Any) -> bool:
    """Check if value is safe for JSON serialization.

    Args:
        value: Value to check

    Returns:
        bool: True if safe for JSON, False otherwise
    """
    if value is None:
        return True

    if isinstance(value, (str, int, float, bool)):
        return True

    if isinstance(value, (list, tuple)):
        return all(validate_json_safe(item) for item in value)

    if isinstance(value, dict):
        return all(
            isinstance(k, str) and validate_json_safe(v)
            for k, v in value.items()
        )

    # Complex types (objects, functions, etc.) are not safe
    return False


def sanitize_sql_identifier(identifier: str) -> str:
    """Sanitize SQL identifier (table/column name).

    Note: This is a backup. Always use parameterized queries.

    Args:
        identifier: SQL identifier to sanitize

    Returns:
        str: Sanitized identifier
    """
    if not identifier or not isinstance(identifier, str):
        return ""

    # Only allow alphanumeric and underscore
    identifier = re.sub(r'[^a-zA-Z0-9_]', '', identifier)

    # Don't allow starting with number
    if identifier and identifier[0].isdigit():
        identifier = '_' + identifier

    # Limit length
    if len(identifier) > 64:
        identifier = identifier[:64]

    return identifier
