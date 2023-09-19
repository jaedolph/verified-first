"""Configuration for the app."""
import os
from typing import cast


# pylint: disable=too-few-public-methods
class Config:
    """Parses application configuration from environment variables."""

    PREFIX = "VFIRST_"
    CLIENT_ID = os.environ.get(f"{PREFIX}CLIENT_ID") or ""
    CLIENT_SECRET = os.environ.get(f"{PREFIX}CLIENT_SECRET") or ""
    EXTENSION_SECRET = cast(str, os.environ.get(f"{PREFIX}EXTENSION_SECRET")) or ""
    REDIRECT_URI = os.environ.get(f"{PREFIX}REDIRECT_URI") or ""
    EVENTSUB_CALLBACK_URL = os.environ.get(f"{PREFIX}EVENTSUB_CALLBACK_URL") or ""
    EVENTSUB_SECRET = os.environ.get(f"{PREFIX}EVENTSUB_SECRET") or ""
    SQLALCHEMY_DATABASE_URI = os.environ.get(f"{PREFIX}SQLALCHEMY_DATABASE_URI") or ""

    # the APP_ACCESS_TOKEN will be created automatically
    APP_ACCESS_TOKEN = None

    TWITCH_API_BASEURL: str = (
        os.environ.get(f"{PREFIX}TWITCH_API_BASEURL") or "https://api.twitch.tv/helix"
    )
    REQUEST_TIMEOUT: int = int((os.environ.get(f"{PREFIX}REQUEST_TIMEOUT") or 5))
