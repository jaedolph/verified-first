"""Fixtures and helper functions for testing."""
import logging

import pytest

from verifiedfirst import create_app, Config

# pylint: disable=too-few-public-methods
class TestConfig(Config):
    """Config suitable for testing
    """
    PREFIX = ""
    CLIENT_ID = 'abcdefghijklmnopqrstuvwxyz1234'
    CLIENT_SECRET = "1234567890qwertyuiopasdfghjkla"
    EXTENSION_SECRET = "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYQo="
    REDIRECT_URI = "https://twitch.hv1.jaedolph.net/auth"
    TWITCH_API_BASEURL = "https://api.twitch.tv/helix"
    EVENTSUB_CALLBACK_URL = "https://verifiedfirst.jaedolph.net/eventsub"
    REQUEST_TIMEOUT = 5
    EVENTSUB_SECRET = "secret1234!"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'

@pytest.fixture
def app(caplog):
    """Create app with test config
    """
    caplog.set_level(logging.DEBUG)
    test_app = create_app(TestConfig)
    return test_app
