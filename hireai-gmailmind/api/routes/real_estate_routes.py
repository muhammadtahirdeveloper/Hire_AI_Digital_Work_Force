"""Real Estate Agent API endpoints.

Routes:
  GET  /real-estate/{user_id}/inquiries     — List property inquiries (paginated)
  GET  /real-estate/{user_id}/viewings      — List upcoming viewings
  GET  /real-estate/{user_id}/maintenance   — List maintenance requests
  GET  /real-estate/{user_id}/properties    — List active properties
  POST /real-estate/{user_id}/properties    — Create new property listing
  GET  /real-estate/{user_id}/summary       — Get summary statistics
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query, Body
from sqlalchemy import text

from config.database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/real-estate", tags=["Real-estate"])


def _ok(data=None):
    return {"success": True, "data": data, "error": None}


def _err(message: str):
    return {"success": False, "data": None, "error": message}


# ============================================================================
# GET /real-estate/{user_id}/inquiries
# ============================================================================


@router.get("/{user_id}/inquiries")
async def get_inquiries(
    user_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """Get paginated list of property inquiries."""
    db = SessionLocal()
    try:
        offset = (page - 1) * page_size

        # Build query
        if status:
            query = text("""
                SELECT id, client_email, property_address, inquiry_type, status, created_at
                FROM property_inquiries
                WHERE user_id = :user_id AND status = :status
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """)
            params = {"user_id": user_id, "status": status, "limit": page_size, "offset": offset}
        else:
            query = text("""
                SELECT id, client_email, property_address, inquiry_type, status, created_at
                FROM property_inquiries
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """)
            params = {"user_id": user_id, "limit": page_size, "offset": offset}

        rows = db.execute(query, params).fetchall()

        inquiries = [
            {
                "id": row[0],
                "client_email": row[1],
                "property_address": row[2],
                "inquiry_type": row[3],
                "status": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
            }
            for row in rows
        ]

        # Get total count
        count_query = text("""
            SELECT COUNT(*) FROM property_inquiries
            WHERE user_id = :user_id
        """) if not status else text("""
            SELECT COUNT(*) FROM property_inquiries
            WHERE user_id = :user_id AND status = :status
        """)
        count_params = {"user_id": user_id} if not status else {"user_id": user_id, "status": status}
        total = db.execute(count_query, count_params).scalar() or 0

        return _ok({
            "inquiries": inquiries,
            "page": page,
            "page_size": page_size,
            "total": total,
        })

    except Exception as exc:
        logger.exception("Failed to get inquiries for user %s", user_id)
        return _err(f"Failed to get inquiries: {exc}")
    finally:
        db.close()


# ============================================================================
# GET /real-estate/{user_id}/viewings
# ============================================================================


@router.get("/{user_id}/viewings")
async def get_viewings(
    user_id: str,
    days_ahead: int = Query(7, ge=1, le=90, description="Number of days ahead to fetch"),
):
    """Get upcoming property viewings."""
    db = SessionLocal()
    try:
        query = text("""
            SELECT id, client_email, property_address, viewing_date, status, created_at
            FROM property_viewings
            WHERE user_id = :user_id
              AND viewing_date >= NOW()
              AND viewing_date <= NOW() + INTERVAL ':days days'
            ORDER BY viewing_date ASC
        """)

        rows = db.execute(query, {"user_id": user_id, "days": days_ahead}).fetchall()

        viewings = [
            {
                "id": row[0],
                "client_email": row[1],
                "property_address": row[2],
                "viewing_date": row[3].isoformat() if row[3] else None,
                "status": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
            }
            for row in rows
        ]

        return _ok({"viewings": viewings, "days_ahead": days_ahead})

    except Exception as exc:
        logger.exception("Failed to get viewings for user %s", user_id)
        return _err(f"Failed to get viewings: {exc}")
    finally:
        db.close()


# ============================================================================
# GET /real-estate/{user_id}/maintenance
# ============================================================================


@router.get("/{user_id}/maintenance")
async def get_maintenance_requests(
    user_id: str,
    status: str = Query("open", description="Filter by status"),
):
    """Get maintenance requests."""
    db = SessionLocal()
    try:
        query = text("""
            SELECT id, tenant_email, property_address, issue_description,
                   priority, status, created_at, updated_at
            FROM maintenance_requests
            WHERE user_id = :user_id AND status = :status
            ORDER BY priority DESC, created_at DESC
        """)

        rows = db.execute(query, {"user_id": user_id, "status": status}).fetchall()

        requests = [
            {
                "id": row[0],
                "tenant_email": row[1],
                "property_address": row[2],
                "issue_description": row[3],
                "priority": row[4],
                "status": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "updated_at": row[7].isoformat() if row[7] else None,
            }
            for row in rows
        ]

        return _ok({"maintenance_requests": requests, "status": status})

    except Exception as exc:
        logger.exception("Failed to get maintenance requests for user %s", user_id)
        return _err(f"Failed to get maintenance requests: {exc}")
    finally:
        db.close()


# ============================================================================
# GET /real-estate/{user_id}/properties
# ============================================================================


@router.get("/{user_id}/properties")
async def get_properties(user_id: str):
    """Get list of active property listings."""
    db = SessionLocal()
    try:
        query = text("""
            SELECT id, address, property_type, status, price, bedrooms,
                   bathrooms, size_sqft, location, listing_type, created_at
            FROM properties
            WHERE user_id = :user_id AND status = 'available'
            ORDER BY created_at DESC
        """)

        rows = db.execute(query, {"user_id": user_id}).fetchall()

        properties = [
            {
                "id": row[0],
                "address": row[1],
                "property_type": row[2],
                "status": row[3],
                "price": float(row[4]) if row[4] else None,
                "bedrooms": row[5],
                "bathrooms": row[6],
                "size_sqft": row[7],
                "location": row[8],
                "listing_type": row[9],
                "created_at": row[10].isoformat() if row[10] else None,
            }
            for row in rows
        ]

        return _ok({"properties": properties})

    except Exception as exc:
        logger.exception("Failed to get properties for user %s", user_id)
        return _err(f"Failed to get properties: {exc}")
    finally:
        db.close()


# ============================================================================
# POST /real-estate/{user_id}/properties
# ============================================================================


@router.post("/{user_id}/properties")
async def create_property(
    user_id: str,
    body: dict = Body(...),
):
    """Create a new property listing."""
    db = SessionLocal()
    try:
        address = body.get("address")
        property_type = body.get("property_type", "residential")
        price = body.get("price")
        bedrooms = body.get("bedrooms", 0)
        bathrooms = body.get("bathrooms", 0)
        size_sqft = body.get("size_sqft", 0)
        location = body.get("location")
        listing_type = body.get("listing_type", "sale")

        if not address:
            return _err("Address is required")

        query = text("""
            INSERT INTO properties
                (user_id, address, property_type, price, bedrooms, bathrooms,
                 size_sqft, location, listing_type, status)
            VALUES
                (:user_id, :address, :property_type, :price, :bedrooms, :bathrooms,
                 :size_sqft, :location, :listing_type, 'available')
            RETURNING id
        """)

        result = db.execute(
            query,
            {
                "user_id": user_id,
                "address": address,
                "property_type": property_type,
                "price": price,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "size_sqft": size_sqft,
                "location": location,
                "listing_type": listing_type,
            },
        )
        property_id = result.fetchone()[0]
        db.commit()

        logger.info("Created property %s for user %s", property_id, user_id)

        return _ok({"success": True, "property_id": property_id})

    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create property for user %s", user_id)
        return _err(f"Failed to create property: {exc}")
    finally:
        db.close()


# ============================================================================
# GET /real-estate/{user_id}/summary
# ============================================================================


@router.get("/{user_id}/summary")
async def get_summary(user_id: str):
    """Get summary statistics for real estate activities."""
    db = SessionLocal()
    try:
        # Total inquiries
        inquiries_count = db.execute(
            text("SELECT COUNT(*) FROM property_inquiries WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).scalar() or 0

        # Viewings scheduled
        viewings_count = db.execute(
            text("""
                SELECT COUNT(*) FROM property_viewings
                WHERE user_id = :user_id AND status = 'scheduled'
            """),
            {"user_id": user_id},
        ).scalar() or 0

        # Open maintenance
        maintenance_count = db.execute(
            text("""
                SELECT COUNT(*) FROM maintenance_requests
                WHERE user_id = :user_id AND status = 'open'
            """),
            {"user_id": user_id},
        ).scalar() or 0

        # Properties listed
        properties_count = db.execute(
            text("""
                SELECT COUNT(*) FROM properties
                WHERE user_id = :user_id AND status = 'available'
            """),
            {"user_id": user_id},
        ).scalar() or 0

        return _ok({
            "total_inquiries": inquiries_count,
            "viewings_scheduled": viewings_count,
            "open_maintenance": maintenance_count,
            "properties_listed": properties_count,
        })

    except Exception as exc:
        logger.exception("Failed to get summary for user %s", user_id)
        return _err(f"Failed to get summary: {exc}")
    finally:
        db.close()
