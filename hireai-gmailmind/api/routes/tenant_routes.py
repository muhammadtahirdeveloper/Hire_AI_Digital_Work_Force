"""White-label tenant management API endpoints.

Provides:
  - GET  /api/tenant/config     — Public: fetch tenant branding by slug/domain
  - GET  /api/tenant/users      — Tenant admin: list users in tenant
  - POST /api/tenant/users      — Tenant admin: invite user to tenant
  - DELETE /api/tenant/users/:id — Tenant admin: remove user from tenant
  - GET  /api/tenant/stats      — Tenant admin: usage stats per user
  - GET  /api/tenants           — Super admin: list all tenants
  - POST /api/tenants           — Super admin: create new tenant
  - PATCH /api/tenants/:id      — Super admin: update tenant
  - GET  /api/agency/plans      — Public: agency pricing tiers
  - POST /api/agency/signup     — Public: agency onboarding
  - GET  /api/agency/invoices   — Tenant admin: billing invoices
  - POST /api/tenant/users/:id/limits — Tenant admin: set user limits
  - GET  /api/tenant/export     — Tenant admin: export usage report
"""

import logging
import uuid
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import text

from api.middleware import get_current_user
from config.database import SessionLocal

logger = logging.getLogger(__name__)
router = APIRouter()

SUPER_ADMIN_EMAIL = "hireaidigitalemployee@gmail.com"

# Agency pricing tiers
AGENCY_PLANS = {
    "agency_starter": {
        "name": "Agency Starter",
        "price": 99,
        "annual_price": 79,
        "max_users": 10,
        "features": [
            "Up to 10 users",
            "White-label branding",
            "Custom logo & colors",
            "Subdomain (name.hireai.app)",
            "User management dashboard",
            "Usage analytics",
            "Email support",
        ],
        "profit_example": "Sell at $19/user = $190/mo revenue, $91/mo profit",
    },
    "agency_pro": {
        "name": "Agency Pro",
        "price": 249,
        "annual_price": 199,
        "max_users": 50,
        "features": [
            "Up to 50 users",
            "Everything in Starter",
            "Custom domain support",
            "Advanced analytics",
            "Priority support",
            "Export usage reports",
            "Per-user email limits",
        ],
        "profit_example": "Sell at $15/user = $750/mo revenue, $501/mo profit",
    },
    "agency_enterprise": {
        "name": "Agency Enterprise",
        "price": 499,
        "annual_price": 399,
        "max_users": 9999,
        "features": [
            "Unlimited users",
            "Everything in Pro",
            "Dedicated support",
            "Custom agent training",
            "SLA guarantee",
            "API access",
            "White-glove onboarding",
        ],
        "profit_example": "Sell at $10/user x 100 = $1000/mo revenue, $501/mo profit",
    },
}


def _ok(data: Any = None) -> dict:
    return {"success": True, "data": data, "error": None}


def _err(message: str) -> dict:
    return {"success": False, "data": None, "error": message}


def _get_user_email(user: dict) -> str:
    """Extract email from JWT payload."""
    return user.get("email", user.get("sub", ""))


def _is_super_admin(user: dict) -> bool:
    return _get_user_email(user) == SUPER_ADMIN_EMAIL


def _get_tenant_id(user: dict) -> Optional[str]:
    """Get tenant_id for the authenticated user from DB."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            row = db.execute(
                text("SELECT tenant_id FROM users WHERE id = :uid OR email = :uid LIMIT 1"),
                {"uid": user_id},
            ).fetchone()
            return row[0] if row and row[0] else None
        finally:
            db.close()
    except Exception:
        return None


def _is_tenant_admin(user: dict) -> bool:
    """Check if user has tenant_admin role."""
    user_id = user.get("sub", "")
    try:
        db = SessionLocal()
        try:
            row = db.execute(
                text("SELECT role FROM users WHERE id = :uid OR email = :uid LIMIT 1"),
                {"uid": user_id},
            ).fetchone()
            return row is not None and row[0] == "tenant_admin"
        finally:
            db.close()
    except Exception:
        return False


# ============================================================================
# PUBLIC: Tenant config (branding) — no auth required
# ============================================================================


@router.get("/api/tenant/config")
async def get_tenant_config(
    slug: str = Query("", description="Tenant slug"),
    domain: str = Query("", description="Custom domain"),
):
    """Fetch tenant branding config by slug or custom domain."""
    if not slug and not domain:
        # Return default HireAI branding
        return _ok({
            "brand_name": "HireAI",
            "logo_url": "/logo.svg",
            "primary_color": "#2563eb",
            "secondary_color": "#1e40af",
            "support_email": "hireaidigitalemployee@gmail.com",
            "is_default": True,
        })

    try:
        db = SessionLocal()
        try:
            if slug:
                row = db.execute(
                    text("SELECT * FROM tenants WHERE slug = :slug AND is_active = true LIMIT 1"),
                    {"slug": slug},
                ).fetchone()
            else:
                row = db.execute(
                    text("SELECT * FROM tenants WHERE domain = :domain AND is_active = true LIMIT 1"),
                    {"domain": domain},
                ).fetchone()

            if not row:
                return _ok({
                    "brand_name": "HireAI",
                    "logo_url": "/logo.svg",
                    "primary_color": "#2563eb",
                    "secondary_color": "#1e40af",
                    "support_email": "hireaidigitalemployee@gmail.com",
                    "is_default": True,
                })

            cols = row._mapping
            return _ok({
                "id": cols.get("id"),
                "brand_name": cols.get("brand_name") or cols.get("name"),
                "logo_url": cols.get("logo_url") or "/logo.svg",
                "primary_color": cols.get("primary_color", "#2563eb"),
                "secondary_color": cols.get("secondary_color", "#1e40af"),
                "support_email": cols.get("support_email", ""),
                "slug": cols.get("slug"),
                "domain": cols.get("domain"),
                "is_default": False,
            })
        finally:
            db.close()
    except Exception as exc:
        logger.error("get_tenant_config error: %s", exc)
        return _ok({
            "brand_name": "HireAI",
            "logo_url": "/logo.svg",
            "primary_color": "#2563eb",
            "secondary_color": "#1e40af",
            "support_email": "hireaidigitalemployee@gmail.com",
            "is_default": True,
        })


# ============================================================================
# TENANT ADMIN: Manage users within their tenant
# ============================================================================


@router.get("/api/tenant/users")
async def list_tenant_users(user: dict = Depends(get_current_user)):
    """List all users in the authenticated user's tenant."""
    if not _is_tenant_admin(user) and not _is_super_admin(user):
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    tenant_id = _get_tenant_id(user)
    if not tenant_id and not _is_super_admin(user):
        raise HTTPException(status_code=404, detail="No tenant found for this user")

    try:
        db = SessionLocal()
        try:
            rows = db.execute(
                text("""
                    SELECT u.id, u.email, u.name, u.role, u.tier, u.created_at,
                           COALESCE(
                               (SELECT COUNT(*) FROM action_logs
                                WHERE user_id = u.id::text
                                AND timestamp > NOW() - INTERVAL '30 days'),
                               0
                           ) as emails_30d
                    FROM users u
                    WHERE u.tenant_id = :tid
                    ORDER BY u.created_at DESC
                """),
                {"tid": tenant_id},
            ).fetchall()

            users = []
            for r in rows:
                cols = r._mapping
                users.append({
                    "id": cols["id"],
                    "email": cols["email"],
                    "name": cols.get("name", ""),
                    "role": cols.get("role", "user"),
                    "tier": cols.get("tier", "trial"),
                    "created_at": str(cols.get("created_at", "")),
                    "emails_30d": cols.get("emails_30d", 0),
                })

            return _ok(users)
        finally:
            db.close()
    except Exception as exc:
        logger.error("list_tenant_users error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


class InviteUserRequest(BaseModel):
    email: str
    name: str = ""
    role: str = "user"


@router.post("/api/tenant/users")
async def invite_tenant_user(
    body: InviteUserRequest,
    user: dict = Depends(get_current_user),
):
    """Add a user to the authenticated user's tenant."""
    if not _is_tenant_admin(user) and not _is_super_admin(user):
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    tenant_id = _get_tenant_id(user)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="No tenant found")

    try:
        db = SessionLocal()
        try:
            # Check tenant user limit
            tenant = db.execute(
                text("SELECT max_users FROM tenants WHERE id = :tid"),
                {"tid": tenant_id},
            ).fetchone()
            if tenant:
                current_count = db.execute(
                    text("SELECT COUNT(*) FROM users WHERE tenant_id = :tid"),
                    {"tid": tenant_id},
                ).fetchone()
                if current_count and current_count[0] >= tenant[0]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"User limit reached ({tenant[0]}). Upgrade your plan.",
                    )

            # Check if user already exists
            existing = db.execute(
                text("SELECT id, tenant_id FROM users WHERE email = :email"),
                {"email": body.email},
            ).fetchone()

            if existing:
                if existing[1]:
                    raise HTTPException(status_code=400, detail="User already belongs to a tenant")
                # Assign existing user to this tenant
                db.execute(
                    text("UPDATE users SET tenant_id = :tid, role = :role WHERE email = :email"),
                    {"tid": tenant_id, "role": body.role, "email": body.email},
                )
            else:
                # Create new user in tenant
                new_id = str(uuid.uuid4())
                db.execute(
                    text("""
                        INSERT INTO users (id, email, name, tenant_id, role, tier, created_at)
                        VALUES (:id, :email, :name, :tid, :role, 'trial', NOW())
                    """),
                    {
                        "id": new_id,
                        "email": body.email,
                        "name": body.name,
                        "tid": tenant_id,
                        "role": body.role,
                    },
                )

            db.commit()
            return _ok({"message": f"User {body.email} added to tenant"})
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("invite_tenant_user error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/api/tenant/users/{user_id}")
async def remove_tenant_user(
    user_id: str,
    user: dict = Depends(get_current_user),
):
    """Remove a user from the tenant (unsets tenant_id, doesn't delete user)."""
    if not _is_tenant_admin(user) and not _is_super_admin(user):
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    tenant_id = _get_tenant_id(user)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="No tenant found")

    try:
        db = SessionLocal()
        try:
            db.execute(
                text("UPDATE users SET tenant_id = NULL, role = 'user' WHERE id = :uid AND tenant_id = :tid"),
                {"uid": user_id, "tid": tenant_id},
            )
            db.commit()
            return _ok({"message": "User removed from tenant"})
        finally:
            db.close()
    except Exception as exc:
        logger.error("remove_tenant_user error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/tenant/stats")
async def get_tenant_stats(user: dict = Depends(get_current_user)):
    """Get usage stats for the tenant."""
    if not _is_tenant_admin(user) and not _is_super_admin(user):
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    tenant_id = _get_tenant_id(user)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="No tenant found")

    try:
        db = SessionLocal()
        try:
            # Total users
            total_users = db.execute(
                text("SELECT COUNT(*) FROM users WHERE tenant_id = :tid"),
                {"tid": tenant_id},
            ).fetchone()[0]

            # Emails processed this month
            emails_month = db.execute(
                text("""
                    SELECT COUNT(*) FROM action_logs al
                    JOIN users u ON al.user_id = u.id::text
                    WHERE u.tenant_id = :tid
                    AND al.timestamp > date_trunc('month', NOW())
                """),
                {"tid": tenant_id},
            ).fetchone()[0]

            # Tenant info
            tenant = db.execute(
                text("SELECT name, plan, max_users, created_at FROM tenants WHERE id = :tid"),
                {"tid": tenant_id},
            ).fetchone()

            # Per-user stats
            user_stats = db.execute(
                text("""
                    SELECT u.id, u.email, u.name,
                           COALESCE((SELECT COUNT(*) FROM action_logs WHERE user_id = u.id::text AND timestamp > date_trunc('month', NOW())), 0) as emails_month,
                           COALESCE((SELECT COUNT(*) FROM action_logs WHERE user_id = u.id::text AND timestamp > NOW() - INTERVAL '1 day'), 0) as emails_today
                    FROM users u WHERE u.tenant_id = :tid
                    ORDER BY emails_month DESC
                """),
                {"tid": tenant_id},
            ).fetchall()

            per_user = []
            for r in user_stats:
                cols = r._mapping
                per_user.append({
                    "id": cols["id"],
                    "email": cols["email"],
                    "name": cols.get("name", ""),
                    "emails_month": cols.get("emails_month", 0),
                    "emails_today": cols.get("emails_today", 0),
                })

            return _ok({
                "total_users": total_users,
                "emails_this_month": emails_month,
                "tenant_name": tenant[0] if tenant else "",
                "plan": tenant[1] if tenant else "",
                "max_users": tenant[2] if tenant else 10,
                "created_at": str(tenant[3]) if tenant else "",
                "user_stats": per_user,
            })
        finally:
            db.close()
    except Exception as exc:
        logger.error("get_tenant_stats error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# SUPER ADMIN: Manage all tenants
# ============================================================================


@router.get("/api/tenants")
async def list_all_tenants(user: dict = Depends(get_current_user)):
    """Super admin: list all tenants."""
    if not _is_super_admin(user):
        raise HTTPException(status_code=403, detail="Super admin access required")

    try:
        db = SessionLocal()
        try:
            rows = db.execute(text("""
                SELECT t.*,
                       COALESCE((SELECT COUNT(*) FROM users WHERE tenant_id = t.id), 0) as user_count
                FROM tenants t
                ORDER BY t.created_at DESC
            """)).fetchall()

            tenants = []
            for r in rows:
                cols = r._mapping
                tenants.append({
                    "id": cols["id"],
                    "name": cols["name"],
                    "slug": cols["slug"],
                    "domain": cols.get("domain"),
                    "brand_name": cols.get("brand_name"),
                    "plan": cols.get("plan", "agency_starter"),
                    "max_users": cols.get("max_users", 10),
                    "is_active": cols.get("is_active", True),
                    "user_count": cols.get("user_count", 0),
                    "created_at": str(cols.get("created_at", "")),
                })

            return _ok(tenants)
        finally:
            db.close()
    except Exception as exc:
        logger.error("list_all_tenants error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


class CreateTenantRequest(BaseModel):
    name: str
    slug: str
    domain: str = ""
    logo_url: str = ""
    primary_color: str = "#2563eb"
    secondary_color: str = "#1e40af"
    brand_name: str = ""
    support_email: str = ""
    plan: str = "agency_starter"
    max_users: int = 10
    admin_email: str = ""


@router.post("/api/tenants")
async def create_tenant(
    body: CreateTenantRequest,
    user: dict = Depends(get_current_user),
):
    """Super admin: create a new tenant."""
    if not _is_super_admin(user):
        raise HTTPException(status_code=403, detail="Super admin access required")

    try:
        db = SessionLocal()
        try:
            # Check slug uniqueness
            existing = db.execute(
                text("SELECT id FROM tenants WHERE slug = :slug"),
                {"slug": body.slug},
            ).fetchone()
            if existing:
                raise HTTPException(status_code=400, detail="Slug already taken")

            tenant_id = str(uuid.uuid4())
            db.execute(
                text("""
                    INSERT INTO tenants (id, name, slug, domain, logo_url, primary_color,
                                        secondary_color, brand_name, support_email, plan, max_users)
                    VALUES (:id, :name, :slug, :domain, :logo, :pc, :sc, :bn, :se, :plan, :mu)
                """),
                {
                    "id": tenant_id,
                    "name": body.name,
                    "slug": body.slug,
                    "domain": body.domain or None,
                    "logo": body.logo_url or None,
                    "pc": body.primary_color,
                    "sc": body.secondary_color,
                    "bn": body.brand_name or body.name,
                    "se": body.support_email or "",
                    "plan": body.plan,
                    "mu": body.max_users,
                },
            )

            # If admin_email provided, assign user as tenant_admin
            if body.admin_email:
                db.execute(
                    text("""
                        UPDATE users SET tenant_id = :tid, role = 'tenant_admin'
                        WHERE email = :email
                    """),
                    {"tid": tenant_id, "email": body.admin_email},
                )

            db.commit()
            return _ok({
                "id": tenant_id,
                "slug": body.slug,
                "message": f"Tenant '{body.name}' created successfully",
            })
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("create_tenant error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


class UpdateTenantRequest(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    brand_name: Optional[str] = None
    support_email: Optional[str] = None
    plan: Optional[str] = None
    max_users: Optional[int] = None
    is_active: Optional[bool] = None


@router.patch("/api/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    body: UpdateTenantRequest,
    user: dict = Depends(get_current_user),
):
    """Super admin or tenant admin: update tenant settings."""
    user_tenant_id = _get_tenant_id(user)
    is_own_tenant = user_tenant_id == tenant_id and _is_tenant_admin(user)

    if not _is_super_admin(user) and not is_own_tenant:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        db = SessionLocal()
        try:
            updates = []
            params: dict[str, Any] = {"tid": tenant_id}

            for field in ["name", "domain", "logo_url", "primary_color", "secondary_color",
                          "brand_name", "support_email", "plan", "max_users", "is_active"]:
                val = getattr(body, field, None)
                if val is not None:
                    # Only super admin can change plan, max_users, is_active
                    if field in ("plan", "max_users", "is_active") and not _is_super_admin(user):
                        continue
                    updates.append(f"{field} = :{field}")
                    params[field] = val

            if not updates:
                return _ok({"message": "No changes"})

            db.execute(
                text(f"UPDATE tenants SET {', '.join(updates)} WHERE id = :tid"),
                params,
            )
            db.commit()
            return _ok({"message": "Tenant updated"})
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("update_tenant error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# AGENCY PRICING & ONBOARDING
# ============================================================================


@router.get("/api/agency/plans")
async def get_agency_plans():
    """Public: get agency pricing tiers."""
    plans = []
    for plan_id, plan in AGENCY_PLANS.items():
        plans.append({
            "id": plan_id,
            **plan,
        })
    return _ok(plans)


class AgencySignupRequest(BaseModel):
    company_name: str
    contact_name: str
    email: str
    phone: str = ""
    slug: str
    plan: str = "agency_starter"


@router.post("/api/agency/signup")
async def agency_signup(body: AgencySignupRequest):
    """Public: agency onboarding — creates tenant + admin user with 14-day trial."""
    # Validate slug
    if not re.match(r"^[a-z0-9][a-z0-9-]{2,30}[a-z0-9]$", body.slug):
        raise HTTPException(
            status_code=400,
            detail="Slug must be 4-32 lowercase letters, numbers, or hyphens",
        )

    plan_info = AGENCY_PLANS.get(body.plan)
    if not plan_info:
        raise HTTPException(status_code=400, detail="Invalid plan")

    try:
        db = SessionLocal()
        try:
            # Check slug uniqueness
            existing = db.execute(
                text("SELECT id FROM tenants WHERE slug = :slug"),
                {"slug": body.slug},
            ).fetchone()
            if existing:
                raise HTTPException(status_code=400, detail="Subdomain already taken")

            # Check email uniqueness for tenant admin
            existing_user = db.execute(
                text("SELECT id, tenant_id FROM users WHERE email = :email"),
                {"email": body.email},
            ).fetchone()

            tenant_id = str(uuid.uuid4())
            trial_end = datetime.now(timezone.utc) + timedelta(days=14)

            # Create tenant
            db.execute(
                text("""
                    INSERT INTO tenants (id, name, slug, brand_name, support_email,
                                        plan, max_users, is_active, created_at)
                    VALUES (:id, :name, :slug, :bn, :se, :plan, :mu, true, NOW())
                """),
                {
                    "id": tenant_id,
                    "name": body.company_name,
                    "slug": body.slug,
                    "bn": body.company_name,
                    "se": body.email,
                    "plan": body.plan,
                    "mu": plan_info["max_users"],
                },
            )

            # Create or update admin user
            if existing_user:
                if existing_user[1]:
                    raise HTTPException(
                        status_code=400,
                        detail="This email already belongs to an organization",
                    )
                db.execute(
                    text("""
                        UPDATE users SET tenant_id = :tid, role = 'tenant_admin',
                                        name = :name, tier = 'trial',
                                        trial_end_date = :trial_end
                        WHERE email = :email
                    """),
                    {
                        "tid": tenant_id,
                        "name": body.contact_name,
                        "email": body.email,
                        "trial_end": trial_end,
                    },
                )
            else:
                user_id = str(uuid.uuid4())
                db.execute(
                    text("""
                        INSERT INTO users (id, email, name, tenant_id, role, tier,
                                          trial_end_date, created_at)
                        VALUES (:id, :email, :name, :tid, 'tenant_admin', 'trial',
                                :trial_end, NOW())
                    """),
                    {
                        "id": user_id,
                        "email": body.email,
                        "name": body.contact_name,
                        "tid": tenant_id,
                        "trial_end": trial_end,
                    },
                )

            db.commit()

            return _ok({
                "tenant_id": tenant_id,
                "slug": body.slug,
                "subdomain": f"{body.slug}.hireai.app",
                "trial_ends": trial_end.isoformat(),
                "plan": body.plan,
                "message": f"Welcome! Your agency portal is ready at {body.slug}.hireai.app. 14-day free trial started.",
            })
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("agency_signup error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# AGENCY USER MANAGEMENT — Enhanced
# ============================================================================


class SetUserLimitsRequest(BaseModel):
    daily_email_limit: int = 100
    permission: str = "full_access"


@router.post("/api/tenant/users/{user_id}/limits")
async def set_user_limits(
    user_id: str,
    body: SetUserLimitsRequest,
    user: dict = Depends(get_current_user),
):
    """Tenant admin: set per-user email limits and permissions."""
    if not _is_tenant_admin(user) and not _is_super_admin(user):
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    tenant_id = _get_tenant_id(user)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="No tenant found")

    try:
        db = SessionLocal()
        try:
            # Ensure user belongs to this tenant
            target = db.execute(
                text("SELECT id FROM users WHERE id = :uid AND tenant_id = :tid"),
                {"uid": user_id, "tid": tenant_id},
            ).fetchone()
            if not target:
                raise HTTPException(status_code=404, detail="User not found in your organization")

            # Store limits in user_configs
            import json
            db.execute(
                text("""
                    INSERT INTO user_configs (user_id, config_key, config_value)
                    VALUES (:uid, 'agency_limits', :val)
                    ON CONFLICT (user_id, config_key) DO UPDATE SET config_value = :val
                """),
                {
                    "uid": user_id,
                    "val": json.dumps({
                        "daily_email_limit": body.daily_email_limit,
                        "permission": body.permission,
                    }),
                },
            )
            db.commit()
            return _ok({"message": "User limits updated"})
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("set_user_limits error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# AGENCY BILLING — Invoices & Reports
# ============================================================================


@router.get("/api/agency/invoices")
async def get_agency_invoices(user: dict = Depends(get_current_user)):
    """Tenant admin: get billing invoices."""
    if not _is_tenant_admin(user) and not _is_super_admin(user):
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    tenant_id = _get_tenant_id(user)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="No tenant found")

    try:
        db = SessionLocal()
        try:
            tenant = db.execute(
                text("SELECT name, plan, max_users, created_at FROM tenants WHERE id = :tid"),
                {"tid": tenant_id},
            ).fetchone()

            if not tenant:
                return _ok([])

            plan = tenant[1] or "agency_starter"
            plan_info = AGENCY_PLANS.get(plan, AGENCY_PLANS["agency_starter"])
            created = tenant[3]

            # Generate invoice history from tenant creation to now
            invoices = []
            current = datetime.now(timezone.utc)
            month_cursor = created.replace(day=1) if created else current.replace(day=1)
            inv_num = 1

            while month_cursor <= current:
                invoices.append({
                    "id": f"INV-{tenant_id[:6].upper()}-{inv_num:03d}",
                    "date": month_cursor.strftime("%Y-%m-%d"),
                    "period": month_cursor.strftime("%B %Y"),
                    "plan": plan_info["name"],
                    "amount": f"${plan_info['price']:.2f}",
                    "status": "Paid" if month_cursor.month < current.month or month_cursor.year < current.year else "Current",
                })
                inv_num += 1
                # Move to next month
                if month_cursor.month == 12:
                    month_cursor = month_cursor.replace(year=month_cursor.year + 1, month=1)
                else:
                    month_cursor = month_cursor.replace(month=month_cursor.month + 1)

            return _ok(invoices[::-1])  # Most recent first
        finally:
            db.close()
    except Exception as exc:
        logger.error("get_agency_invoices error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/tenant/export")
async def export_usage_report(user: dict = Depends(get_current_user)):
    """Tenant admin: export CSV usage report."""
    if not _is_tenant_admin(user) and not _is_super_admin(user):
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    tenant_id = _get_tenant_id(user)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="No tenant found")

    try:
        db = SessionLocal()
        try:
            rows = db.execute(
                text("""
                    SELECT u.email, u.name,
                           COALESCE((SELECT COUNT(*) FROM action_logs WHERE user_id = u.id::text AND timestamp > date_trunc('month', NOW())), 0) as emails_month,
                           COALESCE((SELECT COUNT(*) FROM action_logs WHERE user_id = u.id::text AND action_taken = 'auto_replied' AND timestamp > date_trunc('month', NOW())), 0) as auto_replied,
                           COALESCE((SELECT COUNT(*) FROM action_logs WHERE user_id = u.id::text AND action_taken = 'escalated' AND timestamp > date_trunc('month', NOW())), 0) as escalated
                    FROM users u WHERE u.tenant_id = :tid
                    ORDER BY emails_month DESC
                """),
                {"tid": tenant_id},
            ).fetchall()

            # Build CSV content
            lines = ["Email,Name,Emails This Month,Auto Replied,Escalated"]
            total_emails = 0
            for r in rows:
                cols = r._mapping
                lines.append(
                    f"{cols['email']},{cols.get('name', '')},{cols.get('emails_month', 0)},"
                    f"{cols.get('auto_replied', 0)},{cols.get('escalated', 0)}"
                )
                total_emails += cols.get("emails_month", 0)
            lines.append(f"\nTotal,,{total_emails},,")

            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(
                content="\n".join(lines),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=usage-report-{datetime.now().strftime('%Y-%m')}.csv"
                },
            )
        finally:
            db.close()
    except Exception as exc:
        logger.error("export_usage_report error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
