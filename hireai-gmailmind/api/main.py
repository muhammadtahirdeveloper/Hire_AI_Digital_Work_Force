"""FastAPI application entry point for GmailMind.

Starts the API server with:
  - CORS middleware (configured origins).
  - JWT-based authentication (via ``api.middleware``).
  - Three route groups: agents, config, reports.

Run locally::

    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import agent, auth, config, reports
from config.settings import APP_ENV, CORS_ORIGINS, DEBUG

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
)

# ============================================================================
# CORS
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Routers
# ============================================================================

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(agent.router, prefix="/agents", tags=["Agents"])
app.include_router(config.router, prefix="/config", tags=["Config"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])


# ============================================================================
# Health check
# ============================================================================


@app.get("/health", tags=["System"])
async def health_check():
    """Simple health check — returns OK if the API is running."""
    return {"success": True, "data": {"status": "healthy"}, "error": None}
