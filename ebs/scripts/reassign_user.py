"""Reassign First entries from an old username to a user's current Twitch account.

Looks up the current username via the Twitch API to get the stable user ID, then
sets user_id on all First rows that have the old username and no user_id set.

Usage:
    python -m scripts.reassign_user <current_username> <old_username>

Example:
    python -m scripts.reassign_user newname oldname
"""

import argparse
import logging
import sys

from verifiedfirst import create_app, twitch
from verifiedfirst.database import db
from verifiedfirst.models.firsts import First
from verifiedfirst.models.users import User

logger = logging.getLogger(__name__)


def reassign_user(current_username: str, old_username: str) -> None:
    """Set user_id on First rows for old_username using the current user's Twitch ID.

    :param current_username: the user's current Twitch login name
    :param old_username: the old Twitch login name to reassign entries from
    """
    # Look up the current username to get the stable user_id
    login_to_id = twitch.get_users_by_login([current_username])
    if current_username not in login_to_id:
        logger.error("Could not find Twitch user '%s' via the API.", current_username)
        sys.exit(1)

    user_id = login_to_id[current_username]
    logger.info("Found user_id=%d for current username '%s'.", user_id, current_username)

    # Upsert the User cache record
    user = db.session.get(User, user_id)
    if user is None:
        db.session.add(User(id=user_id, name=current_username))
    else:
        user.name = current_username

    # Find First rows for the old username that have no user_id set
    rows = (
        db.session.query(First)
        .filter(First.name == old_username, First.user_id.is_(None))
        .all()
    )

    if not rows:
        logger.info(
            "No First rows found for old username '%s' with user_id unset.", old_username
        )
    else:
        for first in rows:
            first.user_id = user_id
        logger.info(
            "Set user_id=%d on %d First row(s) for old username '%s'.",
            user_id,
            len(rows),
            old_username,
        )

    # Warn about any rows for the old username that already have a different user_id
    conflicting = (
        db.session.query(First)
        .filter(First.name == old_username, First.user_id.is_not(None), First.user_id != user_id)
        .count()
    )
    if conflicting:
        logger.warning(
            "%d First row(s) for '%s' already have a different user_id and were not changed.",
            conflicting,
            old_username,
        )

    db.session.commit()
    logger.info("Done.")


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Reassign First entries from an old username to a user's current account."
    )
    parser.add_argument("current_username", help="The user's current Twitch login name")
    parser.add_argument("old_username", help="The old Twitch login name to reassign entries from")
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.INFO)
    with create_app().app_context():
        reassign_user(args.current_username, args.old_username)


if __name__ == "__main__":
    main()
