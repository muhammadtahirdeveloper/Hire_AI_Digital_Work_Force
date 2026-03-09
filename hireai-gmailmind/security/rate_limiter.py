"""Rate limiting for GmailMind API using Redis.

Prevents API abuse by limiting requests per time window.
"""

import logging
from typing import Optional

import redis
from fastapi import Header, HTTPException, Request
from fastapi.responses import JSONResponse

from config.settings import REDIS_URL

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiter for API endpoints."""

    # Rate limit configurations (requests per window in seconds)
    LIMITS = {
        'default': {'requests': 100, 'window': 60},           # 100 req/min
        'email_processing': {'requests': 10, 'window': 60},   # 10/min
        'api_key_creation': {'requests': 5, 'window': 3600},  # 5/hour
        'reports': {'requests': 20, 'window': 3600},          # 20/hour
    }

    def __init__(self):
        """Initialize rate limiter with Redis connection.

        If Redis is unavailable, the rate limiter gracefully degrades
        and allows all requests (logs warning).
        """
        try:
            self.redis_client = redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2
            )
            # Test connection
            self.redis_client.ping()
            self.redis_available = True
            logger.info("[RateLimiter] Connected to Redis at %s", REDIS_URL)
        except Exception as exc:
            self.redis_available = False
            self.redis_client = None
            logger.warning(
                "[RateLimiter] Redis unavailable, rate limiting disabled: %s",
                exc
            )

    def check_rate_limit(
        self,
        identifier: str,
        limit_type: str = 'default'
    ) -> dict:
        """Check if request is within rate limit.

        Uses Redis INCR + EXPIRE pattern for efficient rate limiting.

        Args:
            identifier: User ID, API key, or IP address
            limit_type: Type of limit to apply (default, email_processing, etc.)

        Returns:
            dict: {
                allowed: bool,
                remaining: int,
                reset_in: int (seconds until reset)
            }
        """
        # Graceful degradation if Redis unavailable
        if not self.redis_available:
            return {
                'allowed': True,
                'remaining': 999,
                'reset_in': 60
            }

        # Get limit configuration
        limit_config = self.LIMITS.get(limit_type, self.LIMITS['default'])
        max_requests = limit_config['requests']
        window = limit_config['window']

        # Redis key for this identifier and limit type
        key = f"ratelimit:{limit_type}:{identifier}"

        try:
            # Get current count
            current = self.redis_client.get(key)

            if current is None:
                # First request in this window
                self.redis_client.setex(key, window, 1)
                return {
                    'allowed': True,
                    'remaining': max_requests - 1,
                    'reset_in': window
                }

            current = int(current)

            if current >= max_requests:
                # Rate limit exceeded
                ttl = self.redis_client.ttl(key)
                logger.warning(
                    "[RateLimiter] Rate limit exceeded: %s (type=%s, count=%d)",
                    identifier, limit_type, current
                )
                return {
                    'allowed': False,
                    'remaining': 0,
                    'reset_in': ttl if ttl > 0 else window
                }

            # Increment counter
            self.redis_client.incr(key)
            ttl = self.redis_client.ttl(key)

            return {
                'allowed': True,
                'remaining': max_requests - current - 1,
                'reset_in': ttl if ttl > 0 else window
            }

        except Exception as exc:
            logger.error("[RateLimiter] Error checking rate limit: %s", exc)
            # On error, allow request (fail open)
            return {
                'allowed': True,
                'remaining': 999,
                'reset_in': 60
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
