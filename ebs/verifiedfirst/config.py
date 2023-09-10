"""config.py."""
import logging
import os
import sys
from typing import cast

PREFIX = "VFIRST_"
LOG = logging.getLogger("verifiedfirst")


# pylint: disable=too-few-public-methods
class Config:
    """Parses application configuration from environment variables."""

    try:
        CLIENT_ID = os.environ.get(f"{PREFIX}CLIENT_ID") or ""
        if not CLIENT_ID:
            raise ValueError(f"Missing env var {PREFIX}CLIENT_ID")

        CLIENT_SECRET = os.environ.get(f"{PREFIX}CLIENT_SECRET") or ""
        if not CLIENT_SECRET:
            raise ValueError(f"Missing env var {PREFIX}CLIENT_SECRET")

        EXTENSION_SECRET = cast(str, os.environ.get(f"{PREFIX}EXTENSION_SECRET")) or ""
        if not EXTENSION_SECRET:
            raise ValueError(f"Missing env var {PREFIX}EXTENSION_SECRET")

        APP_ACCESS_TOKEN = os.environ.get(f"{PREFIX}APP_ACCESS_TOKEN") or ""
        if not APP_ACCESS_TOKEN:
            raise ValueError(f"Missing env var {PREFIX}APP_ACCESS_TOKEN")

        REDIRECT_URI = os.environ.get(f"{PREFIX}REDIRECT_URI") or ""
        if not REDIRECT_URI:
            raise ValueError(f"Missing env var {PREFIX}REDIRECT_URI")

        EVENTSUB_CALLBACK_URL = os.environ.get(f"{PREFIX}EVENTSUB_CALLBACK_URL") or ""
        if not EVENTSUB_CALLBACK_URL:
            raise ValueError(f"Missing env var {PREFIX}EVENTSUB_CALLBACK_URL")

        EVENTSUB_SECRET = os.environ.get(f"{PREFIX}EVENTSUB_SECRET") or ""
        if not EVENTSUB_SECRET:
            raise ValueError(f"Missing env var {PREFIX}EVENTSUB_SECRET")

        SQLALCHEMY_DATABASE_URI = os.environ.get(f"{PREFIX}SQLALCHEMY_DATABASE_URI") or ""
        if not SQLALCHEMY_DATABASE_URI:
            raise ValueError(f"Missing env var {PREFIX}SQLALCHEMY_DATABASE_URI")
    except ValueError as exp:
        LOG.error(exp)
        sys.exit(1)

    TWITCH_API_BASEURL: str = (
        os.environ.get(f"{PREFIX}TWITCH_API_BASEURL") or "https://api.twitch.tv/helix"
    )
    REQUEST_TIMEOUT: int = int((os.environ.get(f"{PREFIX}REQUEST_TIMEOUT") or 5))
