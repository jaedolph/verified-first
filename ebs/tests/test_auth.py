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
