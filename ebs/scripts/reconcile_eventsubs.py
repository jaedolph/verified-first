"""Repair missing or broken channel points eventsubs.

Twitch can revoke an eventsub (e.g. after too many failed deliveries during an EBS outage) without
the revocation message ever reaching the EBS, which silently stops firsts being recorded for that
channel. This script lists all of the app's eventsubs and, for every broadcaster with a reward
configured, makes sure there is an enabled eventsub for that reward pointing at this instance's
EVENTSUB_CALLBACK_URL and that it is the one stored in the database, repairing it if not.

The client id is shared with other deployments (e.g. test), so eventsubs with a different callback
are ignored and never deleted.

Broadcasters that have revoked the extension's authorization can't have an eventsub created until
they authorize it again. They are counted as unauthorized rather than failed.

Usage:
    python -m scripts.reconcile_eventsubs [--dry-run]
"""

import argparse
import logging
from collections import Counter, defaultdict
from typing import Any

from flask import current_app
from requests import codes
from requests.exceptions import RequestException
from sqlalchemy.exc import SQLAlchemyError

from verifiedfirst import create_app, twitch
from verifiedfirst.database import db
from verifiedfirst.models.broadcasters import Broadcaster

logger = logging.getLogger(__name__)


def reconcile_eventsubs(dry_run: bool = False) -> Counter[str]:
    """Repair eventsubs for broadcasters that don't have a working one for this instance.

    :param dry_run: only report what would be changed, without creating or deleting anything
    :raises RequestException: if the eventsubs can't be listed
    :return: number of broadcasters by result (checked, ok, repaired, unauthorized, failed)
    """
    callback_url = current_app.config["EVENTSUB_CALLBACK_URL"]

    eventsubs_by_broadcaster: dict[str, list[Any]] = defaultdict(list)
    for eventsub in twitch.get_all_eventsubs():
        eventsubs_by_broadcaster[eventsub["condition"]["broadcaster_user_id"]].append(eventsub)

    # in sql NULL != "" isn't true, so this also excludes broadcasters with a NULL reward_id
    broadcasters = (
        Broadcaster.query.filter(Broadcaster.reward_id != "").order_by(Broadcaster.id).all()
    )

    summary: Counter[str] = Counter()
    for broadcaster in broadcasters:
        summary["checked"] += 1
        eventsubs = eventsubs_by_broadcaster[str(broadcaster.id)]
        own_eventsubs = [e for e in eventsubs if e["transport"]["callback"] == callback_url]
        working_ids = [
            e["id"]
            for e in own_eventsubs
            if e["status"] == "enabled" and e["condition"]["reward_id"] == broadcaster.reward_id
        ]

        if working_ids == [broadcaster.eventsub_id]:
            summary["ok"] += 1
            continue

        logger.warning(
            "broadcaster_id=%s (%s) has no working eventsub for reward_id=%s, "
            "db eventsub_id=%s, eventsubs=%s",
            broadcaster.id,
            broadcaster.name,
            broadcaster.reward_id,
            broadcaster.eventsub_id,
            [(e["id"], e["status"]) for e in own_eventsubs],
        )

        if dry_run:
            logger.info("would repair eventsub for broadcaster_id=%s", broadcaster.id)
            summary["repaired"] += 1
            continue

        try:
            eventsub_id = twitch.update_eventsub(broadcaster, broadcaster.reward_id, eventsubs)
        except (RequestException, SQLAlchemyError) as exp:
            db.session.rollback()
            response = getattr(exp, "response", None)
            if response is not None and response.status_code == codes.forbidden:
                logger.warning(
                    "broadcaster_id=%s hasn't authorized the extension: %s", broadcaster.id, exp
                )
                summary["unauthorized"] += 1
                continue
            logger.error("could not repair eventsub for broadcaster_id=%s: %s", broadcaster.id, exp)
            summary["failed"] += 1
            continue
        logger.info(
            "repaired eventsub for broadcaster_id=%s eventsub_id=%s", broadcaster.id, eventsub_id
        )
        summary["repaired"] += 1

    return summary


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Repair missing or broken channel points eventsubs."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be changed without creating or deleting any eventsubs",
    )
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.INFO)
    with create_app().app_context():
        summary = reconcile_eventsubs(dry_run=args.dry_run)

    repaired_label = "would repair" if args.dry_run else "repaired"
    print(
        f"checked: {summary['checked']}, ok: {summary['ok']}, "
        f"{repaired_label}: {summary['repaired']}, unauthorized: {summary['unauthorized']}, "
        f"failed: {summary['failed']}"
    )


if __name__ == "__main__":
    main()
