"""Fixtures and helper functions for testing."""
from contextlib import contextmanager
from datetime import datetime

import pytest
from flask_sqlalchemy.extension import sa_event
from freezegun import freeze_time

from verifiedfirst import create_app, Config
from verifiedfirst.database import db


# pylint: disable=too-few-public-methods
class TestConfig(Config):
    """Config suitable for testing."""

    PREFIX = ""
    CLIENT_ID = "abcdefghijklmnopqrstuvwxyz1234"
    CLIENT_SECRET = "1234567890qwertyuiopasdfghjkla"
    EXTENSION_SECRET = "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYQo="
    REDIRECT_URI = "https://twitch.hv1.jaedolph.net/auth"
    TWITCH_API_BASEURL = "https://api.twitch.tv/helix"
    EVENTSUB_CALLBACK_URL = "https://verifiedfirst.jaedolph.net/eventsub"
    REQUEST_TIMEOUT = 5
    EVENTSUB_SECRET = "secret1234!"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    LOG_LEVEL = "DEBUG"


@pytest.fixture()
def app():
    """Create app with test config."""
    test_app = create_app(TestConfig)
    return test_app


@pytest.fixture(name="init_db")
def fixture_init_db():
    """Initialise the in memory sqllite db used for testing."""

    def init_db(current_app):
        with current_app.app_context():
            db.drop_all()
            db.create_all()
        return db

    return init_db


@contextmanager
def patch_time(time_to_freeze):  # pylint: disable=missing-type-doc
    """Allows timestamps in database entries to be mocked correctly.

    :param time_to_freeze: timestamp compatible with freezegun.freeze_time
    :yield: freeze_time context with the mocked time
    """
    with freeze_time(time_to_freeze) as frozen_time:

        def set_timestamp(mapper, connection, target):  # pylint: disable=unused-argument
            now = datetime.utcnow()
            if hasattr(target, "timestamp"):
                target.timestamp = now

        sa_event.listen(db.Model, "before_insert", set_timestamp, propagate=True)
        yield frozen_time
        sa_event.remove(db.Model, "before_insert", set_timestamp)


@pytest.fixture()
def patch_current_time():
    """Fixture to use the patch_time context manager."""
    return patch_time
