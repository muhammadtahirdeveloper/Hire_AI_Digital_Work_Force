"""SQLAlchemy engine and session factory.

All connection parameters are loaded from environment variables via settings.
Includes connection resilience: pool_pre_ping, recycle, and retry logic.
"""

import logging
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config.settings import DATABASE_URL

logger = logging.getLogger(__name__)


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # Test connections before use
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,         # Recycle connections every 30 minutes
    pool_timeout=10,           # Wait max 10s for a connection from pool
    connect_args={
        "connect_timeout": 5,  # 5s timeout for new connections
    },
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


def get_db():
    """Yield a database session and ensure it is closed after use.

    Yields:
        A SQLAlchemy Session instance.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_with_retry(max_retries: int = 3, delay: float = 1.0):
    """Get a DB session with retry logic for transient connection failures.

    Args:
        max_retries: Maximum number of connection attempts.
        delay: Initial delay between retries (doubles each attempt).

    Returns:
        A SQLAlchemy Session instance.

    Raises:
        Exception: If all retries are exhausted.
    """
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            # Test the connection
            db.execute(text("SELECT 1"))
            return db
        except Exception as exc:
            if attempt < max_retries - 1:
                wait = delay * (2 ** attempt)
                logger.warning(
                    "DB connection attempt %d/%d failed: %s. Retrying in %.1fs",
                    attempt + 1, max_retries, exc, wait,
                )
                time.sleep(wait)
            else:
                logger.error("DB connection failed after %d attempts: %s", max_retries, exc)
                raise
