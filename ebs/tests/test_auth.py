"""Test auth routes."""

from flask import url_for, render_template
from requests import HTTPError

from . import defaults


def test_auth(app, client, mocker):  # pylint: disable=unused-argument
    """Test /auth endpoint works correctly."""

    good_response = render_template("auth.html", auth_msg="AUTH_SUCCESSFUL")
    mock_get_auth_tokens = mocker.patch("verifiedfirst.twitch.get_auth_tokens")
    mock_get_auth_tokens.return_value = (defaults.AUTH_ACCESS_TOKEN, defaults.AUTH_REFRESH_TOKEN)
    mock_update_broadcaster_details = mocker.patch(
        "verifiedfirst.twitch.update_broadcaster_details"
    )

    resp = client.get(
        url_for("auth.auth"),
        query_string={
            "code": defaults.AUTH_CODE,
            "scope": "channel:read:redemptions",
        },
    )

    assert resp.status_code == 200
    assert resp.text == good_response
    mock_get_auth_tokens.assert_called_with(defaults.AUTH_CODE)
    mock_update_broadcaster_details.assert_called_with(
        defaults.AUTH_ACCESS_TOKEN, defaults.AUTH_REFRESH_TOKEN
    )


def test_auth_rejected(app, client):  # pylint: disable=unused-argument
    """Test /auth returns an error if the user rejected the prompt."""

    bad_response = render_template("auth.html", auth_msg="AUTH_FAILED")

    resp = client.get(
        url_for("auth.auth"),
        query_string={
            "error": "access_denied",
            "error_description": "The user denied you access",
        },
    )

    assert resp.status_code == 200
    assert resp.text == bad_response


def test_auth_error(app, client, mocker):  # pylint: disable=unused-argument
    """Test /auth returns an error if request to the oauth api fails."""

    bad_response = render_template("auth.html", auth_msg="AUTH_FAILED")
    mock_get_auth_tokens = mocker.patch("verifiedfirst.twitch.get_auth_tokens")
    mock_get_auth_tokens.side_effect = HTTPError

    resp = client.get(
        url_for("auth.auth"),
        query_string={
            "code": defaults.AUTH_CODE,
            "scope": "channel:read:redemptions",
        },
    )

    assert resp.status_code == 200
    assert resp.text == bad_response
    mock_get_auth_tokens.assert_called_with(defaults.AUTH_CODE)


def test_auth_check(app, client, mocker):  # pylint: disable=unused-argument
    """Test /auth/check endpoint works correctly."""

    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "broadcaster")

    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_broadcaster = mocker.Mock()
    mock_broadcaster.access_token = defaults.AUTH_ACCESS_TOKEN
    mock_get_broadcaster.return_value = mock_broadcaster
    mock_get_broadcaster_from_token = mocker.patch(
        "verifiedfirst.twitch.get_broadcaster_from_token"
    )

    resp = client.get(url_for("auth.auth_check"))

    assert resp.json["auth_status"] == "OK"
    assert resp.status_code == 200
    mock_get_broadcaster_from_token.assert_called_with(defaults.AUTH_ACCESS_TOKEN)


def test_auth_check_not_broadcaster(app, client, mocker):  # pylint: disable=unused-argument
    """Test /auth/check fails if the user accessing it is not a broadcaster."""

    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "viewer")
    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_get_broadcaster_from_token = mocker.patch(
        "verifiedfirst.twitch.get_broadcaster_from_token"
    )
    resp = client.get(url_for("auth.auth_check"))

    assert resp.status_code == 403
    assert resp.json["error"] == "user role is not broadcaster"
    mock_get_broadcaster.assert_not_called()
    mock_get_broadcaster_from_token.assert_not_called()


def test_auth_check_broadcaster_not_found(app, client, mocker):  # pylint: disable=unused-argument
    """Test /auth/check fails if the broadcaster is not in the database."""

    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "broadcaster")
    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_get_broadcaster.return_value = None
    mock_get_broadcaster_from_token = mocker.patch(
        "verifiedfirst.twitch.get_broadcaster_from_token"
    )

    resp = client.get(url_for("auth.auth_check"))

    assert resp.status_code == 403
    assert resp.json["error"] == "broadcaster is not authed yet"
    mock_get_broadcaster.assert_called_with(defaults.CHANNEL_ID)
    mock_get_broadcaster_from_token.assert_not_called()


def test_auth_check_auth_invalid(app, client, mocker):  # pylint: disable=unused-argument
    """Test /auth/check fails if the auth token in the database is invalid/stale."""

    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "broadcaster")

    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_broadcaster = mocker.Mock()
    mock_broadcaster.access_token = defaults.AUTH_ACCESS_TOKEN
    mock_get_broadcaster.return_value = mock_broadcaster
    mock_get_broadcaster_from_token = mocker.patch(
        "verifiedfirst.twitch.get_broadcaster_from_token"
    )
    mock_get_broadcaster_from_token.side_effect = HTTPError

    resp = client.get(url_for("auth.auth_check"))

    assert resp.status_code == 403
    assert resp.json["error"] == "broadcaster auth is invalid"
    mock_get_broadcaster.assert_called_with(defaults.CHANNEL_ID)
    mock_get_broadcaster_from_token.assert_called_with(defaults.AUTH_ACCESS_TOKEN)
