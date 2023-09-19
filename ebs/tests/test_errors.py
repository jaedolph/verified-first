"""Tests for app error handlers."""

import pytest

from verifiedfirst.errors import handlers

ERROR_MSG = "test"
RESPONSE_DICT = {"error": ERROR_MSG}

@pytest.fixture(name="mock_errors")
def fixture_mock_errors(mocker):
    """Mocks functions/objects used in error handlers."""
    mock_jsonify = mocker.patch("verifiedfirst.errors.handlers.jsonify")
    mock_exception = mocker.Mock()
    mock_exception.description = ERROR_MSG

    return mock_jsonify, mock_exception


def test_bad_request(app, mock_errors): # pylint: disable=unused-argument
    """Test bad_request handler."""

    mock_jsonify, mock_exception = mock_errors

    handlers.bad_request(mock_exception)

    mock_jsonify.assert_called_with(RESPONSE_DICT, status=400)

def test_unauthorized(app, mock_errors): # pylint: disable=unused-argument
    """Test unauthorized handler."""

    mock_jsonify, mock_exception = mock_errors

    handlers.unauthorized(mock_exception)

    mock_jsonify.assert_called_with(RESPONSE_DICT, status=401)

def test_forbidden(app, mock_errors): # pylint: disable=unused-argument
    """Test forbidden handler."""

    mock_jsonify, mock_exception = mock_errors

    handlers.forbidden(mock_exception)

    mock_jsonify.assert_called_with(RESPONSE_DICT, status=403)

def test_not_found(app, mock_errors): # pylint: disable=unused-argument
    """Test not_found handler."""

    mock_jsonify, mock_exception = mock_errors

    handlers.not_found(mock_exception)

    mock_jsonify.assert_called_with(RESPONSE_DICT, status=404)

def test_internal_server_error(app, mock_errors): # pylint: disable=unused-argument
    """Test internal_server_error handler."""

    mock_jsonify, mock_exception = mock_errors

    handlers.internal_server_error(mock_exception)

    mock_jsonify.assert_called_with(RESPONSE_DICT, status=500)
