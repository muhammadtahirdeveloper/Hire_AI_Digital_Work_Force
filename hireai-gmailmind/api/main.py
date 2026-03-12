"""FastAPI application entry point for GmailMind.

Starts the API server with:
  - Security headers middleware (OWASP best practices).
  - CORS middleware (configured origins).
  - API key authentication (via ``security.middleware``).
  - Multiple route groups: agents, config, reports, hr, platform.

Run locally::

    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import agent, auth, config, hr_routes, orchestrator_routes, reports, security_routes
from api.routes.security_dashboard import router as security_dashboard_router
from api.routes.real_estate_routes import router as real_estate_router
from api.routes.ecommerce_routes import router as ecommerce_router
from api.routes.dashboard_routes import router as dashboard_router
from api.routes.frontend_routes import router as frontend_router
from config.settings import APP_ENV, CORS_ORIGINS, DEBUG
from security.headers import SecurityHeadersMiddleware
from security.middleware import verify_api_key

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

# ============================================================================
# App
# ============================================================================

app = FastAPI(
    title="GmailMind API",
    description="HireAI Digital Employee #1 — Autonomous Gmail Management Agent",
    version="0.1.0",
    docs_url="/docs" if APP_ENV != "production" else None,
    redoc_url="/redoc" if APP_ENV != "production" else None,
    dependencies=[Depends(verify_api_key)],  # Global API key authentication
)

# ============================================================================
# Middleware (order matters: applied in reverse order)
# ============================================================================

# 1. Security Headers (applied last, wraps response)
app.add_middleware(SecurityHeadersMiddleware)

# 2. CORS (applied second, handles cross-origin requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Restrict to needed methods
    allow_headers=["X-API-Key", "Content-Type", "Authorization"],  # Explicit headers
    expose_headers=["X-RateLimit-Remaining", "X-RateLimit-Reset"],  # Rate limit info
)

# ============================================================================
# Routers
# ============================================================================

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(security_dashboard_router, tags=["Public"])  # Public security status page
app.include_router(security_routes.router, prefix="/security", tags=["Security"])
app.include_router(agent.router, prefix="/agents", tags=["Agents"])
app.include_router(config.router, prefix="/config", tags=["Config"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
app.include_router(orchestrator_routes.router, prefix="/platform", tags=["Platform"])
app.include_router(hr_routes.router, prefix="/hr", tags=["HR"])
app.include_router(real_estate_router)  # Prefix /real-estate defined in router
app.include_router(ecommerce_router)  # Prefix /ecommerce defined in router

# Frontend integration routes
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(frontend_router, prefix="/api", tags=["Frontend"])


# ============================================================================
# Health check
# ============================================================================


@app.get("/health", tags=["System"])
async def health_check():
    """Simple health check — returns OK if the API is running."""
    return {"success": True, "data": {"status": "healthy"}, "error": None}


@app.get("/api/health/platform", tags=["System"])
async def platform_health():
    """Public platform health check — no auth required."""
    return {"success": True, "data": {"status": "operational", "uptime": 99.9}, "error": None}
