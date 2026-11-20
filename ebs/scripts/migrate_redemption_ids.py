"""Migrate the database schema to record the channel points redemption of each first.

Applies the following changes to an existing database:
  - Adds the nullable 'redemption_id' column to the 'first' table if it does not exist
  - Adds the unique 'ix_first_redemption_id' index on that column if it does not exist

The index is what stops the same redemption being added twice when Twitch delivers it more than
once. Existing firsts are left with no redemption id, which the index allows any number of.

This script is idempotent and safe to run multiple times.

Usage:
    python -m scripts.migrate_redemption_ids
"""

import logging

from sqlalchemy import inspect, text

from verifiedfirst import create_app
from verifiedfirst.database import db
from verifiedfirst.models.firsts import First

logger = logging.getLogger(__name__)

INDEX_NAME = "ix_first_redemption_id"


def migrate() -> None:
    """Apply schema migrations for recording redemption ids."""
    inspector = inspect(db.engine)

    if not inspector.has_table("first"):
        # nothing to migrate, init_db creates the full schema
        logger.info("Database has not been initialized, skipping.")
        return

    existing_columns = [col["name"] for col in inspector.get_columns("first")]
    if "redemption_id" not in existing_columns:
        # render the type from the model so it is valid for the database in use (e.g. postgres)
        column_type = First.__table__.c["redemption_id"].type.compile(dialect=db.engine.dialect)
        logger.info("Adding 'redemption_id' column to 'first' table...")
        with db.engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE first ADD COLUMN redemption_id {column_type}"))
            conn.commit()
        logger.info("'redemption_id' column added.")
    else:
        logger.info("'redemption_id' column already exists in 'first' table, skipping.")

    existing_indexes = [index["name"] for index in inspector.get_indexes("first")]
    if INDEX_NAME not in existing_indexes:
        logger.info("Adding '%s' index to 'first' table...", INDEX_NAME)
        with db.engine.connect() as conn:
            conn.execute(text(f"CREATE UNIQUE INDEX {INDEX_NAME} ON first (redemption_id)"))
            conn.commit()
        logger.info("'%s' index created.", INDEX_NAME)
    else:
        logger.info("'%s' index already exists in 'first' table, skipping.", INDEX_NAME)


def main() -> None:
    """Entry point."""
    logging.getLogger().setLevel(logging.INFO)
    with create_app().app_context():
        migrate()


if __name__ == "__main__":
    main()
