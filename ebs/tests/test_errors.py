"""Tests for app error handlers."""

import pytest
from flask import Response

from verifiedfirst.errors import handlers

ERROR_MSG = "test"
RESPONSE_DICT = {"error": ERROR_MSG}


@pytest.fixture(name="mock_exception")
def fixture_mock_exception(mocker):
    """Mocks exception to pass to error handlers."""

    mock_exception = mocker.Mock()
    mock_exception.description = ERROR_MSG

    return mock_exception


def test_bad_request(app, mock_exception):  # pylint: disable=unused-argument
    """Test bad_request handler."""

    response = handlers.bad_request(mock_exception)

    assert isinstance(response, Response)
    assert response.status_code == 400
    assert response.json == RESPONSE_DICT


def test_unauthorized(app, mock_exception):  # pylint: disable=unused-argument
    """Test unauthorized handler."""

    response = handlers.unauthorized(mock_exception)

    assert isinstance(response, Response)
    assert response.status_code == 401
    assert response.json == RESPONSE_DICT


def test_forbidden(app, mock_exception):  # pylint: disable=unused-argument
    """Test forbidden handler."""

    response = handlers.forbidden(mock_exception)

    assert isinstance(response, Response)
    assert response.status_code == 403
    assert response.json == RESPONSE_DICT


def test_not_found(app, mock_exception):  # pylint: disable=unused-argument
    """Test not_found handler."""

    response = handlers.not_found(mock_exception)

    assert isinstance(response, Response)
    assert response.status_code == 404
    assert response.json == RESPONSE_DICT


def test_internal_server_error(app, mock_exception):  # pylint: disable=unused-argument
    """Test internal_server_error handler."""

    response = handlers.internal_server_error(mock_exception)

    assert isinstance(response, Response)
    assert response.status_code == 500
    assert response.json == RESPONSE_DICT
