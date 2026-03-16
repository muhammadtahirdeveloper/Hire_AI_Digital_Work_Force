"""FastAPI middleware for API key + JWT Bearer authentication.

Provides dependency injection for protecting routes with API key or JWT auth.
"""

import logging
import os
from typing import Optional

import jwt
from fastapi import Header, HTTPException, Request
from fastapi.responses import JSONResponse

from config.settings import JWT_SECRET, JWT_ALGORITHM

logger = logging.getLogger(__name__)

# Public routes that don't require authentication
PUBLIC_ROUTES = {
    "/health",
    "/security-status",
    "/auth/setup",
    "/auth/complete-setup",
    "/auth/mark-complete",
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
    "/api/agent/status",
    "/api/dashboard/stats",
    "/api/dashboard/weekly-summary",
    "/api/dashboard/daily-volume",
    "/api/emails/recent",
    "/api/agent/provider-health",
    "/api/health/user",
    "/api/reviews",
}


async def verify_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None)
) -> dict:
    """Verify authentication via JWT Bearer token or API key.

    Checks in order:
    1. Public routes — always allowed.
    2. JWT Bearer token in Authorization header.
    3. Legacy X-API-Key header.

    Args:
        request: FastAPI request object
        x_api_key: API key from X-API-Key header

    Returns:
        dict: User info {user_id, key_id, name}

    Raises:
        HTTPException: 401 if no valid auth provided
    """
    path = request.url.path

    # 1. Public routes — no auth needed
    if path in PUBLIC_ROUTES or path.startswith("/auth/"):
        logger.debug("[verify_api_key] Public route accessed: %s", path)
        return {"user_id": "public", "key_id": None, "name": "public"}

    # 2. Try JWT Bearer token first (sent by frontend)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            request.state.user = payload
            logger.debug("[verify_api_key] JWT auth OK user=%s for %s", payload.get("email"), path)
            return {
                "user_id": payload.get("sub", "jwt-user"),
                "key_id": None,
                "name": payload.get("name", ""),
            }
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token expired. Please login again.",
            )
        except Exception as exc:
            logger.warning("[verify_api_key] JWT decode failed for %s: %s", path, exc)

    # 3. Legacy API key auth
    if x_api_key:
        from security.auth import APIKeyManager

        manager = APIKeyManager()
        user_info = manager.validate_api_key(x_api_key)
        if user_info:
            logger.debug("[verify_api_key] API key auth OK user=%s for %s", user_info["user_id"], path)
            return user_info

        logger.warning("[verify_api_key] Invalid API key attempt for %s", path)
        raise HTTPException(status_code=403, detail="Invalid API key")

    # No valid auth provided
    logger.warning("[verify_api_key] No auth provided for %s", path)
    raise HTTPException(
        status_code=401,
        detail="Unauthorized - Please login",
    )


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

    from security.auth import APIKeyManager

    manager = APIKeyManager()
    return manager.validate_api_key(x_api_key)
