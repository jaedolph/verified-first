"""Tests for functions that interact with the Twitch API."""
from datetime import datetime
from urllib.parse import quote

import pytest
from requests import Request
from requests.exceptions import RequestException

from verifiedfirst import twitch
from verifiedfirst.models.broadcasters import Broadcaster
from verifiedfirst.models.firsts import First

AUTH_ACCESS_TOKEN = "ndwul0n9x8g6257uaei2pyczh22fz"
AUTH_REFRESH_TOKEN = "fi02f7fs1nbpsddfvb709r07y2xbonrk4w7zxjx5woutm568e"
AUTH_CODE = "88va56epq1t98c4km4lune8l4alzv"
AUTH_RESPONSE_JSON = {
    "access_token": AUTH_ACCESS_TOKEN,
    "expires_in": 14442,
    "id_token": (
        "eyJhbGciOiJSUzI1NisInR5cCI6IkpXVCIsImtpZCI6IjEifQ.eyJhdWQiOiJob2Y1Z3d4MHN1Nm9"
        "3Zm55czBueWFuOWM4N3pyNnQiLCJleHAiOjE2NDQ1MTg2NTEsImlhdCI6MTY0NDUxNzc1MSwiaXNz"
        "IjoiaHR0cHM6Ly9pZC50d2l0Y2gudHYvb2F1dGgyIiwic3ViIjoiNzEzOTM2NzMzIiwiZW1haWwiO"
        "iJzY290d2h0QGp1c3Rpbi50diIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlfQ.uMGOyvmiXHbdUAuQ4j5"
        "oExRIO3PyrM7fbhSkbT8r1tIQi5DKlS705oRiQOUGz2_j4yUWIx4zlvYWDbgLWpYS2VtSuXXBb2Gb"
        "mnCR2kG2PKxbfnY9j4F2RkQfwhYnlz0PToxpoqm_NMEIX3ROzaKs6ixgNQyDRkLS8ik39rEoAy1pE"
        "AVwbEj7-NrOYKfvm_W-RCt0Q1ppqHqhSY94jIJ38dYiT47d84c36bY5WBTs7hZniP9vIyDqFel6WO"
        "5zWOCCa-qCRS7NMc6TZNVU-2VLTQFL0ABoLSP-E6Y_i4KTp-6NyWHUBXJYoMJekrIQW8_zM-ptskn"
        "53--3HMtKCKuhiA"
    ),
    "refresh_token": AUTH_REFRESH_TOKEN,
    "scope": [
        "channel:read:redemptions",
    ],
    "token_type": "bearer",
}
AUTH_URL = "https://id.twitch.tv/oauth2/token"
BROADCASTER_NAME = "twitchdev"
BROADCASTER_ID = 141981764
EVENTSUB_ID = "26b1c993-bfcf-44d9-b876-379dacafe75a"
REWARD_ID = "536b13c5-8f49-49b9-81e1-18e52b028919"
EVENTSUB_JSON = {
    "total": 1,
    "data": [
        {
            "id": EVENTSUB_ID,
            "status": "enabled",
            "type": "channel.channel_points_custom_reward_redemption.add",
            "version": "1",
            "condition": {
                "broadcaster_user_id": str(BROADCASTER_ID),
                "reward_id": REWARD_ID,
            },
            "created_at": "2023-09-22T12:13:50.019162515Z",
            "transport": {
                "method": "webhook",
                "callback": "https://verifiedfirst.jaedolph.net/eventsub",
            },
            "cost": 0,
        }
    ],
    "total_cost": 0,
    "max_total_cost": 10000,
    "pagination": {},
}


def test_get_auth_tokens(app, requests_mock):
    """Test get_auth_tokens function."""
    mock_auth_token_request = requests_mock.post(AUTH_URL, json=AUTH_RESPONSE_JSON)
    access_token, refresh_token = twitch.get_auth_tokens(code=AUTH_CODE)

    query_expected = (
        f"client_id={app.config['CLIENT_ID']}&"
        f"client_secret={app.config['CLIENT_SECRET']}&"
        f"code={AUTH_CODE}&"
        "grant_type=authorization_code&"
        f"redirect_uri={quote(app.config['REDIRECT_URI'], safe='').lower()}"
    )

    request = mock_auth_token_request.last_request
    assert mock_auth_token_request.called_once
    assert request.query == query_expected
    assert access_token == AUTH_ACCESS_TOKEN
    assert refresh_token == AUTH_REFRESH_TOKEN


def test_get_auth_tokens_403(app, requests_mock):  # pylint: disable=unused-argument
    """Test get_auth_tokens function raises correct exception."""
    requests_mock.post(AUTH_URL, status_code=403)
    with pytest.raises(RequestException):
        twitch.get_auth_tokens(code=AUTH_CODE)


def test_get_app_access_token(app, requests_mock):
    """Test get_app_access_token function."""
    mock_auth_token_request = requests_mock.post(AUTH_URL, json=AUTH_RESPONSE_JSON)

    access_token = twitch.get_app_access_token()

    query_expected = (
        f"client_id={app.config['CLIENT_ID']}&"
        f"client_secret={app.config['CLIENT_SECRET']}&"
        "grant_type=client_credentials"
    )

    request = mock_auth_token_request.last_request
    assert mock_auth_token_request.called_once
    assert request.query == query_expected
    assert access_token == AUTH_ACCESS_TOKEN


def test_get_app_access_token_403(app, requests_mock):  # pylint: disable=unused-argument
    """Test get_app_access_token function raises correct exception."""
    requests_mock.post(AUTH_URL, status_code=403)
    with pytest.raises(RequestException):
        twitch.get_app_access_token()


def test_refresh_auth_token(app, requests_mock, init_db):
    """Test refresh_auth_token function refreshes tokens correctly."""
    init_db(app)
    initial_refresh_token = "mnbvcxzlkjhgfdsapoiuytrewq"

    initial_broadcaster = Broadcaster(
        id=BROADCASTER_ID,
        name=BROADCASTER_NAME,
        access_token="qwertyuiopasdfghjklzxcvbnm",
        refresh_token=initial_refresh_token,
        reward_name="First",
        reward_id="62eb02de-83e6-46ca-8c01-7caf4a0d83bd",
        eventsub_id="3ec20ba4-05d4-4a9b-8466-67b1b505bc5c",
    )

    mock_auth_token_request = requests_mock.post(AUTH_URL, json=AUTH_RESPONSE_JSON)

    broadcaster = twitch.refresh_auth_token(initial_broadcaster)

    query_expected = (
        f"client_id={app.config['CLIENT_ID']}&"
        f"client_secret={app.config['CLIENT_SECRET']}&"
        f"refresh_token={initial_refresh_token}&"
        "grant_type=refresh_token"
    )

    request = mock_auth_token_request.last_request
    assert mock_auth_token_request.called_once
    assert request.query == query_expected
    assert broadcaster.refresh_token == AUTH_REFRESH_TOKEN
    assert broadcaster.access_token == AUTH_ACCESS_TOKEN


def test_refresh_auth_token_403(app, requests_mock, mocker):  # pylint: disable=unused-argument
    """Test refresh_auth_token function raises the correct exception."""
    requests_mock.post(AUTH_URL, status_code=403)

    initial_broadcaster = mocker.Mock()

    with pytest.raises(RequestException):
        twitch.refresh_auth_token(initial_broadcaster)


def test_request_twitch_api(app, requests_mock):
    """Test request_twitch_api wrapper function."""
    url = f"{app.config['TWITCH_API_BASEURL']}/users"
    input_request = Request(
        method="GET",
        url=url,
    )
    expected_response = {"test": 1}
    mock_request = requests_mock.get(url, json=expected_response)
    access_token = "mnbvcxzlkjhgfdsapoiuytrewq"

    response = twitch.request_twitch_api(access_token, input_request)

    assert response.json() == expected_response
    assert mock_request.called_once
    assert mock_request.last_request.headers["Authorization"] == f"Bearer {access_token}"


def test_request_twitch_api_broadcaster(app, caplog, mocker):  # pylint: disable=unused-argument
    """Test request_twitch_api_broadcaster can request the twitch api with the correct token."""
    mock_request = mocker.Mock()
    mock_response = mocker.Mock()
    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api")
    mock_request_twitch_api.return_value = mock_response
    mock_broadcaster = mocker.Mock()
    access_token = "asdfghjklqwertyuiopzxcvbnm"
    mock_broadcaster.access_token = access_token

    response = twitch.request_twitch_api_broadcaster(mock_broadcaster, mock_request)

    assert response == mock_response
    mock_request_twitch_api.assert_called_once_with(access_token, mock_request)
    caplog_messages = [rec.message for rec in caplog.records]
    assert caplog_messages == []


def test_request_twitch_api_broadcaster_404(app, caplog, mocker):  # pylint: disable=unused-argument
    """Test request_twitch_api_broadcaster throws the correct exception if the twitch API returns an
    error (other than unauthorized)"""

    mock_request = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = RequestException("test exception")

    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api")
    mock_request_twitch_api.return_value = mock_response
    mock_broadcaster = mocker.Mock()
    access_token = "asdfghjklqwertyuiopzxcvbnm"
    mock_broadcaster.access_token = access_token

    with pytest.raises(RequestException):
        twitch.request_twitch_api_broadcaster(mock_broadcaster, mock_request)
    mock_request_twitch_api.assert_called_once_with(access_token, mock_request)
    caplog_messages = [rec.message for rec in caplog.records]
    assert caplog_messages == [
        "request to twitch api failed: test exception",
    ]


def test_request_twitch_api_broadcaster_refresh(
    app, caplog, mocker
):  # pylint: disable=too-many-locals,unused-argument
    """Test request_twitch_api_broadcaster refreshes the access token if the first request gets a
    401 error."""

    mock_request = mocker.Mock()
    mock_error_response = mocker.Mock()
    mock_error_response.status_code = 401
    mock_good_response = mocker.Mock()

    mock_error_response.raise_for_status.side_effect = RequestException("test exception")

    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api")
    mock_request_twitch_api.side_effect = [
        mock_error_response,
        mock_good_response,
    ]

    mock_broadcaster_initial = mocker.Mock()
    access_token_initial = "aaaaaaaaaaaaaaaaaaaaaaaa"
    refresh_token_initial = "bbbbbbbbbbbbbbbbbbbbbbbb"
    mock_broadcaster_initial.access_token = access_token_initial
    mock_broadcaster_initial.refresh_token = refresh_token_initial

    mock_broadcaster_refreshed = mocker.Mock()
    access_token_refreshed = "cccccccccccccccccccccc"
    refresh_token_refreshed = "dddddddddddddddddddddd"
    mock_broadcaster_refreshed.access_token = access_token_refreshed
    mock_broadcaster_refreshed.refresh_token = refresh_token_refreshed
    mock_refresh_auth_token = mocker.patch("verifiedfirst.twitch.refresh_auth_token")
    mock_refresh_auth_token.return_value = mock_broadcaster_refreshed

    response = twitch.request_twitch_api_broadcaster(mock_broadcaster_initial, mock_request)

    assert response == mock_good_response
    mock_refresh_auth_token.assert_called_once()
    caplog_messages = [rec.message for rec in caplog.records]
    assert caplog_messages == [
        "request to twitch api failed: test exception",
        "refreshing auth token",
        "retrying with new auth token: cccccccccccccccccccccc",
    ]
    mock_request_twitch_api.assert_has_calls(
        [
            mocker.call(access_token_initial, mock_request),
            mocker.call(access_token_refreshed, mock_request),
        ]
    )


def test_request_twitch_api_broadcaster_refresh_fail(
    app, caplog, mocker
):  # pylint: disable=unused-argument
    """Test request_twitch_api_broadcaster throws the correct exception if the token refresh
    fails."""

    mock_request = mocker.Mock()
    mock_error_response = mocker.Mock()
    mock_error_response.status_code = 401

    mock_error_response.raise_for_status.side_effect = RequestException("test exception")

    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api")
    mock_request_twitch_api.return_value = mock_error_response

    mock_broadcaster_initial = mocker.Mock()
    access_token_initial = "aaaaaaaaaaaaaaaaaaaaaaaa"
    refresh_token_initial = "bbbbbbbbbbbbbbbbbbbbbbbb"
    mock_broadcaster_initial.access_token = access_token_initial
    mock_broadcaster_initial.refresh_token = refresh_token_initial

    mock_refresh_auth_token = mocker.patch("verifiedfirst.twitch.refresh_auth_token")
    mock_refresh_auth_token.side_effect = RequestException("refresh failed")

    with pytest.raises(RequestException):
        twitch.request_twitch_api_broadcaster(mock_broadcaster_initial, mock_request)

    mock_refresh_auth_token.assert_called_once()
    caplog_messages = [rec.message for rec in caplog.records]
    assert caplog_messages == [
        "request to twitch api failed: test exception",
        "refreshing auth token",
        "failed to refresh auth token: refresh failed",
    ]
    mock_request_twitch_api.assert_has_calls(
        [
            mocker.call(access_token_initial, mock_request),
        ]
    )


def test_request_twitch_api_app(app, mocker, caplog):
    """Test request_twitch_api_app function can request the twitch API with an app access token."""
    mock_request = mocker.Mock()
    mock_response = mocker.Mock()
    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api")
    mock_request_twitch_api.return_value = mock_response
    access_token = app.config["APP_ACCESS_TOKEN"]

    response = twitch.request_twitch_api_app(mock_request)

    assert response == mock_response
    mock_request_twitch_api.assert_called_once_with(access_token, mock_request)
    caplog_messages = [rec.message for rec in caplog.records]
    assert caplog_messages == []


def test_request_twitch_api_app_404(app, mocker, caplog):
    """Test request_twitch_api_app function throws an exception if the twitch API returns an error
    (other than unauthorized)"""

    mock_request = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = RequestException("test exception")

    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api")
    mock_request_twitch_api.return_value = mock_response
    access_token = app.config["APP_ACCESS_TOKEN"]

    with pytest.raises(RequestException):
        twitch.request_twitch_api_app(mock_request)
    mock_request_twitch_api.assert_called_once_with(access_token, mock_request)
    caplog_messages = [rec.message for rec in caplog.records]
    assert caplog_messages == [
        "request to twitch api failed: test exception",
    ]


def test_request_twitch_api_app_refresh(app, mocker, caplog):
    """Test request_twitch_api_app function refreshes the token if the first request gets a 401
    error."""

    mock_request = mocker.Mock()
    mock_error_response = mocker.Mock()
    mock_error_response.status_code = 401
    mock_good_response = mocker.Mock()
    mock_error_response.raise_for_status.side_effect = RequestException("test exception")

    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api")
    mock_request_twitch_api.side_effect = [
        mock_error_response,
        mock_good_response,
    ]
    access_token = app.config["APP_ACCESS_TOKEN"]
    access_token_refreshed = "bbbbbbbbbbbbbbbbbbb"

    mock_get_app_access_token = mocker.patch("verifiedfirst.twitch.get_app_access_token")
    mock_get_app_access_token.return_value = access_token_refreshed

    response = twitch.request_twitch_api_app(mock_request)

    caplog_messages = [rec.message for rec in caplog.records]
    assert caplog_messages == [
        "request to twitch api failed: test exception",
        "refreshing auth token",
        f"retrying with new auth token: {access_token_refreshed}",
    ]
    assert response == mock_good_response
    mock_request_twitch_api.assert_has_calls(
        [
            mocker.call(access_token, mock_request),
            mocker.call(access_token_refreshed, mock_request),
        ]
    )
    assert app.config["APP_ACCESS_TOKEN"] == access_token_refreshed


def test_request_twitch_api_app_refresh_fail(app, mocker, caplog):
    """Test request_twitch_api_app function throws the correct error if the token refresh fails."""

    mock_request = mocker.Mock()
    mock_error_response = mocker.Mock()
    mock_error_response.status_code = 401
    mock_good_response = mocker.Mock()
    mock_error_response.raise_for_status.side_effect = RequestException("test exception")

    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api")
    mock_request_twitch_api.side_effect = [
        mock_error_response,
        mock_good_response,
    ]
    access_token = app.config["APP_ACCESS_TOKEN"]

    mock_get_app_access_token = mocker.patch("verifiedfirst.twitch.get_app_access_token")
    mock_get_app_access_token.side_effect = RequestException("refresh failed")

    with pytest.raises(RequestException):
        twitch.request_twitch_api_app(mock_request)

    caplog_messages = [rec.message for rec in caplog.records]
    assert caplog_messages == [
        "request to twitch api failed: test exception",
        "refreshing auth token",
        "failed to refresh auth token: refresh failed",
    ]
    mock_request_twitch_api.assert_has_calls(
        [
            mocker.call(access_token, mock_request),
        ]
    )
    assert app.config["APP_ACCESS_TOKEN"] == access_token


def test_get_broadcaster_from_token(app, mocker):
    """Test the get_broadcaster_from_token function."""
    mock_response = mocker.Mock()
    access_token = "aaaaaaaaaaaaaaaaaaaaaaaa"
    mock_response.json.return_value = {
        "data": [
            {
                "id": BROADCASTER_ID,
                "login": BROADCASTER_NAME,
                "display_name": "TwitchDev",
                "type": "",
                "broadcaster_type": "partner",
                "description": "",
                "profile_image_url": "",
                "offline_image_url": "",
                "view_count": 5980557,
                "email": "not-real@email.com",
                "created_at": "2016-12-14T20:32:28Z",
            }
        ]
    }
    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api")
    mock_request_twitch_api.return_value = mock_response

    broadcaster_name, broadcaster_id = twitch.get_broadcaster_from_token(access_token)

    request_args = mock_request_twitch_api.call_args_list[0].args

    mock_request_twitch_api.assert_called_once()
    assert request_args[0] == access_token
    request = request_args[1]
    assert request.method == "GET"
    assert request.headers == {"Client-ID": app.config["CLIENT_ID"]}
    assert broadcaster_name == BROADCASTER_NAME
    assert broadcaster_id == BROADCASTER_ID


def test_get_broadcaster_from_token_404(app, mocker):  # pylint: disable=unused-argument
    """Test that the get_broadcaster_from_token function raises the correct exception."""
    mock_response = mocker.Mock()
    access_token = "aaaaaaaaaaaaaaaaaaaaaaaa"
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = RequestException("test exception")
    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api")
    mock_request_twitch_api.return_value = mock_response

    with pytest.raises(RequestException):
        twitch.get_broadcaster_from_token(access_token)


def test_update_broadcaster_details(app, mocker, init_db):
    """Test update_broadcaster_details correctly updates access tokens."""
    init_db(app)
    access_token = "aaaaaaaaaaaaaaaaaaaaaaaa"
    refresh_token = "bbbbbbbbbbbbbbbbbbb"
    expected_broadcaster_name = BROADCASTER_NAME
    expected_broadcaster_id = BROADCASTER_ID
    mock_broadcaster_from_token = mocker.patch("verifiedfirst.twitch.get_broadcaster_from_token")
    mock_broadcaster_from_token.return_value = (expected_broadcaster_name, expected_broadcaster_id)

    broadcaster_name, broadcaster_id = twitch.update_broadcaster_details(
        access_token, refresh_token
    )

    broadcaster = Broadcaster.query.filter(Broadcaster.id == broadcaster_id).one()
    assert broadcaster.name == expected_broadcaster_name
    assert broadcaster.id == expected_broadcaster_id
    assert broadcaster.id == expected_broadcaster_id
    assert broadcaster.access_token == access_token
    assert broadcaster.refresh_token == refresh_token
    assert broadcaster_name == expected_broadcaster_name
    assert broadcaster_id == expected_broadcaster_id

    # test that the token can be updated
    access_token = "ccccccccccccccccccc"
    refresh_token = "ddddddddddddddddddd"
    broadcaster_name, broadcaster_id = twitch.update_broadcaster_details(
        access_token, refresh_token
    )

    broadcaster = Broadcaster.query.filter(Broadcaster.id == broadcaster_id).one()
    assert broadcaster.name == expected_broadcaster_name
    assert broadcaster.id == expected_broadcaster_id
    assert broadcaster.access_token == access_token
    assert broadcaster.refresh_token == refresh_token
    assert broadcaster_name == expected_broadcaster_name
    assert broadcaster_id == expected_broadcaster_id


def test_get_rewards(app, mocker):
    """Test get_rewards function."""
    mock_response = mocker.Mock()
    access_token = "aaaaaaaaaaaaaaaaaaaaaaaa"
    rewards_json = {
        "data": [
            {
                "broadcaster_name": BROADCASTER_NAME,
                "broadcaster_login": BROADCASTER_NAME,
                "broadcaster_id": BROADCASTER_ID,
                "id": "92af127c-7326-4483-a52b-b0da0be61c01",
                "image": None,
                "background_color": "#00E5CB",
                "is_enabled": True,
                "cost": 50000,
                "title": "game analysis",
                "prompt": "",
                "is_user_input_required": False,
                "max_per_stream_setting": {"is_enabled": False, "max_per_stream": 0},
                "max_per_user_per_stream_setting": {
                    "is_enabled": False,
                    "max_per_user_per_stream": 0,
                },
                "global_cooldown_setting": {"is_enabled": False, "global_cooldown_seconds": 0},
                "is_paused": False,
                "is_in_stock": True,
                "default_image": {
                    "url_1x": "https://static-cdn.jtvnw.net/custom-reward-images/default-1.png",
                    "url_2x": "https://static-cdn.jtvnw.net/custom-reward-images/default-2.png",
                    "url_4x": "https://static-cdn.jtvnw.net/custom-reward-images/default-4.png",
                },
                "should_redemptions_skip_request_queue": False,
                "redemptions_redeemed_current_stream": None,
                "cooldown_expires_at": None,
            },
            {
                "broadcaster_name": BROADCASTER_NAME,
                "broadcaster_login": BROADCASTER_NAME,
                "broadcaster_id": BROADCASTER_ID,
                "id": "536b13c5-8f49-49b9-81e1-18e52b028919",
                "image": None,
                "background_color": "#00E5CB",
                "is_enabled": True,
                "cost": 1,
                "title": "first",
                "prompt": "",
                "is_user_input_required": False,
                "max_per_stream_setting": {"is_enabled": True, "max_per_stream": 1},
                "max_per_user_per_stream_setting": {
                    "is_enabled": False,
                    "max_per_user_per_stream": 0,
                },
                "global_cooldown_setting": {"is_enabled": False, "global_cooldown_seconds": 0},
                "is_paused": False,
                "is_in_stock": True,
                "default_image": {
                    "url_1x": "https://static-cdn.jtvnw.net/custom-reward-images/default-1.png",
                    "url_2x": "https://static-cdn.jtvnw.net/custom-reward-images/default-2.png",
                    "url_4x": "https://static-cdn.jtvnw.net/custom-reward-images/default-4.png",
                },
                "should_redemptions_skip_request_queue": False,
                "redemptions_redeemed_current_stream": None,
                "cooldown_expires_at": None,
            },
        ]
    }
    mock_response.json.return_value = rewards_json
    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api")
    mock_request_twitch_api.return_value = mock_response
    mock_broadcaster = mocker.Mock()
    mock_broadcaster.id = BROADCASTER_ID
    mock_broadcaster.access_token = access_token

    rewards = twitch.get_rewards(mock_broadcaster)

    request_args = mock_request_twitch_api.call_args_list[0].args

    mock_request_twitch_api.assert_called_once()
    assert request_args[0] == access_token
    request = request_args[1]
    assert request.method == "GET"
    assert request.headers == {"Client-ID": app.config["CLIENT_ID"]}
    assert request.params == {
        "broadcaster_id": BROADCASTER_ID,
        "only_manageable_rewards": "False",
    }

    assert rewards == rewards_json["data"]


def test_get_rewards_403(app, mocker):  # pylint: disable=unused-argument
    """Test get_rewards throws the correct exception if the twitch API returns an error."""

    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api_broadcaster")
    mock_request_twitch_api.side_effect = RequestException("test exception")
    mock_broadcaster = mocker.Mock()
    access_token = "aaaaaaaaaaaaaaaaaaaaaaaa"
    mock_broadcaster.access_token = access_token

    with pytest.raises(RequestException):
        twitch.get_rewards(mock_broadcaster)


def test_get_firsts(app, mocker, init_db):
    """Test get_firsts function."""

    database = init_db(app)

    broadcaster = mocker.Mock()
    broadcaster.id = BROADCASTER_ID

    users = {
        "user1": 5,
        "user2": 3,
        "user3": 1,
    }

    # Add "firsts" to the database
    for user, count in users.items():
        for _ in range(0, count):
            first = First(broadcaster_id=BROADCASTER_ID, name=user)
            database.session.add(first)
    database.session.commit()

    # tests the first counts match what is in the db
    firsts = twitch.get_firsts(broadcaster)

    assert len(firsts.keys()) == 3
    assert firsts["user1"] == users["user1"]
    assert firsts["user2"] == users["user2"]
    assert firsts["user3"] == users["user3"]


def test_create_eventsub(app, mocker):
    """Test create_eventsub function."""

    mock_response = mocker.Mock()
    mock_response.json.return_value = EVENTSUB_JSON
    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api_app")
    mock_request_twitch_api.return_value = mock_response
    mock_broadcaster = mocker.Mock()
    mock_broadcaster.id = BROADCASTER_ID

    eventsub_id = twitch.create_eventsub(mock_broadcaster, REWARD_ID)

    request_args = mock_request_twitch_api.call_args_list[0].args

    mock_request_twitch_api.assert_called_once()
    request = request_args[0]
    assert request.method == "POST"
    assert request.headers == {"Client-ID": app.config["CLIENT_ID"]}
    assert request.json == {
        "type": "channel.channel_points_custom_reward_redemption.add",
        "version": "1",
        "condition": {
            "broadcaster_user_id": str(BROADCASTER_ID),
            "reward_id": REWARD_ID,
        },
        "transport": {
            "method": "webhook",
            "callback": app.config["EVENTSUB_CALLBACK_URL"],
            "secret": app.config["EVENTSUB_SECRET"],
        },
    }
    assert eventsub_id == EVENTSUB_ID


def test_create_eventsub_403(app, mocker):  # pylint: disable=unused-argument
    """Test create_eventsub throws the correct exception if the twitch API returns an error."""

    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api_app")
    mock_request_twitch_api.side_effect = RequestException("test exception")
    mock_broadcaster = mocker.Mock()
    access_token = "aaaaaaaaaaaaaaaaaaaaaaaa"
    mock_broadcaster.access_token = access_token

    with pytest.raises(RequestException):
        twitch.create_eventsub(mock_broadcaster, REWARD_ID)


def test_get_eventsubs(app, mocker):
    """Test get_eventsubs function."""

    mock_response = mocker.Mock()
    mock_response.json.return_value = EVENTSUB_JSON
    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api_app")
    mock_request_twitch_api.return_value = mock_response
    mock_broadcaster = mocker.Mock()
    mock_broadcaster.id = BROADCASTER_ID

    eventsubs = twitch.get_eventsubs(mock_broadcaster)

    request_args = mock_request_twitch_api.call_args_list[0].args
    mock_request_twitch_api.assert_called_once()
    request = request_args[0]
    assert request.method == "GET"
    assert request.headers == {"Client-ID": app.config["CLIENT_ID"]}
    assert request.params == {"user_id": BROADCASTER_ID}
    assert eventsubs == EVENTSUB_JSON["data"]


def test_get_eventsubs_bad_format(app, mocker):  # pylint: disable=unused-argument
    """Test get_eventsubs throws correct exception when data is in wrong format."""

    mock_response = mocker.Mock()
    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api_app")
    mock_request_twitch_api.return_value = mock_response
    mock_broadcaster = mocker.Mock()
    mock_broadcaster.id = BROADCASTER_ID

    # test badly formatted data key
    mock_response.json.return_value = {"data": {}}
    with pytest.raises(RequestException):
        twitch.get_eventsubs(mock_broadcaster)

    # test missing data key
    mock_response.json.return_value = {}
    with pytest.raises(RequestException):
        twitch.get_eventsubs(mock_broadcaster)

    # test non-json response
    mock_response.json.return_value = "not json"
    with pytest.raises(RequestException):
        twitch.get_eventsubs(mock_broadcaster)


def test_get_eventsub_fail(app, mocker):  # pylint: disable=unused-argument
    """Test get_eventsub throws the correct exception if the twitch API returns an error."""

    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api_app")
    mock_request_twitch_api.side_effect = RequestException("test exception")
    mock_broadcaster = mocker.Mock()
    access_token = "aaaaaaaaaaaaaaaaaaaaaaaa"
    mock_broadcaster.access_token = access_token

    with pytest.raises(RequestException):
        twitch.get_eventsubs(mock_broadcaster)


def test_delete_eventsub(app, mocker):  # pylint: disable=unused-argument
    """Test delete_eventsub function."""

    mock_response = mocker.Mock()
    mock_response.text = "test"
    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api_app")
    mock_request_twitch_api.return_value = mock_response

    twitch.delete_eventsub(EVENTSUB_ID)


def test_update_eventsub(app, init_db, mocker):
    """Test new eventsub gets created if it doesn't exist."""

    database = init_db(app)

    mock_get_eventsubs = mocker.patch("verifiedfirst.twitch.get_eventsubs")
    mock_get_eventsubs.return_value = []

    mock_create_eventsub = mocker.patch("verifiedfirst.twitch.create_eventsub")
    mock_create_eventsub.return_value = EVENTSUB_ID

    mock_delete_eventsub = mocker.patch("verifiedfirst.twitch.delete_eventsub")

    broadcaster = Broadcaster(
        id=BROADCASTER_ID,
        name=BROADCASTER_NAME,
        access_token="aaaaaaaaaaaaaaaaaaaaaaaa",
        refresh_token="bbbbbbbbbbbbbbbbbbbbbbbb",
    )
    database.session.add(broadcaster)
    database.session.commit()

    # Test new eventsub gets created if it doesn't exist
    matching_eventsub = twitch.update_eventsub(broadcaster, REWARD_ID)
    updated_broadcaster = Broadcaster.query.filter(Broadcaster.id == BROADCASTER_ID).one()

    assert mock_create_eventsub.called_with()
    assert not mock_delete_eventsub.called
    mock_get_eventsubs.assert_has_calls(
        [
            mocker.call(broadcaster),
        ]
    )
    mock_create_eventsub.assert_has_calls(
        [
            mocker.call(broadcaster, REWARD_ID),
        ]
    )
    assert matching_eventsub == EVENTSUB_ID
    assert updated_broadcaster.eventsub_id == EVENTSUB_ID

    # Test that eventsub is not updated if it is already correct in the database
    mock_get_eventsubs.reset_mock()
    mock_create_eventsub.reset_mock()
    mock_delete_eventsub.reset_mock()
    mock_get_eventsubs.return_value = EVENTSUB_JSON["data"]

    matching_eventsub = twitch.update_eventsub(broadcaster, REWARD_ID)
    updated_broadcaster = Broadcaster.query.filter(Broadcaster.id == BROADCASTER_ID).one()

    assert not mock_delete_eventsub.called
    assert not mock_create_eventsub.called
    mock_get_eventsubs.assert_has_calls(
        [
            mocker.call(broadcaster),
        ]
    )
    assert matching_eventsub == EVENTSUB_ID
    assert updated_broadcaster.eventsub_id == EVENTSUB_ID

    # Test that the eventsub gets updated if the reward_id changes
    new_reward_id = "79f26a1a-fd0e-48d9-a0e8-a91247261e43"
    new_eventsub_id = "18462e51-08b5-4a54-bbe8-b818a48d7a0c"
    mock_get_eventsubs.reset_mock()
    mock_create_eventsub.reset_mock()
    mock_delete_eventsub.reset_mock()
    mock_get_eventsubs.return_value = EVENTSUB_JSON["data"]
    mock_create_eventsub.return_value = new_eventsub_id
    broadcaster = updated_broadcaster

    matching_eventsub = twitch.update_eventsub(broadcaster, new_reward_id)
    updated_broadcaster = Broadcaster.query.filter(Broadcaster.id == BROADCASTER_ID).one()

    mock_delete_eventsub.assert_has_calls(
        [
            mocker.call(EVENTSUB_ID),
        ]
    )
    mock_get_eventsubs.assert_has_calls(
        [
            mocker.call(broadcaster),
        ]
    )
    mock_create_eventsub.assert_has_calls(
        [
            mocker.call(broadcaster, new_reward_id),
        ]
    )

    assert matching_eventsub == new_eventsub_id
    assert updated_broadcaster.eventsub_id == new_eventsub_id


def test_add_first(app, init_db, patch_current_time):
    """Test add_first function."""
    with patch_current_time("2000-01-01"):
        init_db(app)
        first1 = twitch.add_first(BROADCASTER_ID, "testuser1")
        first2 = twitch.add_first(BROADCASTER_ID, "testuser2")

        assert first1.name == "testuser1"
        assert first1.broadcaster_id == BROADCASTER_ID
        assert first1.timestamp == datetime(2000, 1, 1, 0, 0, 0)
        assert first2.name == "testuser2"
        assert first2.broadcaster_id == BROADCASTER_ID
        assert first2.timestamp == datetime(2000, 1, 1, 0, 0, 0)


def test_update_reward(app, init_db):
    """Test update_reward function."""

    database = init_db(app)

    broadcaster = Broadcaster(
        id=BROADCASTER_ID,
        name=BROADCASTER_NAME,
        access_token="aaaaaaaaaaaaaaaaaaaaaaaa",
        refresh_token="bbbbbbbbbbbbbbbbbbbbbbbb",
    )
    database.session.add(broadcaster)
    database.session.commit()

    # test that the reward_id can be updated
    reward_id = twitch.update_reward(broadcaster, REWARD_ID)
    updated_broadcaster = Broadcaster.query.filter(Broadcaster.id == BROADCASTER_ID).one()

    assert reward_id == REWARD_ID
    assert updated_broadcaster.reward_id == REWARD_ID


def test_get_broadcaster(app, init_db):
    """Test get_broadcaster function."""

    database = init_db(app)

    expected_broadcaster = Broadcaster(
        id=BROADCASTER_ID,
        name=BROADCASTER_NAME,
        access_token="aaaaaaaaaaaaaaaaaaaaaaaa",
        refresh_token="bbbbbbbbbbbbbbbbbbbbbbbb",
    )
    database.session.add(expected_broadcaster)
    database.session.commit()

    broadcaster = twitch.get_broadcaster(BROADCASTER_ID)

    assert broadcaster == expected_broadcaster
