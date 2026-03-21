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
from api.routes.notifications import router as notifications_router
from api.routes.tenant_routes import router as tenant_router
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
        "https://*.hireai.app",
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

# Web push notifications
app.include_router(notifications_router, tags=["Notifications"])

# White-label tenant management
app.include_router(tenant_router, tags=["Tenants"])

# Gmail push notification webhook (no auth — verified by Google Pub/Sub)
app.include_router(gmail_webhook_router, tags=["Webhooks"])


# ============================================================================
# Startup: ensure action_logs schema is up to date
# ============================================================================


@app.on_event("startup")
async def ensure_action_logs_schema():
    """Add missing columns and performance indexes to action_logs."""
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

            # Performance indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_action_logs_user_id ON action_logs(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_action_logs_timestamp ON action_logs(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_action_logs_user_ts ON action_logs(user_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_user_agents_user_id ON user_agents(user_id)",
            ]
            for idx_sql in indexes:
                try:
                    db.execute(text(idx_sql))
                except Exception:
                    pass

            db.commit()
            logger.info("action_logs schema + indexes migration complete")
        finally:
            db.close()
    except Exception as exc:
        logger.warning("action_logs migration skipped (non-fatal): %s", exc)


@app.on_event("startup")
async def ensure_contacts_table():
    """Create contacts table if it doesn't exist."""
    try:
        from config.database import SessionLocal
        db = SessionLocal()
        try:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                    user_id VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    name VARCHAR(255),
                    company VARCHAR(255),
                    phone VARCHAR(50),
                    category VARCHAR(50) DEFAULT 'other',
                    status VARCHAR(50) DEFAULT 'active',
                    tags TEXT,
                    notes TEXT,
                    first_contact_date TIMESTAMP DEFAULT NOW(),
                    last_contact_date TIMESTAMP DEFAULT NOW(),
                    total_emails INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            # Indexes
            for idx in [
                "CREATE INDEX IF NOT EXISTS idx_contacts_user_id ON contacts(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(user_id, email)",
            ]:
                try:
                    db.execute(text(idx))
                except Exception:
                    pass
            db.commit()
            logger.info("contacts table migration complete")
        finally:
            db.close()
    except Exception as exc:
        logger.warning("contacts migration skipped (non-fatal): %s", exc)


@app.on_event("startup")
async def ensure_deals_table():
    """Create deals table if it doesn't exist."""
    try:
        from config.database import SessionLocal
        db = SessionLocal()
        try:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS deals (
                    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                    user_id VARCHAR(255) NOT NULL,
                    contact_id VARCHAR(36),
                    title VARCHAR(255),
                    value DECIMAL(10,2) DEFAULT 0,
                    currency VARCHAR(10) DEFAULT 'USD',
                    stage VARCHAR(50) DEFAULT 'lead',
                    probability INTEGER DEFAULT 0,
                    expected_close_date DATE,
                    source_email_id VARCHAR(255),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            for idx in [
                "CREATE INDEX IF NOT EXISTS idx_deals_user_id ON deals(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_deals_stage ON deals(user_id, stage)",
            ]:
                try:
                    db.execute(text(idx))
                except Exception:
                    pass
            db.commit()
            logger.info("deals table migration complete")
        finally:
            db.close()
    except Exception as exc:
        logger.warning("deals migration skipped (non-fatal): %s", exc)


@app.on_event("startup")
async def ensure_tenants_table():
    """Create tenants table and add tenant_id column to users for white-label support."""
    try:
        from config.database import SessionLocal
        db = SessionLocal()
        try:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS tenants (
                    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                    name VARCHAR(255) NOT NULL,
                    slug VARCHAR(100) UNIQUE NOT NULL,
                    domain VARCHAR(255),
                    logo_url TEXT,
                    primary_color VARCHAR(7) DEFAULT '#2563eb',
                    secondary_color VARCHAR(7) DEFAULT '#1e40af',
                    brand_name VARCHAR(255),
                    support_email VARCHAR(255),
                    plan VARCHAR(50) DEFAULT 'agency_starter',
                    max_users INTEGER DEFAULT 10,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            # Add tenant_id column to users table
            try:
                db.execute(text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36)"
                ))
            except Exception:
                pass
            # Add role column to users table (for tenant_admin role)
            try:
                db.execute(text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user'"
                ))
            except Exception:
                pass
            # Index for fast tenant lookups
            try:
                db.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id)"
                ))
            except Exception:
                pass
            try:
                db.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug)"
                ))
            except Exception:
                pass
            try:
                db.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_tenants_domain ON tenants(domain)"
                ))
            except Exception:
                pass
            db.commit()
            logger.info("tenants table + users.tenant_id migration complete")
        finally:
            db.close()
    except Exception as exc:
        logger.warning("tenants migration skipped (non-fatal): %s", exc)


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
