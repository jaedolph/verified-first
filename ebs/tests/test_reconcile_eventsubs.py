"""Tests for the reconcile_eventsubs script."""

import copy
import sys

from requests.exceptions import RequestException
from sqlalchemy.exc import SQLAlchemyError

from scripts import reconcile_eventsubs
from verifiedfirst.models.broadcasters import Broadcaster

from . import defaults

OTHER_CALLBACK_URL = "https://verifiedfirst-test.jaedolph.net/eventsub"
OTHER_REWARD_ID = "92af127c-7326-4483-a52b-b0da0be61c01"
# eventsub id stored in the database for an eventsub that no longer exists
STALE_EVENTSUB_ID = "stale-eventsub-id"


def add_broadcaster(  # pylint: disable=missing-type-doc
    database, broadcaster_id, reward_id=defaults.REWARD_ID, eventsub_id=STALE_EVENTSUB_ID
):
    """Add a broadcaster to the database.

    :param database: database to add the broadcaster to
    :param broadcaster_id: id of the broadcaster
    :param reward_id: reward id configured for the broadcaster
    :param eventsub_id: eventsub id stored for the broadcaster
    """
    database.session.add(
        Broadcaster(
            id=broadcaster_id,
            name=f"broadcaster{broadcaster_id}",
            access_token=defaults.AUTH_ACCESS_TOKEN,
            refresh_token=defaults.AUTH_REFRESH_TOKEN,
            reward_id=reward_id,
            eventsub_id=eventsub_id,
        )
    )
    database.session.commit()


def make_eventsub(  # pylint: disable=missing-type-doc
    broadcaster_id,
    status="enabled",
    reward_id=defaults.REWARD_ID,
    callback=defaults.EVENTSUB_JSON["data"][0]["transport"]["callback"],
):
    """Create an eventsub in the format returned by the twitch api.

    :param broadcaster_id: id of the broadcaster the eventsub is for
    :param status: status of the eventsub
    :param reward_id: reward id the eventsub is for
    :param callback: callback url of the eventsub
    :return: eventsub data
    """
    eventsub = copy.deepcopy(defaults.EVENTSUB_JSON["data"][0])
    eventsub["id"] = f"eventsub-{broadcaster_id}-{status}-{reward_id}-{callback}"
    eventsub["status"] = status
    eventsub["condition"]["broadcaster_user_id"] = str(broadcaster_id)
    eventsub["condition"]["reward_id"] = reward_id
    eventsub["transport"]["callback"] = callback
    return eventsub


def mock_twitch(mocker, eventsubs):  # pylint: disable=missing-type-doc
    """Mock the twitch api calls made by the reconcile script.

    :param mocker: pytest-mock fixture
    :param eventsubs: eventsubs returned when listing eventsubs
    :return: mocked update_eventsub, create_eventsub and delete_eventsub functions
    """
    mocker.patch("verifiedfirst.twitch.get_all_eventsubs").return_value = eventsubs
    mock_update_eventsub = mocker.patch("verifiedfirst.twitch.update_eventsub")
    mock_update_eventsub.return_value = defaults.EVENTSUB_ID
    mock_create_eventsub = mocker.patch("verifiedfirst.twitch.create_eventsub")
    mock_delete_eventsub = mocker.patch("verifiedfirst.twitch.delete_eventsub")
    return mock_update_eventsub, mock_create_eventsub, mock_delete_eventsub


def updated_broadcaster_ids(mock_update_eventsub):  # pylint: disable=missing-type-doc
    """Get the ids of the broadcasters update_eventsub was called for.

    :param mock_update_eventsub: mocked update_eventsub function
    :return: list of broadcaster ids
    """
    return [call.args[0].id for call in mock_update_eventsub.call_args_list]


def add_ok_broadcaster(database, broadcaster_id):  # pylint: disable=missing-type-doc
    """Add a broadcaster whose eventsub is stored in the database.

    :param database: database to add the broadcaster to
    :param broadcaster_id: id of the broadcaster
    :return: the broadcaster's eventsub
    """
    eventsub = make_eventsub(broadcaster_id)
    add_broadcaster(database, broadcaster_id, eventsub_id=eventsub["id"])
    return eventsub


def test_reconcile_eventsubs(app, init_db, mocker):
    """Test broadcasters without a working eventsub for this instance get it repaired."""
    database = init_db(app)
    ok_id, missing_id, disabled_id, wrong_reward_id, wrong_db_id = 1, 2, 3, 4, 7
    ok_eventsub = add_ok_broadcaster(database, ok_id)
    for broadcaster_id in (missing_id, disabled_id, wrong_reward_id):
        add_broadcaster(database, broadcaster_id)
    # an enabled eventsub exists, but it isn't the one stored in the database
    add_broadcaster(database, wrong_db_id)
    # broadcasters without a reward configured are ignored
    add_broadcaster(database, 5, reward_id=None)
    add_broadcaster(database, 6, reward_id="")

    eventsubs = [
        ok_eventsub,
        make_eventsub(disabled_id, status="notification_failures_exceeded"),
        make_eventsub(wrong_reward_id, reward_id=OTHER_REWARD_ID),
        make_eventsub(wrong_db_id),
    ]
    mock_update_eventsub, _, _ = mock_twitch(mocker, eventsubs)

    summary = reconcile_eventsubs.reconcile_eventsubs()

    assert updated_broadcaster_ids(mock_update_eventsub) == [
        missing_id,
        disabled_id,
        wrong_reward_id,
        wrong_db_id,
    ]
    # the eventsubs already fetched are passed through rather than fetched again
    assert [call.args[1:] for call in mock_update_eventsub.call_args_list] == [
        (defaults.REWARD_ID, []),
        (defaults.REWARD_ID, [eventsubs[1]]),
        (defaults.REWARD_ID, [eventsubs[2]]),
        (defaults.REWARD_ID, [eventsubs[3]]),
    ]
    assert summary == {"checked": 5, "ok": 1, "repaired": 4}


def test_reconcile_eventsubs_no_db_eventsub(app, init_db, mocker):
    """Test broadcasters with no eventsub stored are only repaired if they have an eventsub."""
    database = init_db(app)
    # e.g. a new eventsub was created but storing its id failed
    add_broadcaster(database, 1, eventsub_id=None)
    # e.g. the broadcaster revoked authorization, so creating an eventsub would fail
    add_broadcaster(database, 2, eventsub_id=None)

    eventsubs = [make_eventsub(1)]
    mock_update_eventsub, _, _ = mock_twitch(mocker, eventsubs)

    summary = reconcile_eventsubs.reconcile_eventsubs()

    mock_update_eventsub.assert_called_once()
    assert mock_update_eventsub.call_args.args[0].id == 1
    assert summary == {"checked": 2, "inactive": 1, "repaired": 1}


def test_reconcile_eventsubs_other_callback(app, init_db, mocker):
    """Test eventsubs for another deployment are ignored and never deleted."""
    database = init_db(app)
    add_broadcaster(database, 1)
    add_ok_broadcaster(database, 2)

    foreign_eventsubs = [
        make_eventsub(1, callback=OTHER_CALLBACK_URL),
        make_eventsub(2, callback=OTHER_CALLBACK_URL),
    ]
    mocker.patch("verifiedfirst.twitch.get_all_eventsubs").return_value = foreign_eventsubs + [
        make_eventsub(2)
    ]
    mock_create_eventsub = mocker.patch("verifiedfirst.twitch.create_eventsub")
    mock_create_eventsub.return_value = "new-eventsub-id"
    mock_delete_eventsub = mocker.patch("verifiedfirst.twitch.delete_eventsub")

    summary = reconcile_eventsubs.reconcile_eventsubs()

    mock_create_eventsub.assert_called_once()
    assert mock_create_eventsub.call_args.args[0].id == 1
    mock_delete_eventsub.assert_not_called()
    assert database.session.get(Broadcaster, 1).eventsub_id == "new-eventsub-id"
    assert summary == {"checked": 2, "ok": 1, "repaired": 1}


def test_reconcile_eventsubs_dry_run(app, init_db, mocker):
    """Test a dry run reports what would change without changing anything."""
    database = init_db(app)
    ok_eventsub = add_ok_broadcaster(database, 1)
    add_broadcaster(database, 2)

    mock_update_eventsub, mock_create_eventsub, mock_delete_eventsub = mock_twitch(
        mocker, [ok_eventsub, make_eventsub(2, status="notification_failures_exceeded")]
    )

    summary = reconcile_eventsubs.reconcile_eventsubs(dry_run=True)

    mock_update_eventsub.assert_not_called()
    mock_create_eventsub.assert_not_called()
    mock_delete_eventsub.assert_not_called()
    assert summary == {"checked": 2, "ok": 1, "repaired": 1}


def test_reconcile_eventsubs_failure(app, init_db, mocker, caplog):
    """Test failures to repair an eventsub are logged and the next broadcaster is still checked,
    with broadcasters that haven't authorized the extension counted separately."""
    database = init_db(app)
    for broadcaster_id in (1, 2, 3, 4):
        add_broadcaster(database, broadcaster_id)

    forbidden = mocker.Mock()
    forbidden.status_code = 403
    mock_update_eventsub, _, _ = mock_twitch(mocker, [])
    mock_update_eventsub.side_effect = [
        RequestException("500 server error"),
        RequestException("403 forbidden", response=forbidden),
        SQLAlchemyError("db down"),
        defaults.EVENTSUB_ID,
    ]

    summary = reconcile_eventsubs.reconcile_eventsubs()

    assert updated_broadcaster_ids(mock_update_eventsub) == [1, 2, 3, 4]
    assert summary == {"checked": 4, "repaired": 1, "unauthorized": 1, "failed": 2}
    assert "could not repair eventsub for broadcaster_id=1: 500 server error" in caplog.text
    assert (
        "broadcaster_id=2 hasn't authorized the extension, "
        f"clearing eventsub_id={STALE_EVENTSUB_ID}"
    ) in caplog.text
    assert "could not repair eventsub for broadcaster_id=3: db down" in caplog.text
    # only the unauthorized broadcaster's eventsub id is cleared
    assert database.session.get(Broadcaster, 1).eventsub_id == STALE_EVENTSUB_ID
    assert database.session.get(Broadcaster, 2).eventsub_id is None
    assert database.session.get(Broadcaster, 3).eventsub_id == STALE_EVENTSUB_ID

    # the unauthorized broadcaster is skipped on later runs
    mock_update_eventsub.reset_mock()
    mock_update_eventsub.side_effect = None

    summary = reconcile_eventsubs.reconcile_eventsubs()

    # update_eventsub is mocked, so broadcaster 4 is repaired again as nothing was stored for it
    assert updated_broadcaster_ids(mock_update_eventsub) == [1, 3, 4]
    assert summary == {"checked": 4, "inactive": 1, "repaired": 3}


def test_reconcile_eventsubs_pagination(app, init_db, mocker):
    """Test eventsubs on every page of the twitch api response are taken into account."""
    database = init_db(app)
    first_eventsub = add_ok_broadcaster(database, 1)
    second_eventsub = add_ok_broadcaster(database, 2)

    first_page = mocker.Mock()
    first_page.json.return_value = {
        "data": [first_eventsub],
        "pagination": {"cursor": "page2cursor"},
    }
    second_page = mocker.Mock()
    second_page.json.return_value = {"data": [second_eventsub], "pagination": {}}
    mock_request_twitch_api = mocker.patch("verifiedfirst.twitch.request_twitch_api_app")
    mock_request_twitch_api.side_effect = [first_page, second_page]
    mock_update_eventsub = mocker.patch("verifiedfirst.twitch.update_eventsub")

    summary = reconcile_eventsubs.reconcile_eventsubs()

    assert mock_request_twitch_api.call_count == 2
    mock_update_eventsub.assert_not_called()
    assert summary == {"checked": 2, "ok": 2}


def test_main(app, init_db, mocker, capsys):
    """Test the script entry point prints a summary."""
    database = init_db(app)
    ok_eventsub = add_ok_broadcaster(database, 1)
    add_broadcaster(database, 2)
    mocker.patch("scripts.reconcile_eventsubs.create_app").return_value = app
    mock_update_eventsub, _, _ = mock_twitch(mocker, [ok_eventsub])

    mocker.patch.object(sys, "argv", ["reconcile_eventsubs", "--dry-run"])
    reconcile_eventsubs.main()

    mock_update_eventsub.assert_not_called()
    assert capsys.readouterr().out == (
        "checked: 2, ok: 1, inactive: 0, would repair: 1, unauthorized: 0, failed: 0\n"
    )

    mocker.patch.object(sys, "argv", ["reconcile_eventsubs"])
    reconcile_eventsubs.main()

    assert updated_broadcaster_ids(mock_update_eventsub) == [2]
    assert capsys.readouterr().out == (
        "checked: 2, ok: 1, inactive: 0, repaired: 1, unauthorized: 0, failed: 0\n"
    )
