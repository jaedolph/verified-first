"""Backfill user_id on existing First rows that predate the User table.

For each distinct username in the firsts table that has no user_id set, this script
looks up the user via the Twitch API and populates the User cache table and the
user_id column on all matching First rows. Rows whose username is not found in the
API response are left with user_id=NULL.

A second phase ensures User records exist for any user_id values already set in the
First table that are missing from the User table (e.g. from a partial previous run).

Usage:
    python -m scripts.backfill_user_ids
"""

import logging
from typing import List

from requests import Request
from sqlalchemy import select

from verifiedfirst import create_app, twitch
from verifiedfirst.database import db
from verifiedfirst.models.firsts import First
from verifiedfirst.models.users import User

logger = logging.getLogger(__name__)


def _get_users_by_id(user_ids: List[int]) -> dict[int, str]:
    """Look up Twitch users by numeric ID and return a mapping of user_id -> login.

    :param user_ids: list of numeric Twitch user IDs to look up
    :return: dict mapping user_id to current login name
    """
    id_to_login: dict[int, str] = {}
    batch_size = 100
    from flask import current_app  # pylint: disable=import-outside-toplevel

    for i in range(0, len(user_ids), batch_size):
        batch = user_ids[i : i + batch_size]
        req = Request(
            method="GET",
            url=f"{current_app.config['TWITCH_API_BASEURL']}/users",
            headers={"Client-ID": current_app.config["CLIENT_ID"]},
            params=[("id", str(uid)) for uid in batch],
        )
        resp = twitch.request_twitch_api_app(req)
        for user in resp.json().get("data", []):
            id_to_login[int(user["id"])] = user["login"]

    return id_to_login


def backfill_user_ids() -> None:
    """Look up Twitch user IDs for all First rows that are missing a user_id."""

    # Phase 1: set user_id on First rows that are still NULL
    rows_without_id = (
        db.session.query(First.name)
        .filter(First.user_id.is_(None))
        .distinct()
        .all()
    )
    logins = [row.name for row in rows_without_id]

    if not logins:
        logger.info("No First rows are missing a user_id, nothing to do.")
    else:
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
            user = db.session.get(User, user_id)
            if user is None:
                db.session.add(User(id=user_id, name=login))
            else:
                user.name = login

            updated = (
                db.session.query(First)
                .filter(First.name == login, First.user_id.is_(None))
                .all()
            )
            for first in updated:
                first.user_id = user_id

            logger.info("Set user_id=%d for login=%s (%d row(s))", user_id, login, len(updated))

        db.session.commit()

    # Phase 2: ensure User records exist for any user_id already set in First
    existing_user_ids = db.session.execute(select(User.id)).scalars().all()
    orphaned_ids = [
        row.user_id
        for row in (
            db.session.query(First.user_id)
            .filter(First.user_id.is_not(None), First.user_id.not_in(existing_user_ids))
            .distinct()
            .all()
        )
    ]

    if not orphaned_ids:
        logger.info("No orphaned user_ids found in First table, nothing to do.")
    else:
        logger.info(
            "Looking up %d user_id(s) with no User record...", len(orphaned_ids)
        )
        id_to_login = _get_users_by_id(list(orphaned_ids))

        for user_id, login in id_to_login.items():
            db.session.add(User(id=user_id, name=login))
            logger.info("Created User record for user_id=%d login=%s", user_id, login)

        missing = set(orphaned_ids) - set(id_to_login.keys())
        if missing:
            logger.warning(
                "%d user_id(s) were not found in the Twitch API: %s",
                len(missing),
                sorted(missing),
            )

        db.session.commit()

    logger.info("Backfill complete.")


def main() -> None:
    """Entry point."""
    logging.getLogger().setLevel(logging.INFO)
    with create_app().app_context():
        backfill_user_ids()


if __name__ == "__main__":
    main()
