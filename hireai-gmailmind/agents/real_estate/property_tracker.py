"""Property tracking and inquiry management for Real Estate Agent."""

import logging
from typing import Optional

from sqlalchemy import text

from config.database import SessionLocal

logger = logging.getLogger(__name__)


class PropertyTracker:
    """Track properties, inquiries, viewings, and maintenance requests."""

    def get_property(self, user_id: str, property_address: str) -> Optional[dict]:
        """Get property details by address.

        Args:
            user_id: User identifier
            property_address: Property address

        Returns:
            Property dict or None if not found
        """
        db = SessionLocal()
        try:
            result = db.execute(
                text("""
                    SELECT id, user_id, address, property_type, status,
                           price, bedrooms, bathrooms, size_sqft, location,
                           description, listing_type, created_at
                    FROM properties
                    WHERE user_id = :user_id AND address = :address
                    LIMIT 1
                """),
                {"user_id": user_id, "address": property_address}
            ).fetchone()

            if result:
                return {
                    "id": result[0],
                    "user_id": result[1],
                    "address": result[2],
                    "property_type": result[3],
                    "status": result[4],
                    "price": float(result[5]) if result[5] else None,
                    "bedrooms": result[6],
                    "bathrooms": result[7],
                    "size_sqft": result[8],
                    "location": result[9],
                    "description": result[10],
                    "listing_type": result[11],
                    "created_at": str(result[12]) if result[12] else None,
                }
            return None

        except Exception as e:
            logger.error(f"[PropertyTracker] Error getting property: {e}")
            return None
        finally:
            db.close()

    def log_inquiry(
        self,
        user_id: str,
        client_email: str,
        property_address: str,
        inquiry_type: str = "general"
    ) -> int:
        """Log a property inquiry.

        Args:
            user_id: User identifier
            client_email: Client's email address
            property_address: Property address
            inquiry_type: Type of inquiry (general, viewing, pricing, etc.)

        Returns:
            Inquiry ID
        """
        db = SessionLocal()
        try:
            result = db.execute(
                text("""
                    INSERT INTO property_inquiries
                    (user_id, client_email, property_address, inquiry_type, status)
                    VALUES (:user_id, :client_email, :property_address, :inquiry_type, 'new')
                    RETURNING id
                """),
                {
                    "user_id": user_id,
                    "client_email": client_email,
                    "property_address": property_address,
                    "inquiry_type": inquiry_type,
                }
            )
            inquiry_id = result.fetchone()[0]
            db.commit()
            logger.info(
                f"[PropertyTracker] Logged inquiry {inquiry_id} for {property_address}"
            )
            return inquiry_id

        except Exception as e:
            logger.error(f"[PropertyTracker] Error logging inquiry: {e}")
            db.rollback()
            return 0
        finally:
            db.close()

    def log_viewing(
        self,
        user_id: str,
        client_email: str,
        property_address: str,
        viewing_date: str,
        viewing_time: str
    ) -> int:
        """Log a property viewing appointment.

        Args:
            user_id: User identifier
            client_email: Client's email address
            property_address: Property address
            viewing_date: Date of viewing
            viewing_time: Time of viewing

        Returns:
            Viewing ID
        """
        db = SessionLocal()
        try:
            viewing_datetime = f"{viewing_date} {viewing_time}"
            result = db.execute(
                text("""
                    INSERT INTO property_viewings
                    (user_id, client_email, property_address, viewing_date, status)
                    VALUES (:user_id, :client_email, :property_address,
                            :viewing_date::timestamp, 'scheduled')
                    RETURNING id
                """),
                {
                    "user_id": user_id,
                    "client_email": client_email,
                    "property_address": property_address,
                    "viewing_date": viewing_datetime,
                }
            )
            viewing_id = result.fetchone()[0]
            db.commit()
            logger.info(
                f"[PropertyTracker] Logged viewing {viewing_id} for {property_address}"
            )
            return viewing_id

        except Exception as e:
            logger.error(f"[PropertyTracker] Error logging viewing: {e}")
            db.rollback()
            return 0
        finally:
            db.close()

    def get_active_listings(self, user_id: str) -> list:
        """Get all active property listings for a user.

        Args:
            user_id: User identifier

        Returns:
            List of active property dicts
        """
        db = SessionLocal()
        try:
            results = db.execute(
                text("""
                    SELECT id, address, property_type, price, bedrooms,
                           bathrooms, size_sqft, location, listing_type
                    FROM properties
                    WHERE user_id = :user_id AND status = 'available'
                    ORDER BY created_at DESC
                """),
                {"user_id": user_id}
            ).fetchall()

            return [
                {
                    "id": row[0],
                    "address": row[1],
                    "property_type": row[2],
                    "price": float(row[3]) if row[3] else None,
                    "bedrooms": row[4],
                    "bathrooms": row[5],
                    "size_sqft": row[6],
                    "location": row[7],
                    "listing_type": row[8],
                }
                for row in results
            ]

        except Exception as e:
            logger.error(f"[PropertyTracker] Error getting active listings: {e}")
            return []
        finally:
            db.close()

    def get_inquiry_summary(self, user_id: str) -> dict:
        """Get summary of property inquiries and activities.

        Args:
            user_id: User identifier

        Returns:
            Summary dict with counts
        """
        db = SessionLocal()
        try:
            # Total inquiries
            inquiries_result = db.execute(
                text("SELECT COUNT(*) FROM property_inquiries WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            total_inquiries = inquiries_result[0] if inquiries_result else 0

            # Viewings scheduled
            viewings_result = db.execute(
                text("""
                    SELECT COUNT(*) FROM property_viewings
                    WHERE user_id = :user_id AND status = 'scheduled'
                """),
                {"user_id": user_id}
            ).fetchone()
            viewings_scheduled = viewings_result[0] if viewings_result else 0

            # Active properties
            properties_result = db.execute(
                text("""
                    SELECT COUNT(*) FROM properties
                    WHERE user_id = :user_id AND status = 'available'
                """),
                {"user_id": user_id}
            ).fetchone()
            properties_listed = properties_result[0] if properties_result else 0

            return {
                "total_inquiries": total_inquiries,
                "viewings_scheduled": viewings_scheduled,
                "offers_received": 0,  # To be implemented
                "properties_listed": properties_listed,
            }

        except Exception as e:
            logger.error(f"[PropertyTracker] Error getting inquiry summary: {e}")
            return {
                "total_inquiries": 0,
                "viewings_scheduled": 0,
                "offers_received": 0,
                "properties_listed": 0,
            }
        finally:
            db.close()
