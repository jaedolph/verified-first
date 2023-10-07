"""Test config load/validation."""

import pytest


from verifiedfirst import validate_config, create_app


def test_validate_config(testconfig):
    """Test valid config can be loaded."""
    validate_config(testconfig)


# pylint: disable=missing-class-docstring,too-few-public-methods
def test_validate_config_errors(testconfig):
    """Test that correct error is thrown if config value is missing."""

    class TestConfig1(testconfig):
        CLIENT_ID = ""

    with pytest.raises(ValueError, match=r"Missing env var VFIRST_CLIENT_ID"):
        validate_config(TestConfig1)

    class TestConfig2(testconfig):
        CLIENT_SECRET = ""

    with pytest.raises(ValueError, match=r"Missing env var VFIRST_CLIENT_SECRET"):
        validate_config(TestConfig2)

    class TestConfig3(testconfig):
        EXTENSION_SECRET = ""

    with pytest.raises(ValueError, match=r"Missing env var VFIRST_EXTENSION_SECRET"):
        validate_config(TestConfig3)

    class TestConfig4(testconfig):
        REDIRECT_URI = ""

    with pytest.raises(ValueError, match=r"Missing env var VFIRST_REDIRECT_URI"):
        validate_config(TestConfig4)

    class TestConfig5(testconfig):
        EVENTSUB_CALLBACK_URL = ""

    with pytest.raises(ValueError, match=r"Missing env var VFIRST_EVENTSUB_CALLBACK_URL"):
        validate_config(TestConfig5)

    class TestConfig6(testconfig):
        EVENTSUB_SECRET = ""

    with pytest.raises(ValueError, match=r"Missing env var VFIRST_EVENTSUB_SECRET"):
        validate_config(TestConfig6)

    class TestConfig7(testconfig):
        SQLALCHEMY_DATABASE_URI = ""

    with pytest.raises(ValueError, match=r"Missing env var VFIRST_SQLALCHEMY_DATABASE_URI"):
        validate_config(TestConfig7)


# pylint: disable=missing-class-docstring,too-few-public-methods
def test_create_app_config_errors(testconfig, caplog):
    """Test that create_app throws correct errors for invalid config."""

    class TestConfig1(testconfig):
        CLIENT_ID = ""

    with pytest.raises(SystemExit, match=r"1"):
        create_app(TestConfig1)

    caplog_messages = [rec.message for rec in caplog.records]
    assert caplog_messages == [
        "Missing env var VFIRST_CLIENT_ID",
    ]
    caplog.clear()

    class TestConfig2(testconfig):
        LOG_LEVEL = "TESTING"

    with pytest.raises(SystemExit, match=r"1"):
        create_app(TestConfig2)
    caplog_messages = [rec.message for rec in caplog.records]
    assert caplog_messages == [
        "error setting log level: Unknown level: 'TESTING'",
    ]
