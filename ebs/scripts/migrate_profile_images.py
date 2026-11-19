"""Migrate the database schema to support caching Twitch profile images.

Applies the following changes to an existing database:
  - Adds the nullable 'profile_image_url' column to the 'twitch_user' table if it does not exist
  - Adds the nullable 'profile_image_updated' column to the 'twitch_user' table if it does not exist

Profile images are fetched from the Twitch API on demand, so no backfill is required.

This script is idempotent and safe to run multiple times.

Usage:
    python -m scripts.migrate_profile_images
"""

import logging

from sqlalchemy import inspect, text

from verifiedfirst import create_app
from verifiedfirst.database import db
from verifiedfirst.models.users import User

logger = logging.getLogger(__name__)

NEW_COLUMNS = ["profile_image_url", "profile_image_updated"]


def migrate() -> None:
    """Apply schema migrations for profile image caching."""
    inspector = inspect(db.engine)

    existing_columns = [col["name"] for col in inspector.get_columns("twitch_user")]
    for column in NEW_COLUMNS:
        if column not in existing_columns:
            # render the type from the model so it is valid for the database in use (e.g. postgres)
            column_type = User.__table__.c[column].type.compile(dialect=db.engine.dialect)
            logger.info("Adding '%s' column to 'twitch_user' table...", column)
            with db.engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE twitch_user ADD COLUMN {column} {column_type}"))
                conn.commit()
            logger.info("'%s' column added.", column)
        else:
            logger.info("'%s' column already exists in 'twitch_user' table, skipping.", column)


def main() -> None:
    """Entry point."""
    logging.getLogger().setLevel(logging.INFO)
    with create_app().app_context():
        migrate()


if __name__ == "__main__":
    main()
