"""Reset the Twitch extension configuration for a specific broadcaster.

Sets the broadcaster segment configuration to an empty object via the Twitch
Extensions Configuration API.

Usage:
    python -m scripts.reset_twitch_config <broadcaster_id>

Example:
    python -m scripts.reset_twitch_config 123456789
"""

import argparse
import base64
import json
import logging
import sys
import time

import jwt
import requests
from flask import current_app

from verifiedfirst import create_app, twitch

VERSION = "1"

logger = logging.getLogger(__name__)


def get_jwt_headers(broadcaster):
    jwt_payload = {
        "exp": int(time.time() + 10),
        "user_id": str(broadcaster.id),
        "role": "broadcaster",
    }

    jwt_token = jwt.encode(
        payload=jwt_payload,
        key=base64.b64decode(current_app.config["EXTENSION_SECRET"]),
    )

    return {
        "Authorization": "Bearer " + jwt_token,
        "Client-Id": current_app.config["CLIENT_ID"],
    }


def reset_config(broadcaster) -> None:
    """Set the broadcaster extension configuration to an empty object.

    :param broadcaster: broadcaster whose configuration should be reset
    """
    headers = get_jwt_headers(broadcaster)
    data = {
        "extension_id": current_app.config["CLIENT_ID"],
        "segment": "broadcaster",
        "version": VERSION,
        "content": json.dumps({}),
    }

    logger.info("Resetting config for broadcaster '%s' (id=%d).", broadcaster.name, broadcaster.id)

    resp = requests.put(
        "https://api.twitch.tv/helix/extensions/configurations",
        params={
            "extension_id": current_app.config["CLIENT_ID"],
            "broadcaster_id": str(broadcaster.id),
            "segment": "broadcaster",
            "version": VERSION,
        },
        timeout=5,
        headers=headers,
        json=data,
    )
    resp.raise_for_status()
    logger.info("Config reset successfully.")


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Reset the Twitch extension configuration for a specific broadcaster."
    )
    parser.add_argument("broadcaster_id", type=int, help="Twitch user ID of the broadcaster")
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.INFO)
    with create_app().app_context():
        broadcaster = twitch.get_broadcaster(args.broadcaster_id)
        if broadcaster is None:
            logger.error("No broadcaster found with id=%d.", args.broadcaster_id)
            sys.exit(1)
        reset_config(broadcaster)


if __name__ == "__main__":
    main()
