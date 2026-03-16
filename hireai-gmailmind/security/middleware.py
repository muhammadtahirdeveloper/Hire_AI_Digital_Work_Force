"""FastAPI middleware for API key authentication.

Provides dependency injection for protecting routes with API key auth.
"""

import logging
from typing import Optional

from fastapi import Header, HTTPException, Request

from security.auth import APIKeyManager

logger = logging.getLogger(__name__)

# Public routes that don't require API key authentication
PUBLIC_ROUTES = {
    "/health",
    "/security-status",
    "/auth/setup",
    "/auth/complete-setup",
    "/auth/verify-email",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/auth/register",
    "/auth/login",
    "/auth/google-login",
    "/auth/google",
    "/auth/google/callback",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/health/platform",
    "/api/reviews/public",
    "/api/support/chat",
}


async def verify_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None)
) -> dict:
    """Verify API key from request header.

    This dependency can be used on individual routes or globally.
    Public routes (health, docs, OAuth callbacks) are automatically exempt.

    Args:
        request: FastAPI request object
        x_api_key: API key from X-API-Key header

    Returns:
        dict: User info {user_id, key_id, name}

    Raises:
        HTTPException: 401 if key missing, 403 if key invalid
    """
    # Check if route is public
    path = request.url.path
    if path in PUBLIC_ROUTES or path.startswith("/auth/"):
        logger.debug(f"[verify_api_key] Public route accessed: {path}")
        return {"user_id": "public", "key_id": None, "name": "public"}

    # Require API key for protected routes
    if not x_api_key:
        logger.warning(f"[verify_api_key] Missing API key for {path}")
        raise HTTPException(
            status_code=401,
            detail="API key required. Include X-API-Key header."
        )

    # Validate API key
    manager = APIKeyManager()
    user_info = manager.validate_api_key(x_api_key)

    if not user_info:
        logger.warning(f"[verify_api_key] Invalid API key attempt for {path}")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )

    logger.debug(f"[verify_api_key] Authenticated user={user_info['user_id']} for {path}")
    return user_info


async def get_current_user(
    x_api_key: Optional[str] = Header(None)
) -> Optional[dict]:
    """Get current user from API key without raising exceptions.

    Useful for optional authentication.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        dict: User info if valid key provided
        None: If no key or invalid key
    """
    if not x_api_key:
        return None

    manager = APIKeyManager()
    return manager.validate_api_key(x_api_key)
