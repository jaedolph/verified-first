"""Backfill user_id on existing First rows that predate the User table.

For each distinct username in the firsts table that has no user_id set, this script
looks up the user via the Twitch API and populates the User cache table and the
user_id column on all matching First rows. Rows whose username is not found in the
API response are left with user_id=NULL.

Usage:
    python -m scripts.backfill_user_ids
"""

import logging

from verifiedfirst import create_app
from verifiedfirst.database import db
from verifiedfirst.models.firsts import First
from verifiedfirst.models.users import User
from verifiedfirst import twitch

logger = logging.getLogger(__name__)


def backfill_user_ids() -> None:
    """Look up Twitch user IDs for all First rows that are missing a user_id."""

    # Collect all distinct names that still need a user_id
    rows_without_id = (
        db.session.query(First.name)
        .filter(First.user_id.is_(None))
        .distinct()
        .all()
    )
    logins = [row.name for row in rows_without_id]

    if not logins:
        logger.info("No First rows are missing a user_id, nothing to do.")
        return

    logger.info("Looking up %d unique login(s) via the Twitch API...", len(logins))

    login_to_id = twitch.get_users_by_login(logins)

    found = set(login_to_id.keys())
    not_found = set(logins) - found
    if not_found:
        logger.warning(
            "%d login(s) were not found in the Twitch API and will remain NULL: %s",
            len(not_found),
            sorted(not_found),
        )

    for login, user_id in login_to_id.items():
        # Upsert into the User cache table
        user = db.session.get(User, user_id)
        if user is None:
            db.session.add(User(id=user_id, name=login))
        else:
            user.name = login

        # Update all First rows for this login
        updated = (
            db.session.query(First)
            .filter(First.name == login, First.user_id.is_(None))
            .all()
        )
        for first in updated:
            first.user_id = user_id

        logger.info("Set user_id=%d for login=%s (%d row(s))", user_id, login, len(updated))

    db.session.commit()
    logger.info("Backfill complete.")


def main() -> None:
    """Entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with create_app().app_context():
        backfill_user_ids()


if __name__ == "__main__":
    main()
