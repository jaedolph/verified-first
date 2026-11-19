"""Tests for main routes."""

import copy
from datetime import datetime

import pytest
from flask import url_for
from requests import RequestException
from sqlalchemy.exc import SQLAlchemyError

from verifiedfirst.models.broadcasters import Broadcaster

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


def test_avatars(client, mocker):
    """Test the /avatars endpoint works."""
    avatars = {
        "user1": "https://example.com/user1.png",
        "user2": "https://example.com/user2.png",
    }
    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "viewer")
    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_broadcaster = mocker.Mock()
    mock_get_broadcaster.return_value = mock_broadcaster
    mock_get_avatars = mocker.patch("verifiedfirst.twitch.get_avatars")
    mock_get_avatars.return_value = avatars

    resp = client.get(url_for("main.avatars"))

    mock_get_broadcaster.assert_called_with(defaults.CHANNEL_ID)
    mock_get_avatars.assert_called_with(mock_broadcaster)
    assert resp.status_code == 200
    assert resp.json == avatars


def test_avatars_no_broadcaster(client, mocker):
    """Test the /avatars returns a 403 if the broadcaster is not authed."""
    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "viewer")
    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_get_broadcaster.return_value = None
    mock_get_avatars = mocker.patch("verifiedfirst.twitch.get_avatars")

    resp = client.get(url_for("main.avatars"))

    mock_get_broadcaster.assert_called_with(defaults.CHANNEL_ID)
    mock_get_avatars.assert_not_called()
    assert resp.status_code == 403
    assert resp.json == {"error": "broadcaster is not authed yet"}


def test_eventsub_create(client, mocker):
    """Test the /eventsub/create endpoint works."""
    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "broadcaster")
    mock_broadcaster = mocker.Mock()
    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_get_broadcaster.return_value = mock_broadcaster
    mock_twitch = mocker.Mock()
    mock_update_reward = mocker.patch(
        "verifiedfirst.twitch.update_reward", mock_twitch.update_reward
    )
    mock_update_reward.return_value = defaults.REWARD_ID
    mock_update_eventsub = mocker.patch(
        "verifiedfirst.twitch.update_eventsub", mock_twitch.update_eventsub
    )
    mock_update_eventsub.return_value = defaults.EVENTSUB_ID

    resp = client.post(
        url_for("main.eventsub_create"), query_string={"reward_id": defaults.REWARD_ID}
    )

    assert resp.status_code == 200
    assert resp.json["eventsub_id"] == defaults.EVENTSUB_ID
    mock_get_broadcaster.assert_called_with(defaults.CHANNEL_ID)
    # the reward is only stored once the eventsub exists
    assert mock_twitch.mock_calls == [
        mocker.call.update_eventsub(mock_broadcaster, defaults.REWARD_ID),
        mocker.call.update_reward(mock_broadcaster, defaults.REWARD_ID),
    ]


def test_eventsub_create_eventsub_fails(client, mocker):
    """Test the stored reward isn't changed if the eventsub can't be created, so /rewards doesn't
    report a reward that isn't being listened for."""
    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "broadcaster")
    mock_broadcaster = mocker.Mock()
    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_get_broadcaster.return_value = mock_broadcaster
    mock_update_reward = mocker.patch("verifiedfirst.twitch.update_reward")
    mock_update_eventsub = mocker.patch("verifiedfirst.twitch.update_eventsub")
    mock_update_eventsub.side_effect = RequestException("could not create eventsub")

    with pytest.raises(RequestException):
        client.post(url_for("main.eventsub_create"), query_string={"reward_id": defaults.REWARD_ID})

    mock_update_eventsub.assert_called_with(mock_broadcaster, defaults.REWARD_ID)
    mock_update_reward.assert_not_called()


def test_eventsub_create_not_broadcaster(client, mocker):
    """Test that only broadcasters can use the /eventsub/create endpoint."""
    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")

    mock_jwt.return_value = (defaults.CHANNEL_ID, "viewer")
    resp = client.post(
        url_for("main.eventsub_create"), query_string={"reward_id": defaults.REWARD_ID}
    )

    assert resp.status_code == 403
    assert resp.json["error"] == "user role is not broadcaster"


def test_eventsub_create_missing_reward_id(client, mocker):
    """Test that a missing reward_id query param returns 400."""
    mock_jwt = mocker.patch("verifiedfirst.verify.verify_jwt")
    mock_jwt.return_value = (defaults.CHANNEL_ID, "broadcaster")

    resp = client.post(url_for("main.eventsub_create"))

    assert resp.status_code == 400
    assert resp.json["error"] == "reward_id is required"


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
    rewards_json = copy.deepcopy(defaults.REWARDS_JSON["data"])
    mock_broadcaster = mocker.Mock()
    mock_broadcaster.reward_id = rewards_json[1]["id"]
    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_get_broadcaster.return_value = mock_broadcaster
    mock_get_rewards = mocker.patch("verifiedfirst.twitch.get_rewards")
    mock_get_rewards.return_value = copy.deepcopy(rewards_json)

    resp = client.get(url_for("main.rewards"))

    assert resp.status_code == 200
    # the reward the broadcaster has configured on this instance is marked
    assert resp.json == [
        {**reward, "configured": index == 1} for index, reward in enumerate(rewards_json)
    ]


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
    mock_add_first.assert_called_with(
        defaults.BROADCASTER_ID, defaults.TEST_USER_ID, defaults.TEST_USER_NAME
    )


def add_broadcaster(database, eventsub_id=defaults.EVENTSUB_ID):  # pylint: disable=missing-type-doc
    """Add a broadcaster using the default reward to the database.

    :param database: database to add the broadcaster to
    :param eventsub_id: eventsub id to store for the broadcaster
    """
    database.session.add(
        Broadcaster(
            id=defaults.BROADCASTER_ID,
            name=defaults.BROADCASTER_NAME,
            access_token=defaults.AUTH_ACCESS_TOKEN,
            refresh_token=defaults.AUTH_REFRESH_TOKEN,
            reward_id=defaults.REWARD_ID,
            eventsub_id=eventsub_id,
        )
    )
    database.session.commit()


def post_revocation(client, reason, subscription=None):  # pylint: disable=missing-type-doc
    """Post an eventsub revocation message, closing the response like the wsgi server would after
    sending it.

    :param client: test client
    :param reason: revocation reason to put in the subscription status
    :param subscription: subscription to send instead of the default one
    :return: response from the /eventsub endpoint
    """
    if subscription is None:
        subscription = copy.deepcopy(defaults.EVENTSUB_REVOCATION_JSON["subscription"])
        subscription["status"] = reason
    resp = client.post(
        url_for("main.eventsub"),
        headers=[
            ("Twitch-Eventsub-Message-Type", "revocation"),
        ],
        json={"subscription": subscription},
    )
    resp.get_data()
    resp.close()
    return resp


def test_eventsub_revocation(client, mocker, caplog):
    """Test an eventsub revocation deletes the eventsub and logs why it was revoked."""
    mock_verify_eventsub_message = mocker.patch("verifiedfirst.verify.verify_eventsub_message")
    mock_verify_eventsub_message.return_value = True
    mock_add_first = mocker.patch("verifiedfirst.twitch.add_first")
    mock_delete_eventsub = mocker.patch("verifiedfirst.twitch.delete_eventsub")
    mock_get_broadcaster = mocker.patch("verifiedfirst.twitch.get_broadcaster")
    mock_get_broadcaster.return_value = None
    mock_update_eventsub = mocker.patch("verifiedfirst.twitch.update_eventsub")

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
    mock_get_broadcaster.assert_called_with(defaults.BROADCASTER_ID)
    mock_update_eventsub.assert_not_called()
    mock_add_first.assert_not_called()
    assert (
        f"eventsub revoked for broadcaster_id={defaults.BROADCASTER_ID} "
        f"eventsub_id={defaults.EVENTSUB_ID} reward_id={defaults.REWARD_ID} "
        "reason=authorization_revoked"
    ) in caplog.text
    assert any(
        record.levelname == "WARNING" and "reason=authorization_revoked" in record.getMessage()
        for record in caplog.records
    )


def test_eventsub_revocation_recreate(app, client, init_db, mocker):
    """Test a recoverable revocation of the broadcaster's current eventsub recreates it after the
    response is sent."""
    database = init_db(app)
    add_broadcaster(database)
    mock_verify_eventsub_message = mocker.patch("verifiedfirst.verify.verify_eventsub_message")
    mock_verify_eventsub_message.return_value = True
    mock_delete_eventsub = mocker.patch("verifiedfirst.twitch.delete_eventsub")
    mock_update_eventsub = mocker.patch("verifiedfirst.twitch.update_eventsub")
    mock_update_eventsub.return_value = "18462e51-08b5-4a54-bbe8-b818a48d7a0c"

    revocation = copy.deepcopy(defaults.EVENTSUB_REVOCATION_JSON)
    revocation["subscription"]["status"] = "notification_failures_exceeded"
    resp = client.post(
        url_for("main.eventsub"),
        headers=[("Twitch-Eventsub-Message-Type", "revocation")],
        json=revocation,
    )

    assert resp.status_code == 200
    assert resp.json["eventsub_id"] == defaults.EVENTSUB_ID
    mock_delete_eventsub.assert_called_with(defaults.EVENTSUB_ID)
    mock_update_eventsub.assert_not_called()

    resp.close()

    mock_update_eventsub.assert_called_once()
    broadcaster, reward_id = mock_update_eventsub.call_args.args
    assert broadcaster.id == defaults.BROADCASTER_ID
    assert reward_id == defaults.REWARD_ID


def test_eventsub_revocation_recreate_config_changed(app, client, init_db, mocker):
    """Test the eventsub isn't recreated if the broadcaster's config changed before the response was
    sent."""
    database = init_db(app)
    add_broadcaster(database)
    mock_verify_eventsub_message = mocker.patch("verifiedfirst.verify.verify_eventsub_message")
    mock_verify_eventsub_message.return_value = True
    mocker.patch("verifiedfirst.twitch.delete_eventsub")
    mock_update_eventsub = mocker.patch("verifiedfirst.twitch.update_eventsub")

    revocation = copy.deepcopy(defaults.EVENTSUB_REVOCATION_JSON)
    revocation["subscription"]["status"] = "notification_failures_exceeded"
    resp = client.post(
        url_for("main.eventsub"),
        headers=[("Twitch-Eventsub-Message-Type", "revocation")],
        json=revocation,
    )
    broadcaster = database.session.get(Broadcaster, defaults.BROADCASTER_ID)
    broadcaster.eventsub_id = "18462e51-08b5-4a54-bbe8-b818a48d7a0c"
    database.session.commit()

    resp.close()

    assert resp.status_code == 200
    mock_update_eventsub.assert_not_called()


def test_eventsub_revocation_not_recoverable(app, client, init_db, mocker):
    """Test an unrecoverable revocation doesn't recreate the eventsub and clears its id."""
    database = init_db(app)
    mock_verify_eventsub_message = mocker.patch("verifiedfirst.verify.verify_eventsub_message")
    mock_verify_eventsub_message.return_value = True
    mock_delete_eventsub = mocker.patch("verifiedfirst.twitch.delete_eventsub")
    mock_update_eventsub = mocker.patch("verifiedfirst.twitch.update_eventsub")

    # version_removed can't be recovered from as create_eventsub always uses version 1
    for reason in ("authorization_revoked", "user_removed", "version_removed"):
        database.session.query(Broadcaster).delete()
        add_broadcaster(database)

        resp = post_revocation(client, reason)

        assert resp.status_code == 200
        mock_delete_eventsub.assert_called_with(defaults.EVENTSUB_ID)
        mock_update_eventsub.assert_not_called()
        broadcaster = database.session.get(Broadcaster, defaults.BROADCASTER_ID)
        assert broadcaster.eventsub_id is None
        assert broadcaster.reward_id == defaults.REWARD_ID


def test_eventsub_revocation_not_recoverable_db_error(app, client, init_db, mocker, caplog):
    """Test a revocation still returns 2xx if the eventsub id can't be cleared."""
    database = init_db(app)
    add_broadcaster(database)
    mock_verify_eventsub_message = mocker.patch("verifiedfirst.verify.verify_eventsub_message")
    mock_verify_eventsub_message.return_value = True
    mocker.patch("verifiedfirst.twitch.delete_eventsub")
    mocker.patch.object(database.session, "commit").side_effect = SQLAlchemyError("db down")

    resp = post_revocation(client, "authorization_revoked")

    assert resp.status_code == 200
    assert (
        f"could not clear eventsub_id for broadcaster_id={defaults.BROADCASTER_ID}: db down"
        in caplog.text
    )


def test_eventsub_revocation_not_current(app, client, init_db, mocker):
    """Test revoking an eventsub that isn't the broadcaster's current one doesn't recreate it."""
    database = init_db(app)
    current_eventsub_id = "18462e51-08b5-4a54-bbe8-b818a48d7a0c"
    add_broadcaster(database, eventsub_id=current_eventsub_id)
    mock_verify_eventsub_message = mocker.patch("verifiedfirst.verify.verify_eventsub_message")
    mock_verify_eventsub_message.return_value = True
    mock_delete_eventsub = mocker.patch("verifiedfirst.twitch.delete_eventsub")
    mock_update_eventsub = mocker.patch("verifiedfirst.twitch.update_eventsub")

    # a different eventsub id to the one stored for the broadcaster
    for reason in ("notification_failures_exceeded", "authorization_revoked"):
        resp = post_revocation(client, reason)

        assert resp.status_code == 200
        mock_delete_eventsub.assert_called_with(defaults.EVENTSUB_ID)
        mock_update_eventsub.assert_not_called()
        broadcaster = database.session.get(Broadcaster, defaults.BROADCASTER_ID)
        assert broadcaster.eventsub_id == current_eventsub_id

    # the current eventsub id but for a different reward
    broadcaster.eventsub_id = defaults.EVENTSUB_ID
    broadcaster.reward_id = "92af127c-7326-4483-a52b-b0da0be61c01"
    database.session.commit()

    resp = post_revocation(client, "notification_failures_exceeded")

    assert resp.status_code == 200
    mock_update_eventsub.assert_not_called()
    broadcaster = database.session.get(Broadcaster, defaults.BROADCASTER_ID)
    assert broadcaster.eventsub_id == defaults.EVENTSUB_ID


def test_eventsub_revocation_recreate_fail(app, client, init_db, mocker, caplog):
    """Test a revocation still returns 2xx if the eventsub can't be deleted or recreated."""
    database = init_db(app)
    add_broadcaster(database)
    mock_verify_eventsub_message = mocker.patch("verifiedfirst.verify.verify_eventsub_message")
    mock_verify_eventsub_message.return_value = True
    mock_delete_eventsub = mocker.patch("verifiedfirst.twitch.delete_eventsub")
    mock_delete_eventsub.side_effect = RequestException("404 not found")
    mock_update_eventsub = mocker.patch("verifiedfirst.twitch.update_eventsub")

    for exp in (
        RequestException("403 forbidden"),
        KeyError("transport"),
        SQLAlchemyError("db down"),
    ):
        mock_update_eventsub.reset_mock()
        mock_update_eventsub.side_effect = exp
        caplog.clear()

        resp = post_revocation(client, "notification_failures_exceeded")

        assert resp.status_code == 200
        assert resp.json["eventsub_id"] == defaults.EVENTSUB_ID
        mock_update_eventsub.assert_called_once()
        assert f"could not delete revoked eventsub_id={defaults.EVENTSUB_ID}" in caplog.text
        assert (
            f"could not recreate eventsub for broadcaster_id={defaults.BROADCASTER_ID}: {exp}"
            in caplog.text
        )


def test_eventsub_revocation_malformed(app, client, init_db, mocker, caplog):
    """Test a revocation missing fields still deletes the eventsub and returns 2xx."""
    database = init_db(app)
    add_broadcaster(database)
    mock_verify_eventsub_message = mocker.patch("verifiedfirst.verify.verify_eventsub_message")
    mock_verify_eventsub_message.return_value = True
    mock_delete_eventsub = mocker.patch("verifiedfirst.twitch.delete_eventsub")
    mock_update_eventsub = mocker.patch("verifiedfirst.twitch.update_eventsub")

    for subscription in (
        {"id": defaults.EVENTSUB_ID},
        {"id": defaults.EVENTSUB_ID, "condition": {"broadcaster_user_id": "not a number"}},
        {"id": defaults.EVENTSUB_ID, "condition": {"broadcaster_user_id": defaults.BROADCASTER_ID}},
    ):
        mock_delete_eventsub.reset_mock()

        resp = post_revocation(client, None, subscription=subscription)

        assert resp.status_code == 200
        assert resp.json["eventsub_id"] == defaults.EVENTSUB_ID
        mock_delete_eventsub.assert_called_once_with(defaults.EVENTSUB_ID)
        mock_update_eventsub.assert_not_called()
    assert f"revoked eventsub_id={defaults.EVENTSUB_ID} has no broadcaster_user_id" in caplog.text
    broadcaster = database.session.get(Broadcaster, defaults.BROADCASTER_ID)
    assert broadcaster.eventsub_id == defaults.EVENTSUB_ID


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
