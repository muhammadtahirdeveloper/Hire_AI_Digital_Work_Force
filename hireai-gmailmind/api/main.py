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
from sqlalchemy import text

from api.routes import agent, auth, config, hr_routes, orchestrator_routes, reports, security_routes
from api.routes.security_dashboard import router as security_dashboard_router
from api.routes.real_estate_routes import router as real_estate_router
from api.routes.ecommerce_routes import router as ecommerce_router
from api.routes.dashboard_routes import router as dashboard_router
from api.routes.frontend_routes import router as frontend_router
from api.routes.gmail_webhook import router as gmail_webhook_router
from config.settings import APP_ENV, DEBUG
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
# Middleware (order matters: CORS must be outermost to handle preflight)
# ============================================================================

# 1. CORS — added first so it becomes outermost after subsequent add_middleware calls
#    In Starlette, each add_middleware wraps the previous, so the LAST added is outermost.
#    We add CORS last to ensure it intercepts OPTIONS preflight before anything else.

# 2. Security Headers (inner middleware, adds headers to responses)
app.add_middleware(SecurityHeadersMiddleware)

# 3. CORS (outermost — handles preflight OPTIONS before other middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://hireai-frontend.vercel.app",
        "https://hireai-frontend-*.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
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

# Gmail push notification webhook (no auth — verified by Google Pub/Sub)
app.include_router(gmail_webhook_router, tags=["Webhooks"])


# ============================================================================
# Startup: ensure action_logs schema is up to date
# ============================================================================


@app.on_event("startup")
async def ensure_action_logs_schema():
    """Add missing columns to action_logs if the table exists."""
    try:
        from config.database import SessionLocal
        db = SessionLocal()
        try:
            for col in [
                "user_id VARCHAR(255)",
                "email_subject VARCHAR(500)",
            ]:
                try:
                    db.execute(text(f"ALTER TABLE action_logs ADD COLUMN IF NOT EXISTS {col}"))
                except Exception:
                    pass
            db.commit()
            logger.info("action_logs schema migration complete")
        finally:
            db.close()
    except Exception as exc:
        logger.warning("action_logs migration skipped (non-fatal): %s", exc)


# ============================================================================
# Health check
# ============================================================================


@app.get("/health", tags=["System"])
async def health_check():
    """Health check — tests API, database, and AI provider connectivity."""
    from datetime import datetime, timezone
    checks = {"api": "healthy"}

    # Database check
    try:
        from config.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = "healthy"
        finally:
            db.close()
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    # AI provider check (quick — just verify key exists)
    import os
    checks["groq_key"] = "configured" if os.environ.get("GROQ_API_KEY") else "missing"
    checks["claude_key"] = "configured" if os.environ.get("ANTHROPIC_API_KEY") else "missing"

    overall = "healthy" if checks["database"] == "healthy" else "degraded"
    return {
        "success": True,
        "data": {
            "status": overall,
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "error": None,
    }


@app.get("/api/health/platform", tags=["System"])
async def platform_health():
    """Public platform health check — no auth required."""
    from datetime import datetime, timezone
    return {
        "success": True,
        "data": {
            "status": "operational",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "error": None,
    }
