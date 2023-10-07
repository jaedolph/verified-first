"""test_verify.py."""
import base64
import time

import jwt
import pytest

from verifiedfirst import verify

from . import defaults


def test_get_hmac(app, mocker):  # pylint: disable=unused-argument
    """Test the get_hmac function generates a correct hmac."""

    message = (defaults.MESSAGE_ID + defaults.MESSAGE_TIMESTAMP + defaults.MESSAGE_DATA).encode(
        "utf-8"
    )
    hmac = verify.get_hmac(message)
    assert hmac == defaults.MESSAGE_HMAC


def test_verify_eventsub_message(app, mocker):  # pylint: disable=unused-argument
    """Test the verify_eventsub_message function."""

    mock_request = mocker.Mock()
    mock_get_hmac = mocker.patch("verifiedfirst.verify.get_hmac")

    mock_get_hmac.return_value = defaults.MESSAGE_HMAC

    headers = {
        "Twitch-Eventsub-Message-Id": defaults.MESSAGE_ID,
        "Twitch-Eventsub-Message-Timestamp": defaults.MESSAGE_TIMESTAMP,
        "Twitch-Eventsub-Message-Signature": "sha256=" + defaults.MESSAGE_HMAC,
    }
    mock_request.headers = headers
    mock_request.data = defaults.MESSAGE_DATA.encode("utf-8")

    # test that verification works on good signature
    verified = verify.verify_eventsub_message(mock_request)
    assert verified

    # test that verification fails when the hmac function throws an exception
    mock_get_hmac.side_effect = TypeError("Strings must be encoded before hashing")
    verified = verify.verify_eventsub_message(mock_request)
    assert not verified

    mock_get_hmac.reset_mock(return_value=False, side_effect=True)
    # test that verification fails when the signature is incorrect
    headers["Twitch-Eventsub-Message-Signature"] = "sha256=" + defaults.MESSAGE_BAD_HMAC
    mock_request.headers = headers
    verified = verify.verify_eventsub_message(mock_request)
    assert not verified


def test_verify_jwt(app, mocker, generate_jwt):  # pylint: disable=unused-argument
    """Test the verify_jwt function."""

    mock_request = mocker.Mock()

    # test the valid jwt decodes correctly
    mock_request.headers = {
        "Authorization": "Bearer " + generate_jwt(),
    }
    channel_id, role = verify.verify_jwt(mock_request)
    assert channel_id == defaults.CHANNEL_ID
    assert role == defaults.ROLE

    # test with missing auth header
    mock_request.headers = {}
    with pytest.raises(PermissionError) as exp:
        channel_id, role = verify.verify_jwt(mock_request)
    assert str(exp.value) == "could not get auth token from headers, KeyError: 'Authorization'"

    # test with badly formed auth header
    mock_request.headers = {
        "Authorization": "badauth",
    }
    with pytest.raises(PermissionError) as exp:
        channel_id, role = verify.verify_jwt(mock_request)
    assert str(exp.value) == (
        "could not get auth token from headers, IndexError: list index out of range"
    )

    # test with expired jwt
    expiry = int(time.time() - 10)
    jwt_token = generate_jwt(expiry=expiry)
    mock_request.headers = {
        "Authorization": "Bearer " + jwt_token,
    }
    with pytest.raises(PermissionError) as exp:
        channel_id, role = verify.verify_jwt(mock_request)
    assert str(exp.value) == "could not validate jwt, ExpiredSignatureError: Signature has expired"

    # test with missing jwt options
    jwt_payload = {
        "exp": int(time.time() + 999),
    }
    jwt_token = jwt.encode(
        payload=jwt_payload,
        key=base64.b64decode(app.config["EXTENSION_SECRET"]),
    )
    mock_request.headers = {
        "Authorization": "Bearer " + jwt_token,
    }
    with pytest.raises(PermissionError) as exp:
        channel_id, role = verify.verify_jwt(mock_request)
    assert str(exp.value) == "could not validate jwt, KeyError: 'channel_id'"


def function(channel_id, role):
    """Function to test the token_required decorator."""
    return channel_id, role


def test_token_required(app, mocker):  # pylint: disable=unused-argument
    """Test the token_required decorator."""

    mock_verify_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_verify_jwt.return_value = (defaults.CHANNEL_ID, defaults.ROLE)

    # test decorator correctly gets the channel_id and role
    decorated_function = verify.token_required(function)
    channel_id, role = decorated_function()

    assert channel_id == defaults.CHANNEL_ID
    assert role == defaults.ROLE

    # test 401 error is thrown if auth fails
    mock_function = mocker.Mock()
    mock_abort = mocker.patch("verifiedfirst.verify.abort")
    mock_verify_jwt.side_effect = PermissionError("mocking error")
    decorated_function = verify.token_required(mock_function)
    decorated_function()

    assert not mock_function.called
    mock_abort.assert_called_with(401, "authentication failed: mocking error")
