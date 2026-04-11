"""Rate limiting for GmailMind API.

Prevents API abuse by limiting requests per time window.
Uses in-memory tracking (Redis removed).
"""

import logging
import time
from typing import Optional

from fastapi import Header, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimiter:
    """In-memory rate limiter for API endpoints."""

    LIMITS = {
        'default': {'requests': 100, 'window': 60},
        'email_processing': {'requests': 10, 'window': 60},
        'api_key_creation': {'requests': 5, 'window': 3600},
        'reports': {'requests': 20, 'window': 3600},
    }

    def __init__(self):
        self._buckets: dict[str, list[float]] = {}
        logger.info("[RateLimiter] Using in-memory rate limiter")

    def check_rate_limit(self, identifier: str, limit_type: str = 'default') -> dict:
        limit_config = self.LIMITS.get(limit_type, self.LIMITS['default'])
        max_requests = limit_config['requests']
        window = limit_config['window']

        key = f"{limit_type}:{identifier}"
        now = time.time()
        cutoff = now - window

        # Get or create bucket, prune old entries
        bucket = self._buckets.get(key, [])
        bucket = [t for t in bucket if t > cutoff]

        if len(bucket) >= max_requests:
            reset_in = int(bucket[0] - cutoff) if bucket else window
            self._buckets[key] = bucket
            return {'allowed': False, 'remaining': 0, 'reset_in': max(reset_in, 1)}

        bucket.append(now)
        self._buckets[key] = bucket

        return {
            'allowed': True,
            'remaining': max_requests - len(bucket),
            'reset_in': window,
        }


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


# ============================================================================
# FastAPI Dependency
# ============================================================================


async def rate_limit_dependency(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    limit_type: str = 'default'
):
    """FastAPI dependency for rate limiting.

    Can be applied to individual routes or route groups.

    Args:
        request: FastAPI request object
        x_api_key: API key from header (if authenticated)
        limit_type: Type of rate limit to apply

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    # Determine identifier (prefer API key, fallback to IP)
    identifier = x_api_key if x_api_key else request.client.host

    # Check rate limit
    limiter = get_rate_limiter()
    result = limiter.check_rate_limit(identifier, limit_type)

    # Add rate limit headers to response
    # Note: FastAPI doesn't support modifying response headers in dependencies directly,
    # so we'll add them in the exception or rely on middleware

    if not result['allowed']:
        logger.warning(
            "[rate_limit_dependency] Rate limit exceeded for %s",
            identifier[:20]  # Log partial identifier for privacy
        )
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please slow down.",
            headers={
                "Retry-After": str(result['reset_in']),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(result['reset_in'])
            }
        )

    # Request allowed - log for debugging
    logger.debug(
        "[rate_limit_dependency] Rate limit OK: %s (remaining=%d)",
        identifier[:20],
        result['remaining']
    )


# Specific rate limit dependencies for common use cases
async def rate_limit_api_key_creation(request: Request, x_api_key: Optional[str] = Header(None)):
    """Rate limit for API key creation (5 per hour)."""
    await rate_limit_dependency(request, x_api_key, 'api_key_creation')


async def rate_limit_email_processing(request: Request, x_api_key: Optional[str] = Header(None)):
    """Rate limit for email processing (10 per minute)."""
    await rate_limit_dependency(request, x_api_key, 'email_processing')


async def rate_limit_reports(request: Request, x_api_key: Optional[str] = Header(None)):
    """Rate limit for report generation (20 per hour)."""
    await rate_limit_dependency(request, x_api_key, 'reports')
