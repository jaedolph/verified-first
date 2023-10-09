"""Tests for main routes."""
from datetime import datetime

from flask import url_for
from requests import RequestException

from . import defaults


def test_firsts(client, mocker):
    """Test the /firsts endpoint works."""

    firsts = {
        "user1": 5,
        "user2": 3,
        "user3": 1,
    }
    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "viewer")
    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_broadcaster = mocker.Mock()
    mock_get_broadcaster.return_value = mock_broadcaster
    mock_get_firsts = mocker.patch("verifiedfirst.twitch.get_firsts")
    mock_get_firsts.return_value = firsts

    # test with no time ranges
    resp = client.get(url_for("main.firsts"))
    mock_get_broadcaster.assert_called_with(defaults.CHANNEL_ID)
    mock_get_firsts.assert_called_with(mock_broadcaster, start_time=None, end_time=None)
    assert resp.status_code == 200
    assert resp.json == firsts

    # test with end time
    resp = client.get(
        url_for("main.firsts"),
        query_string={
            "end_time": "2020-01-01",
        },
    )
    mock_get_firsts.assert_called_with(
        mock_broadcaster, start_time=None, end_time=datetime(2020, 1, 1)
    )
    assert resp.status_code == 200
    assert resp.json == firsts

    # test with start and end time
    resp = client.get(
        url_for("main.firsts"),
        query_string={
            "end_time": "2020-01-01",
            "start_time": "2019-01-01",
        },
    )
    mock_get_firsts.assert_called_with(
        mock_broadcaster, start_time=datetime(2019, 1, 1), end_time=datetime(2020, 1, 1)
    )
    assert resp.status_code == 200
    assert resp.json == firsts


def test_firsts_no_broadcaster(client, mocker):
    """Test the /firsts returns a 403 if the broadcaster is not authed."""

    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "viewer")
    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_get_broadcaster.return_value = None
    mock_get_firsts = mocker.patch("verifiedfirst.twitch.get_firsts")

    resp = client.get(url_for("main.firsts"))

    mock_get_broadcaster.assert_called_with(defaults.CHANNEL_ID)
    mock_get_firsts.assert_not_called()
    assert resp.status_code == 403
    assert resp.json == {"error": "broadcaster is not authed yet"}


def test_firsts_no_firsts(client, mocker):
    """Test the /firsts returns a 404 if no firsts are returned."""

    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "viewer")
    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_broadcaster = mocker.Mock()
    mock_get_broadcaster.return_value = mock_broadcaster
    mock_get_firsts = mocker.patch("verifiedfirst.twitch.get_firsts")
    mock_get_firsts.return_value = {}

    resp = client.get(url_for("main.firsts"))

    mock_get_broadcaster.assert_called_with(defaults.CHANNEL_ID)
    mock_get_firsts.assert_called_with(mock_broadcaster, start_time=None, end_time=None)
    assert resp.status_code == 404
    assert resp.json == {"error": "could not get firsts"}


def test_eventsub_create(client, mocker):
    """Test the /eventsub/create endpoint works."""

    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "broadcaster")
    mock_broadcaster = mocker.Mock()
    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_get_broadcaster.return_value = mock_broadcaster
    mock_update_reward = mocker.patch("verifiedfirst.twitch.update_reward")
    mock_update_reward.return_value = defaults.REWARD_ID
    mock_update_eventsub = mocker.patch("verifiedfirst.twitch.update_eventsub")
    mock_update_eventsub.return_value = defaults.EVENTSUB_ID

    resp = client.post(
        url_for("main.eventsub_create"), query_string={"reward_id": defaults.REWARD_ID}
    )

    assert resp.status_code == 200
    assert resp.json["eventsub_id"] == defaults.EVENTSUB_ID
    mock_get_broadcaster.assert_called_with(defaults.CHANNEL_ID)
    mock_update_reward.assert_called_with(mock_broadcaster, defaults.REWARD_ID)
    mock_update_eventsub.assert_called_with(mock_broadcaster, defaults.REWARD_ID)


def test_eventsub_create_not_broadcaster(client, mocker):
    """Test that only broadcasters can use the /eventsub/create endpoint."""

    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")

    mock_jwt.return_value = (defaults.CHANNEL_ID, "viewer")
    resp = client.post(
        url_for("main.eventsub_create"), query_string={"reward_id": defaults.REWARD_ID}
    )

    assert resp.status_code == 403
    assert resp.json["error"] == "user role is not broadcaster"


def test_eventsub_create_undefined(client, mocker):
    """Test that an 'undefined' reward id is rejected."""

    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    reward_id = "undefined"

    mock_jwt.return_value = (defaults.CHANNEL_ID, "broadcaster")
    resp = client.post(url_for("main.eventsub_create"), query_string={"reward_id": reward_id})

    assert resp.status_code == 400
    assert resp.json["error"] == "reward id is undefined"


def test_eventsub_create_unauthed(client, mocker):
    """Test that a 403 is returned if the broadcaster has not authed yet."""

    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "broadcaster")
    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_get_broadcaster.return_value = None

    resp = client.post(
        url_for("main.eventsub_create"), query_string={"reward_id": defaults.REWARD_ID}
    )

    assert resp.status_code == 403
    assert resp.json["error"] == "broadcaster is not authed yet"
    mock_get_broadcaster.assert_called_with(defaults.CHANNEL_ID)


def test_rewards(client, mocker):
    """Test the /rewards endpoint works."""

    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "broadcaster")
    mock_broadcaster = mocker.Mock()
    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_get_broadcaster.return_value = mock_broadcaster
    mock_get_rewards = mocker.patch("verifiedfirst.twitch.get_rewards")
    rewards_json = defaults.REWARDS_JSON["data"]
    mock_get_rewards.return_value = rewards_json

    resp = client.get(url_for("main.rewards"))

    assert resp.status_code == 200
    assert resp.json == rewards_json


def test_rewards_not_broadcaster(client, mocker):
    """Test that only broadcasters can get rewards."""

    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "viewer")

    resp = client.get(url_for("main.rewards"))

    assert resp.status_code == 403
    assert resp.json["error"] == "user role is not broadcaster"


def test_rewards_unauthed(client, mocker):
    """Test that a 403 is returned if the broadcaster has not authed yet."""

    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "broadcaster")
    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_get_broadcaster.return_value = None

    resp = client.get(url_for("main.rewards"))

    assert resp.status_code == 403
    assert resp.json["error"] == "broadcaster is not authed yet"


def test_rewards_no_rewards(client, mocker):
    """Test that 500 error if getting rewards fails."""

    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "broadcaster")
    mock_broadcaster = mocker.Mock()
    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_get_broadcaster.return_value = mock_broadcaster
    mock_get_rewards = mocker.patch("verifiedfirst.twitch.get_rewards")
    mock_get_rewards.side_effect = RequestException

    resp = client.get(url_for("main.rewards"))

    assert resp.status_code == 500
    assert resp.json["error"] == "failed to get rewards for broadcaster"


def test_eventsub_challenge(client, mocker):
    """Test the /eventsub endpoint responds to a challenge request."""

    mock_verify_eventsub_message = mocker.patch("verifiedfirst.verify.verify_eventsub_message")
    mock_verify_eventsub_message.return_value = True
    mock_add_first = mocker.patch("verifiedfirst.twitch.add_first")

    # check that a challenge is responded to
    resp = client.post(
        url_for("main.eventsub"),
        headers=[
            ("Twitch-Eventsub-Message-Type", "webhook_callback_verification"),
        ],
        json=defaults.EVENTSUB_CHALLENGE_JSON,
    )
    mock_add_first.assert_not_called()
    assert resp.text == defaults.CHALLENGE
    assert resp.status_code == 200


def test_eventsub_notification(client, mocker):
    """Test an eventsub notification adds a "first" for the correct broadcaster."""

    mock_verify_eventsub_message = mocker.patch("verifiedfirst.verify.verify_eventsub_message")
    mock_verify_eventsub_message.return_value = True
    mock_add_first = mocker.patch("verifiedfirst.twitch.add_first")
    first_json = {
        "broadcaster_id": defaults.BROADCASTER_ID,
        "id": 26,
        "name": defaults.TEST_USER_NAME,
        "timestamp": "Thu, 05 Oct 2023 10:51:14 GMT",
    }
    mock_add_first.return_value = first_json

    # check that a notification adds a new "first"
    resp = client.post(
        url_for("main.eventsub"),
        headers=[
            ("Twitch-Eventsub-Message-Type", "notification"),
        ],
        json=defaults.EVENTSUB_NOTIFICATION_JSON,
    )

    assert resp.json == first_json
    assert resp.status_code == 200
    mock_add_first.assert_called_with(defaults.BROADCASTER_ID, defaults.TEST_USER_NAME)


def test_eventsub_revocation(client, mocker):
    """Test an eventsub revocation deletes the eventsub for that broadcaster."""

    mock_verify_eventsub_message = mocker.patch("verifiedfirst.verify.verify_eventsub_message")
    mock_verify_eventsub_message.return_value = True
    mock_add_first = mocker.patch("verifiedfirst.twitch.add_first")
    mock_delete_eventsub = mocker.patch("verifiedfirst.twitch.delete_eventsub")

    # check eventsub can be revoked
    resp = client.post(
        url_for("main.eventsub"),
        headers=[
            ("Twitch-Eventsub-Message-Type", "revocation"),
        ],
        json=defaults.EVENTSUB_REVOCATION_JSON,
    )

    assert resp.json["eventsub_id"] == defaults.EVENTSUB_ID
    assert resp.status_code == 200
    mock_delete_eventsub.assert_called_with(defaults.EVENTSUB_ID)
    mock_add_first.assert_not_called()


def test_eventsub_bad_message_type(client, mocker):
    """Test that an unhandled message type throws an error."""

    mock_verify_eventsub_message = mocker.patch("verifiedfirst.verify.verify_eventsub_message")
    mock_verify_eventsub_message.return_value = True

    # check eventsub can be revoked
    resp = client.post(
        url_for("main.eventsub"),
        headers=[
            ("Twitch-Eventsub-Message-Type", "bad_type"),
        ],
        json=defaults.EVENTSUB_REVOCATION_JSON,
    )

    assert resp.status_code == 401
    assert resp.json["error"] == "could not process eventsub"


def test_eventsub_bad_hmac(client, mocker):
    """Test the /eventsub endpoint fails if hmac doesn't verify."""

    mock_verify_eventsub_message = mocker.patch("verifiedfirst.verify.verify_eventsub_message")
    mock_verify_eventsub_message.return_value = False

    resp = client.post(
        url_for("main.eventsub"),
        headers=[
            ("Twitch-Eventsub-Message-Type", "webhook_callback_verification"),
        ],
        json=defaults.EVENTSUB_CHALLENGE_JSON,
    )

    assert resp.json["error"] == "could not verify hmac in eventsub message"
    assert resp.status_code == 401
