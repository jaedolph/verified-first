"""test_verify.py."""
import base64
import time

import jwt
import pytest

from verifiedfirst import verify

# some mock values for testing
MESSAGE_ID = "f929cb30-aa0f-4320-a630-351b23dff92a"
MESSAGE_TIMESTAMP = "2000-01-01T00:00:00.000Z"
MESSAGE_DATA = "test"
CHANNEL_ID = 123456
ROLE = "broadcaster"
# hmacs generated using the secret key "secret1234!"
# correct message hmac
MESSAGE_HMAC = "8afac673b554fc414e0740ea9edb567830e97f7465eb3c381023d04beb2f45e2"
# incorrect message hmac
MESSAGE_BAD_HMAC = "4b6915b3e283e23d92f775d37d7430a7729ee0f83bb8a0405fc717ddc7763b82"


def test_get_hmac(app, mocker):  # pylint: disable=unused-argument
    """Test the get_hmac function generates a correct hmac."""

    message = (MESSAGE_ID + MESSAGE_TIMESTAMP + MESSAGE_DATA).encode("utf-8")
    hmac = verify.get_hmac(message)
    assert hmac == MESSAGE_HMAC


def test_verify_eventsub_message(app, mocker):  # pylint: disable=unused-argument
    """Test the verify_eventsub_message function."""

    mock_request = mocker.Mock()
    mock_get_hmac = mocker.patch("verifiedfirst.verify.get_hmac")

    mock_get_hmac.return_value = MESSAGE_HMAC

    headers = {
        "Twitch-Eventsub-Message-Id": MESSAGE_ID,
        "Twitch-Eventsub-Message-Timestamp": MESSAGE_TIMESTAMP,
        "Twitch-Eventsub-Message-Signature": "sha256=" + MESSAGE_HMAC,
    }
    mock_request.headers = headers
    mock_request.data = MESSAGE_DATA.encode("utf-8")

    # test that verification works on good signature
    verified = verify.verify_eventsub_message(mock_request)
    assert verified

    # test that verification fails when the hmac function throws an exception
    mock_get_hmac.side_effect = TypeError("Strings must be encoded before hashing")
    verified = verify.verify_eventsub_message(mock_request)
    assert not verified

    mock_get_hmac.reset_mock(return_value=False, side_effect=True)
    # test that verification fails when the signature is incorrect
    headers["Twitch-Eventsub-Message-Signature"] = "sha256=" + MESSAGE_BAD_HMAC
    mock_request.headers = headers
    verified = verify.verify_eventsub_message(mock_request)
    assert not verified


def test_verify_jwt(app, mocker):  # pylint: disable=unused-argument
    """Test the verify_jwt function."""

    mock_request = mocker.Mock()

    jwt_payload = {
        "exp": int(time.time() + 999),
        "opaque_user_id": "UG12X345T6J78",
        "channel_id": CHANNEL_ID,
        "role": ROLE,
        "is_unlinked": "false",
        "pubsub_perms": {
            "listen": ["broadcast", "whisper-UG12X345T6J78"],
            "send": ["broadcast", "whisper-*"],
        },
    }

    jwt_token = jwt.encode(
        payload=jwt_payload,
        key=base64.b64decode(app.config["EXTENSION_SECRET"]),
    )

    # test the valid jwt decodes correctly
    mock_request.headers = {
        "Authorization": "Bearer " + jwt_token,
    }
    channel_id, role = verify.verify_jwt(mock_request)
    assert channel_id == CHANNEL_ID
    assert role == ROLE

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
    jwt_payload["exp"] = int(time.time() - 10)
    jwt_token = jwt.encode(
        payload=jwt_payload,
        key=base64.b64decode(app.config["EXTENSION_SECRET"]),
    )
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
    mock_verify_jwt.return_value = (CHANNEL_ID, ROLE)

    # test decorator correctly gets the channel_id and role
    decorated_function = verify.token_required(function)
    channel_id, role = decorated_function()

    assert channel_id == CHANNEL_ID
    assert role == ROLE

    # test 401 error is thrown if auth fails
    mock_function = mocker.Mock()
    mock_abort = mocker.patch("verifiedfirst.verify.abort")
    mock_verify_jwt.side_effect = PermissionError("mocking error")
    decorated_function = verify.token_required(mock_function)
    decorated_function()

    assert not mock_function.called
    mock_abort.assert_called_with(401, "authentication failed: mocking error")
