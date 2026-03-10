"""E-commerce Agent API endpoints.

Routes:
  GET /ecommerce/{user_id}/inquiries          — List order inquiries (paginated)
  GET /ecommerce/{user_id}/refunds            — List refund requests
  PUT /ecommerce/{user_id}/refunds/{id}       — Update refund status
  GET /ecommerce/{user_id}/complaints         — List customer complaints
  PUT /ecommerce/{user_id}/complaints/{id}    — Update complaint status/resolution
  GET /ecommerce/{user_id}/summary            — Get summary statistics
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query, Body
from sqlalchemy import text

from config.database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ecommerce", tags=["Ecommerce"])


def _ok(data=None):
    return {"success": True, "data": data, "error": None}


def _err(message: str):
    return {"success": False, "data": None, "error": message}


# ============================================================================
# GET /ecommerce/{user_id}/inquiries
# ============================================================================


@router.get("/{user_id}/inquiries")
async def get_inquiries(
    user_id: str,
    inquiry_type: Optional[str] = Query(None, description="Filter by inquiry type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """Get paginated list of order inquiries."""
    db = SessionLocal()
    try:
        offset = (page - 1) * page_size

        # Build query
        if inquiry_type:
            query = text("""
                SELECT id, customer_email, order_id, inquiry_type, status, created_at
                FROM order_inquiries
                WHERE user_id = :user_id AND inquiry_type = :inquiry_type
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """)
            params = {
                "user_id": user_id,
                "inquiry_type": inquiry_type,
                "limit": page_size,
                "offset": offset,
            }
        else:
            query = text("""
                SELECT id, customer_email, order_id, inquiry_type, status, created_at
                FROM order_inquiries
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """)
            params = {"user_id": user_id, "limit": page_size, "offset": offset}

        rows = db.execute(query, params).fetchall()

        inquiries = [
            {
                "id": row[0],
                "customer_email": row[1],
                "order_id": row[2],
                "inquiry_type": row[3],
                "status": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
            }
            for row in rows
        ]

        # Get total count
        count_query = text("""
            SELECT COUNT(*) FROM order_inquiries WHERE user_id = :user_id
        """) if not inquiry_type else text("""
            SELECT COUNT(*) FROM order_inquiries
            WHERE user_id = :user_id AND inquiry_type = :inquiry_type
        """)
        count_params = (
            {"user_id": user_id}
            if not inquiry_type
            else {"user_id": user_id, "inquiry_type": inquiry_type}
        )
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
# GET /ecommerce/{user_id}/refunds
# ============================================================================


@router.get("/{user_id}/refunds")
async def get_refunds(
    user_id: str,
    status: str = Query("pending", description="Filter by status"),
):
    """Get list of refund requests."""
    db = SessionLocal()
    try:
        query = text("""
            SELECT id, customer_email, order_id, reason, amount, status,
                   created_at, updated_at
            FROM refund_requests
            WHERE user_id = :user_id AND status = :status
            ORDER BY created_at DESC
        """)

        rows = db.execute(query, {"user_id": user_id, "status": status}).fetchall()

        refunds = [
            {
                "id": row[0],
                "customer_email": row[1],
                "order_id": row[2],
                "reason": row[3],
                "amount": float(row[4]) if row[4] else None,
                "status": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "updated_at": row[7].isoformat() if row[7] else None,
            }
            for row in rows
        ]

        return _ok({"refunds": refunds, "status": status})

    except Exception as exc:
        logger.exception("Failed to get refunds for user %s", user_id)
        return _err(f"Failed to get refunds: {exc}")
    finally:
        db.close()


# ============================================================================
# PUT /ecommerce/{user_id}/refunds/{refund_id}
# ============================================================================


@router.put("/{user_id}/refunds/{refund_id}")
async def update_refund(
    user_id: str,
    refund_id: int,
    body: dict = Body(...),
):
    """Update refund request status."""
    db = SessionLocal()
    try:
        new_status = body.get("status")
        if not new_status:
            return _err("Status is required")

        # Valid statuses: pending, approved, processed, rejected
        valid_statuses = ["pending", "approved", "processed", "rejected"]
        if new_status not in valid_statuses:
            return _err(f"Invalid status. Must be one of: {valid_statuses}")

        query = text("""
            UPDATE refund_requests
            SET status = :status, updated_at = NOW()
            WHERE id = :refund_id AND user_id = :user_id
        """)

        result = db.execute(
            query,
            {"status": new_status, "refund_id": refund_id, "user_id": user_id},
        )
        db.commit()

        if result.rowcount == 0:
            return _err(f"Refund {refund_id} not found for user {user_id}")

        logger.info(
            "Updated refund %s to status %s for user %s",
            refund_id, new_status, user_id,
        )

        return _ok({
            "success": True,
            "refund_id": refund_id,
            "new_status": new_status,
        })

    except Exception as exc:
        db.rollback()
        logger.exception("Failed to update refund %s for user %s", refund_id, user_id)
        return _err(f"Failed to update refund: {exc}")
    finally:
        db.close()


# ============================================================================
# GET /ecommerce/{user_id}/complaints
# ============================================================================


@router.get("/{user_id}/complaints")
async def get_complaints(
    user_id: str,
    priority: Optional[str] = Query(None, description="Filter by priority"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """Get list of customer complaints."""
    db = SessionLocal()
    try:
        # Build query based on filters
        conditions = ["user_id = :user_id"]
        params = {"user_id": user_id}

        if priority:
            conditions.append("priority = :priority")
            params["priority"] = priority

        if status:
            conditions.append("status = :status")
            params["status"] = status

        where_clause = " AND ".join(conditions)

        query = text(f"""
            SELECT id, customer_email, description, priority, status,
                   resolution, created_at, updated_at
            FROM customer_complaints
            WHERE {where_clause}
            ORDER BY priority DESC, created_at DESC
        """)

        rows = db.execute(query, params).fetchall()

        complaints = [
            {
                "id": row[0],
                "customer_email": row[1],
                "description": row[2],
                "priority": row[3],
                "status": row[4],
                "resolution": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "updated_at": row[7].isoformat() if row[7] else None,
            }
            for row in rows
        ]

        return _ok({"complaints": complaints})

    except Exception as exc:
        logger.exception("Failed to get complaints for user %s", user_id)
        return _err(f"Failed to get complaints: {exc}")
    finally:
        db.close()


# ============================================================================
# PUT /ecommerce/{user_id}/complaints/{complaint_id}
# ============================================================================


@router.put("/{user_id}/complaints/{complaint_id}")
async def update_complaint(
    user_id: str,
    complaint_id: int,
    body: dict = Body(...),
):
    """Update complaint status and resolution."""
    db = SessionLocal()
    try:
        new_status = body.get("status")
        resolution = body.get("resolution")

        if not new_status:
            return _err("Status is required")

        # Valid statuses: open, investigating, resolved, closed
        valid_statuses = ["open", "investigating", "resolved", "closed"]
        if new_status not in valid_statuses:
            return _err(f"Invalid status. Must be one of: {valid_statuses}")

        # Build update query
        if resolution:
            query = text("""
                UPDATE customer_complaints
                SET status = :status, resolution = :resolution, updated_at = NOW()
                WHERE id = :complaint_id AND user_id = :user_id
            """)
            params = {
                "status": new_status,
                "resolution": resolution,
                "complaint_id": complaint_id,
                "user_id": user_id,
            }
        else:
            query = text("""
                UPDATE customer_complaints
                SET status = :status, updated_at = NOW()
                WHERE id = :complaint_id AND user_id = :user_id
            """)
            params = {
                "status": new_status,
                "complaint_id": complaint_id,
                "user_id": user_id,
            }

        result = db.execute(query, params)
        db.commit()

        if result.rowcount == 0:
            return _err(f"Complaint {complaint_id} not found for user {user_id}")

        logger.info(
            "Updated complaint %s to status %s for user %s",
            complaint_id, new_status, user_id,
        )

        return _ok({"success": True})

    except Exception as exc:
        db.rollback()
        logger.exception(
            "Failed to update complaint %s for user %s",
            complaint_id, user_id,
        )
        return _err(f"Failed to update complaint: {exc}")
    finally:
        db.close()


# ============================================================================
# GET /ecommerce/{user_id}/summary
# ============================================================================


@router.get("/{user_id}/summary")
async def get_summary(user_id: str):
    """Get summary statistics for e-commerce activities."""
    db = SessionLocal()
    try:
        # Total inquiries
        inquiries_count = db.execute(
            text("SELECT COUNT(*) FROM order_inquiries WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).scalar() or 0

        # Pending refunds
        refunds_count = db.execute(
            text("""
                SELECT COUNT(*) FROM refund_requests
                WHERE user_id = :user_id AND status = 'pending'
            """),
            {"user_id": user_id},
        ).scalar() or 0

        # Open complaints
        complaints_count = db.execute(
            text("""
                SELECT COUNT(*) FROM customer_complaints
                WHERE user_id = :user_id AND status = 'open'
            """),
            {"user_id": user_id},
        ).scalar() or 0

        # Resolved today
        resolved_count = db.execute(
            text("""
                SELECT COUNT(*) FROM customer_complaints
                WHERE user_id = :user_id
                  AND status = 'resolved'
                  AND updated_at::date = CURRENT_DATE
            """),
            {"user_id": user_id},
        ).scalar() or 0

        return _ok({
            "total_inquiries": inquiries_count,
            "pending_refunds": refunds_count,
            "open_complaints": complaints_count,
            "resolved_today": resolved_count,
        })

    except Exception as exc:
        logger.exception("Failed to get summary for user %s", user_id)
        return _err(f"Failed to get summary: {exc}")
    finally:
        db.close()
