"""Seed admin user and migrate orphan data on startup. Idempotent."""

import logging
import os

from sqlalchemy import text
from sqlmodel import Session

from auth_storage import create_user, get_user_by_email
from storage import _get_engine

logger = logging.getLogger(__name__)

_ADMIN_EMAIL = os.environ.get("AGENTLENS_ADMIN_EMAIL", "admin@agentlens.local")
_ADMIN_PASSWORD = os.environ.get("AGENTLENS_ADMIN_PASSWORD", "changeme")


def seed_admin() -> None:
    """Create admin user if not exists, then migrate orphan data."""
    admin_id = _ensure_admin_user()
    _migrate_orphan_data(admin_id)

    if _ADMIN_PASSWORD == "changeme":
        logger.warning("Admin using default password — set AGENTLENS_ADMIN_PASSWORD in production")


def _ensure_admin_user() -> str:
    """Create admin user if not exists. Returns admin user_id."""
    existing = get_user_by_email(_ADMIN_EMAIL)
    if existing:
        logger.info("Admin user already exists: %s", _ADMIN_EMAIL)
        return existing.id

    user = create_user(
        email=_ADMIN_EMAIL,
        password=_ADMIN_PASSWORD,
        display_name="Admin",
        is_admin=True,
    )
    logger.info("Seeded admin user: %s (id=%s)", user.email, user.id)
    return user.id


def _migrate_orphan_data(admin_user_id: str) -> None:
    """Assign orphan records (user_id=NULL) to admin user. Idempotent."""
    engine = _get_engine()
    with Session(engine) as session:
        for table in ("trace", "alert_rule", "alert_event"):
            result = session.execute(
                text(f"UPDATE {table} SET user_id = :uid WHERE user_id IS NULL"),
                {"uid": admin_user_id},
            )
            if result.rowcount > 0:
                logger.info("Migrated %d orphan rows in %s to admin", result.rowcount, table)
        session.commit()
