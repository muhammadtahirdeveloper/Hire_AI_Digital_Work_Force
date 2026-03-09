"""API routes for security management (API keys, etc.)."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from security.auth import APIKeyManager
from security.rate_limiter import rate_limit_api_key_creation
from security.security_report import generate_security_report, export_report_pdf_ready
from security.validators import sanitize_string, validate_user_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateAPIKeyRequest(BaseModel):
    """Request body for creating an API key."""
    user_id: str
    name: str


class CreateAPIKeyResponse(BaseModel):
    """Response for API key creation."""
    api_key: str
    key_id: int
    message: str


class APIKeyInfo(BaseModel):
    """API key information (without plain key)."""
    key_id: int
    name: str
    created_at: str = None
    is_active: bool
    last_used: str = None


class RevokeAPIKeyRequest(BaseModel):
    """Request body for revoking an API key."""
    user_id: str


# ============================================================================
# Routes
# ============================================================================

@router.post(
    "/api-keys",
    response_model=CreateAPIKeyResponse,
    dependencies=[Depends(rate_limit_api_key_creation)]
)
async def create_api_key(request: CreateAPIKeyRequest):
    """Create a new API key for a user.

    **Important:** The API key is shown ONLY ONCE. Save it securely.

    Args:
        request: Contains user_id and name for the key

    Returns:
        API key details including the plain key (shown once only)
    """
    # Validate and sanitize inputs
    if not validate_user_id(request.user_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid user_id format. Use only alphanumeric, underscore, hyphen."
        )

    sanitized_name = sanitize_string(request.name, max_length=100)
    if not sanitized_name:
        raise HTTPException(
            status_code=400,
            detail="API key name cannot be empty"
        )

    try:
        manager = APIKeyManager()
        result = manager.create_api_key(
            user_id=request.user_id,
            name=sanitized_name
        )

        logger.info(f"[security_routes] Created API key for user={request.user_id}")

        return CreateAPIKeyResponse(
            api_key=result["api_key"],
            key_id=result["key_id"],
            message="Save this key safely — it won't be shown again"
        )

    except Exception as exc:
        logger.error(f"[security_routes] Failed to create API key: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create API key"
        )


@router.get("/api-keys/{user_id}", response_model=List[APIKeyInfo])
async def list_api_keys(user_id: str):
    """List all API keys for a user.

    Does not return plain API keys, only metadata.

    Args:
        user_id: User identifier

    Returns:
        List of API key metadata
    """
    try:
        manager = APIKeyManager()
        keys = manager.list_api_keys(user_id)

        logger.debug(f"[security_routes] Listed {len(keys)} keys for user={user_id}")

        return [APIKeyInfo(**key) for key in keys]

    except Exception as exc:
        logger.error(f"[security_routes] Failed to list API keys: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list API keys"
        )


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: int, request: RevokeAPIKeyRequest):
    """Revoke (deactivate) an API key.

    The key will no longer be accepted for authentication.

    Args:
        key_id: ID of the key to revoke
        request: Contains user_id for authorization

    Returns:
        Success confirmation
    """
    try:
        manager = APIKeyManager()
        success = manager.revoke_api_key(key_id, request.user_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail="API key not found or permission denied"
            )

        logger.info(f"[security_routes] Revoked API key id={key_id} for user={request.user_id}")

        return {
            "success": True,
            "message": f"API key {key_id} has been revoked"
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[security_routes] Failed to revoke API key: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Failed to revoke API key"
        )


@router.get("/report/{user_id}")
async def get_security_report(
    user_id: str,
    pdf_format: bool = Query(False, description="Return PDF-ready format")
):
    """Get comprehensive security report for a user.

    Returns security score, checks, recent events, and recommendations.

    Args:
        user_id: User identifier
        pdf_format: If True, returns PDF-ready format with additional metadata

    Returns:
        Security report dictionary
    """
    # Validate user_id
    if not validate_user_id(user_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid user_id format"
        )

    try:
        if pdf_format:
            report = export_report_pdf_ready(user_id)
        else:
            report = generate_security_report(user_id)

        logger.info(f"[security_routes] Generated security report for user={user_id}")

        return {
            "success": True,
            "data": report,
            "error": None
        }

    except Exception as exc:
        logger.error(f"[security_routes] Failed to generate security report: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate security report"
        )
