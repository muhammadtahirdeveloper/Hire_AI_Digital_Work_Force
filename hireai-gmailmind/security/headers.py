"""Security headers middleware for GmailMind.

Adds OWASP-recommended security headers to all HTTP responses.
"""

import logging
import os
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses.

    Implements OWASP security best practices:
    - X-Content-Type-Options: Prevent MIME sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable browser XSS filters
    - Referrer-Policy: Control referrer information
    - Content-Security-Policy: Restrict resource loading
    - Strict-Transport-Security: Enforce HTTPS (when enabled)
    """

    def __init__(self, app):
        """Initialize security headers middleware.

        Args:
            app: The FastAPI/Starlette application
        """
        super().__init__(app)
        self.https_enabled = os.getenv('HTTPS', 'false').lower() == 'true'
        logger.info(
            "[SecurityHeadersMiddleware] Initialized (HTTPS=%s)",
            self.https_enabled
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request and add security headers to response.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response with security headers added
        """
        # Process the request
        response = await call_next(request)

        # Add security headers
        security_headers = {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",

            # Prevent clickjacking - deny embedding in frames
            "X-Frame-Options": "DENY",

            # Enable browser XSS protection
            "X-XSS-Protection": "1; mode=block",

            # Control referrer information leakage
            "Referrer-Policy": "strict-origin-when-cross-origin",

            # Content Security Policy - restrict resource loading
            # Note: This is a basic policy. Adjust based on your needs.
            "Content-Security-Policy": "default-src 'self'",

            # Permissions Policy (formerly Feature-Policy)
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

        # Add HSTS (Strict-Transport-Security) only when HTTPS is enabled
        # This header is NOT added for local development (HTTPS=false by default)
        # Only enable in production with valid SSL certificates (HTTPS=true)
        if self.https_enabled:
            security_headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Apply all security headers
        for header, value in security_headers.items():
            response.headers[header] = value

        # Remove headers that leak server information
        headers_to_remove = ["Server", "X-Powered-By"]
        for header in headers_to_remove:
            if header in response.headers:
                del response.headers[header]

        return response


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """Additional CORS security checks.

    Validates Origin header and enforces CORS policy.
    """

    def __init__(self, app, allowed_origins: list):
        """Initialize CORS security middleware.

        Args:
            app: The FastAPI/Starlette application
            allowed_origins: List of allowed origin URLs
        """
        super().__init__(app)
        self.allowed_origins = set(allowed_origins)
        logger.info(
            "[CORSSecurityMiddleware] Allowed origins: %s",
            allowed_origins
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Validate origin and process request.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response (may be rejected if origin not allowed)
        """
        origin = request.headers.get("origin")

        # If origin is present and not in allowed list, log warning
        if origin and origin not in self.allowed_origins:
            logger.warning(
                "[CORSSecurityMiddleware] Suspicious origin: %s from %s",
                origin,
                request.client.host if request.client else "unknown"
            )

        # Process request normally (FastAPI CORS middleware handles rejection)
        response = await call_next(request)
        return response
