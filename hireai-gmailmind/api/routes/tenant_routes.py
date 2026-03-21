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
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import text

from api.middleware import get_current_user
from config.database import SessionLocal

logger = logging.getLogger(__name__)
router = APIRouter()

SUPER_ADMIN_EMAIL = "hireaidigitalemployee@gmail.com"


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
