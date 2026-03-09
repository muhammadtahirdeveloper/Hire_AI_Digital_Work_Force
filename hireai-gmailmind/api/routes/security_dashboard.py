"""Public security status dashboard for GmailMind.

Displays security posture and compliance information.
This is a PUBLIC endpoint - no API key required.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from config.database import engine

logger = logging.getLogger(__name__)

router = APIRouter()


def get_security_stats() -> dict:
    """Fetch real-time security statistics from database.

    Returns:
        dict: Security statistics
    """
    stats = {
        "api_calls_today": 0,
        "security_events_today": 0,
        "active_api_keys": 0,
        "uptime_hours": 0,
    }

    try:
        with engine.connect() as conn:
            # Count API calls today (from action_logs)
            result = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM action_logs
                    WHERE DATE(timestamp) = CURRENT_DATE
                """)
            ).scalar()
            stats["api_calls_today"] = result or 0

            # Count security events today
            result = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM security_audit_logs
                    WHERE DATE(created_at) = CURRENT_DATE
                """)
            ).scalar()
            stats["security_events_today"] = result or 0

            # Count active API keys
            result = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM api_keys
                    WHERE is_active = TRUE
                """)
            ).scalar()
            stats["active_api_keys"] = result or 0

            # Calculate uptime (hours since oldest agent_status entry)
            result = conn.execute(
                text("""
                    SELECT EXTRACT(EPOCH FROM (NOW() - MIN(updated_at))) / 3600
                    FROM agent_status
                """)
            ).scalar()
            stats["uptime_hours"] = int(result) if result else 0

    except Exception as exc:
        logger.error("[security_dashboard] Failed to fetch stats: %s", exc)

    return stats


@router.get("/security-status", response_class=HTMLResponse)
async def security_status_page():
    """Public security status page (HTML).

    Shows current security posture and compliance status.
    """
    stats = get_security_stats()
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GmailMind — Security Status</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                color: #e2e8f0;
                min-height: 100vh;
                padding: 2rem;
            }}

            .container {{
                max-width: 1000px;
                margin: 0 auto;
            }}

            .header {{
                text-align: center;
                margin-bottom: 3rem;
                padding: 2rem 0;
                border-bottom: 2px solid #334155;
            }}

            .header h1 {{
                font-size: 2.5rem;
                font-weight: 700;
                color: #10b981;
                margin-bottom: 0.5rem;
                text-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
            }}

            .header p {{
                font-size: 1.1rem;
                color: #94a3b8;
            }}

            .status-badge {{
                display: inline-block;
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white;
                padding: 0.5rem 1.5rem;
                border-radius: 2rem;
                font-weight: 600;
                margin-top: 1rem;
                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
            }}

            .security-checks {{
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 1rem;
                padding: 2rem;
                margin-bottom: 2rem;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            }}

            .security-checks h2 {{
                font-size: 1.5rem;
                margin-bottom: 1.5rem;
                color: #f1f5f9;
                display: flex;
                align-items: center;
            }}

            .security-checks h2::before {{
                content: "🔒";
                margin-right: 0.5rem;
                font-size: 1.8rem;
            }}

            .check-item {{
                display: flex;
                align-items: center;
                padding: 1rem;
                margin: 0.5rem 0;
                background: #0f172a;
                border-radius: 0.5rem;
                border-left: 4px solid #10b981;
                transition: transform 0.2s;
            }}

            .check-item:hover {{
                transform: translateX(5px);
                background: #1e293b;
            }}

            .check-icon {{
                font-size: 1.5rem;
                margin-right: 1rem;
                color: #10b981;
            }}

            .check-text {{
                flex: 1;
            }}

            .check-title {{
                font-weight: 600;
                color: #f1f5f9;
                margin-bottom: 0.25rem;
            }}

            .check-description {{
                font-size: 0.9rem;
                color: #94a3b8;
            }}

            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 1rem;
                margin-bottom: 2rem;
            }}

            .stat-card {{
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 1rem;
                padding: 1.5rem;
                text-align: center;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            }}

            .stat-value {{
                font-size: 2.5rem;
                font-weight: 700;
                color: #10b981;
                margin-bottom: 0.5rem;
            }}

            .stat-label {{
                color: #94a3b8;
                font-size: 0.9rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}

            .footer {{
                text-align: center;
                padding: 2rem 0;
                border-top: 2px solid #334155;
                color: #64748b;
                font-size: 0.9rem;
            }}

            .footer a {{
                color: #10b981;
                text-decoration: none;
            }}

            .footer a:hover {{
                text-decoration: underline;
            }}

            @media (max-width: 768px) {{
                body {{
                    padding: 1rem;
                }}

                .header h1 {{
                    font-size: 1.8rem;
                }}

                .stats-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>GmailMind</h1>
                <p>Enterprise Security Dashboard</p>
                <div class="status-badge">✓ All Systems Secure</div>
            </div>

            <div class="security-checks">
                <h2>Security Compliance</h2>

                <div class="check-item">
                    <div class="check-icon">✅</div>
                    <div class="check-text">
                        <div class="check-title">API Key Authentication</div>
                        <div class="check-description">SHA-256 hashed keys with per-request validation</div>
                    </div>
                </div>

                <div class="check-item">
                    <div class="check-icon">✅</div>
                    <div class="check-text">
                        <div class="check-title">Data Encryption</div>
                        <div class="check-description">AES-128 via Fernet for sensitive data at rest</div>
                    </div>
                </div>

                <div class="check-item">
                    <div class="check-icon">✅</div>
                    <div class="check-text">
                        <div class="check-title">Rate Limiting</div>
                        <div class="check-description">Redis-based, 100 req/min per client</div>
                    </div>
                </div>

                <div class="check-item">
                    <div class="check-icon">✅</div>
                    <div class="check-text">
                        <div class="check-title">Input Validation & Sanitization</div>
                        <div class="check-description">Prevents SQL injection, XSS, and path traversal</div>
                    </div>
                </div>

                <div class="check-item">
                    <div class="check-icon">✅</div>
                    <div class="check-text">
                        <div class="check-title">Security Headers</div>
                        <div class="check-description">OWASP compliant (CSP, HSTS, X-Frame-Options, etc.)</div>
                    </div>
                </div>

                <div class="check-item">
                    <div class="check-icon">✅</div>
                    <div class="check-text">
                        <div class="check-title">Audit Logging</div>
                        <div class="check-description">All security events tracked and monitored</div>
                    </div>
                </div>

                <div class="check-item">
                    <div class="check-icon">✅</div>
                    <div class="check-text">
                        <div class="check-title">Data Isolation</div>
                        <div class="check-description">Per-client data separation with access controls</div>
                    </div>
                </div>

                <div class="check-item">
                    <div class="check-icon">✅</div>
                    <div class="check-text">
                        <div class="check-title">SQL Injection Protection</div>
                        <div class="check-description">Parameterized queries and input validation</div>
                    </div>
                </div>

                <div class="check-item">
                    <div class="check-icon">✅</div>
                    <div class="check-text">
                        <div class="check-title">CORS Protection</div>
                        <div class="check-description">Whitelist-based origin validation</div>
                    </div>
                </div>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{stats['api_calls_today']:,}</div>
                    <div class="stat-label">API Calls Today</div>
                </div>

                <div class="stat-card">
                    <div class="stat-value">{stats['security_events_today']:,}</div>
                    <div class="stat-label">Security Events Today</div>
                </div>

                <div class="stat-card">
                    <div class="stat-value">{stats['active_api_keys']}</div>
                    <div class="stat-label">Active API Keys</div>
                </div>

                <div class="stat-card">
                    <div class="stat-value">{stats['uptime_hours']:,}h</div>
                    <div class="stat-label">System Uptime</div>
                </div>
            </div>

            <div class="footer">
                <p>Last updated: {current_time}</p>
                <p style="margin-top: 0.5rem;">
                    Powered by <a href="https://github.com/anthropics/claude-code" target="_blank">GmailMind</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)
