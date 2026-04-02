"""Migrate the database schema to support tracking users by Twitch user ID.

Applies the following changes to an existing database:
  - Creates the 'user' table if it does not exist
  - Adds the nullable 'user_id' foreign key column to the 'first' table if it does not exist

This script is idempotent and safe to run multiple times.

After running this migration, run the backfill script to populate user_id on existing rows:
    python -m scripts.backfill_user_ids

Usage:
    python -m scripts.migrate_user_ids
"""

import logging

from sqlalchemy import inspect, text

from verifiedfirst import create_app
from verifiedfirst.database import db
from verifiedfirst.models.users import User  # noqa: F401 - registers model with SQLAlchemy

logger = logging.getLogger(__name__)


def migrate() -> None:
    """Apply schema migrations for user ID tracking."""
    inspector = inspect(db.engine)

    if not inspector.has_table("user"):
        logger.info("Creating 'user' table...")
        User.__table__.create(db.engine)
        logger.info("'user' table created.")
    else:
        logger.info("'user' table already exists, skipping.")

    existing_columns = [col["name"] for col in inspector.get_columns("first")]
    if "user_id" not in existing_columns:
        logger.info("Adding 'user_id' column to 'first' table...")
        with db.engine.connect() as conn:
            conn.execute(
                text("ALTER TABLE first ADD COLUMN user_id INTEGER REFERENCES \"user\"(id)")
            )
            conn.commit()
        logger.info("'user_id' column added.")
    else:
        logger.info("'user_id' column already exists in 'first' table, skipping.")


def main() -> None:
    """Entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with create_app().app_context():
        migrate()


if __name__ == "__main__":
    main()
