"""Main routes."""

from datetime import datetime
from functools import partial
from typing import Any

from flask import Blueprint, Flask, Response, abort, jsonify, make_response, request, current_app
from markupsafe import escape
from requests import RequestException
from sqlalchemy.exc import SQLAlchemyError

from verifiedfirst import twitch, verify
from verifiedfirst.database import db
from verifiedfirst.models.broadcasters import Broadcaster

bp = Blueprint("main", __name__)

# eventsub revocation reasons where creating a new eventsub is expected to work. version_removed
# isn't one, as create_eventsub always creates the version twitch has just removed.
RECOVERABLE_REVOCATION_REASONS = ("notification_failures_exceeded",)


@bp.route("/firsts", methods=["GET"])
@verify.token_required
def firsts(channel_id: int, role: str) -> Response:
    """Get total count of "firsts" for each user.

    :param channel_id: id of the channel the extension is running on.
    :param role: role of the user making the request
    :return: first counts by user in json format e.g {"user1": 5, "user2": 3}
    """
    del role
    # check broadcaster exists in database
    broadcaster = twitch.get_broadcaster(channel_id)
    if broadcaster is None:
        abort(403, "broadcaster is not authed yet")

    end_time = None
    start_time = None
    if "end_time" in request.args:
        end_time = datetime.fromisoformat(request.args["end_time"])

    if "start_time" in request.args:
        start_time = datetime.fromisoformat(request.args["start_time"])

    firsts_dict = twitch.get_firsts(broadcaster, end_time=end_time, start_time=start_time)
    if not firsts_dict:
        abort(404, "could not get firsts")

    resp = make_response(jsonify(firsts_dict))

    return resp


@bp.route("/avatars", methods=["GET"])
@verify.token_required
def avatars(channel_id: int, role: str) -> Response:
    """Get the profile image url of each user that has a "first" on the channel.

    :param channel_id: id of the channel the extension is running on.
    :param role: role of the user making the request
    :return: profile image urls by user in json format e.g {"user1": "https://..."}
    """
    del role
    # check broadcaster exists in database
    broadcaster = twitch.get_broadcaster(channel_id)
    if broadcaster is None:
        abort(403, "broadcaster is not authed yet")

    avatars_dict = twitch.get_avatars(broadcaster)

    return make_response(jsonify(avatars_dict))


@bp.route("/eventsub/create", methods=["POST"])
@verify.token_required
def eventsub_create(channel_id: int, role: str) -> Response:
    """Create an eventsub to listen for channel point redemption events.

    :param channel_id: id of the channel the extension is running on.
    :param role: role of the user making the request
    :return: the eventsub id in json format
    """
    current_app.logger.debug("method: %s", request.method)
    current_app.logger.debug("args: %s", request.args)

    if role != "broadcaster":
        abort(403, "user role is not broadcaster")

    reward_id = request.args.get("reward_id")

    if reward_id is None:
        abort(400, "reward_id is required")

    if reward_id == "undefined":
        abort(400, "reward id is undefined")

    # check broadcaster exists in database
    broadcaster = twitch.get_broadcaster(channel_id)
    if broadcaster is None:
        abort(403, "broadcaster is not authed yet")

    # only store the reward once the eventsub exists, so /rewards never reports a reward this
    # instance isn't listening for. if this fails the stored reward is unchanged, and
    # reconcile_eventsubs recreates the eventsub for it if the old one was already deleted
    eventsub_id = twitch.update_eventsub(broadcaster, reward_id)

    twitch.update_reward(broadcaster, reward_id)

    return make_response(jsonify({"eventsub_id": eventsub_id}))


@bp.route("/rewards", methods=["GET"])
@verify.token_required
def rewards(channel_id: int, role: str) -> Response:
    """Get list of rewards for the current broadcaster/channel.

    :param channel_id: id of the channel the extension is running on
    :param role: role of the user making the request
    :return: list of rewards in json format
    """
    if role != "broadcaster":
        abort(403, "user role is not broadcaster")

    # check broadcaster exists in database
    broadcaster = twitch.get_broadcaster(channel_id)
    if broadcaster is None:
        abort(403, "broadcaster is not authed yet")
    try:
        rewards_dict = twitch.get_rewards(broadcaster)
    except RequestException:
        abort(500, "failed to get rewards for broadcaster")

    # mark the reward this instance is listening for. the twitch extension config is shared
    # between the released and testing versions of the extension, so it can't be trusted for this
    for reward in rewards_dict:
        reward["configured"] = reward.get("id") == broadcaster.reward_id

    return make_response(jsonify(rewards_dict))


@bp.route("/eventsub", methods=["POST"])
def eventsub() -> Response:
    """Endpoint for receiving eventsub requests from the twitch api.

    :return: the "first" event that was added to the database in json format
    """
    request_data = request.get_json()

    message_type = request.headers["Twitch-Eventsub-Message-Type"]

    current_app.logger.debug("eventsub_headers=%s", request.headers)
    current_app.logger.debug("eventsub_data=%s", request_data)

    if not verify.verify_eventsub_message(request):
        abort(401, "could not verify hmac in eventsub message")

    current_app.logger.info("hmac verified")

    if message_type == "webhook_callback_verification":
        challenge = request_data["challenge"]
        current_app.logger.info("responding to challenge: %s", challenge)
        return make_response(escape(challenge), 200, {"Content-Type": "text/plain"})

    if message_type == "notification":
        broadcaster_id = int(request_data["event"]["broadcaster_user_id"])
        user_id = int(request_data["event"]["user_id"])
        user_name = request_data["event"]["user_login"]
        reward_id = request_data["event"]["reward"]["id"]
        # the redemption id is the same across every delivery of a redemption, unlike the message
        # id which differs between eventsubs
        redemption_id = request_data["event"]["id"]

        current_app.logger.info(
            "adding first for broadcaster_id=%s user_id=%s user_name=%s reward_id=%s "
            "redemption_id=%s",
            broadcaster_id,
            user_id,
            user_name,
            reward_id,
            redemption_id,
        )
        # TODO: check reward id is correct
        first = twitch.add_first(broadcaster_id, user_id, user_name, redemption_id)

        return make_response(jsonify(first))

    if message_type == "revocation":
        subscription = request_data["subscription"]
        response = make_response(jsonify({"eventsub_id": subscription["id"]}))
        if handle_revocation(subscription):
            # recreating takes several twitch api calls, so do it after the response is sent to
            # avoid twitch timing out waiting for a response to the revocation message
            app = current_app._get_current_object()  # pylint: disable=protected-access
            response.call_on_close(partial(recreate_eventsub, app, subscription))
        return response

    abort(401, "could not process eventsub")


def handle_revocation(subscription: dict[str, Any]) -> bool:
    """Clean up after twitch revokes an eventsub, and work out if it should be recreated.

    Errors are logged rather than raised, as twitch still needs a 2xx response to the revocation
    message.

    :param subscription: the revoked subscription from the eventsub revocation message
    :return: True if the eventsub should be recreated with recreate_eventsub
    """
    eventsub_id = subscription["id"]
    try:
        twitch.delete_eventsub(eventsub_id)
    except RequestException as exp:
        current_app.logger.warning("could not delete revoked eventsub_id=%s: %s", eventsub_id, exp)

    reason = subscription.get("status")
    condition = subscription.get("condition") or {}
    reward_id = condition.get("reward_id")
    current_app.logger.warning(
        "eventsub revoked for broadcaster_id=%s eventsub_id=%s reward_id=%s reason=%s",
        condition.get("broadcaster_user_id"),
        eventsub_id,
        reward_id,
        reason,
    )

    broadcaster = get_revoked_broadcaster(subscription)
    if broadcaster is None:
        return False

    if reason in RECOVERABLE_REVOCATION_REASONS:
        return True

    # e.g. authorization_revoked or user_removed, recreating the eventsub would fail
    current_app.logger.warning(
        "not recreating eventsub for broadcaster_id=%s reason=%s", broadcaster.id, reason
    )
    broadcaster.eventsub_id = None
    try:
        db.session.commit()
    except SQLAlchemyError as exp:
        current_app.logger.error(
            "could not clear eventsub_id for broadcaster_id=%s: %s", broadcaster.id, exp
        )
        db.session.rollback()
    return False


def get_revoked_broadcaster(subscription: dict[str, Any]) -> Broadcaster | None:
    """Get the broadcaster a revoked eventsub belongs to, if it is their current eventsub.

    Revocations of stale eventsubs (or ones created by another deployment sharing the client id)
    shouldn't change anything.

    :param subscription: the revoked subscription from the eventsub revocation message
    :return: the broadcaster, or None if the eventsub isn't the current one for any broadcaster
    """
    eventsub_id = subscription["id"]
    condition = subscription.get("condition") or {}
    try:
        broadcaster_id = int(condition["broadcaster_user_id"])
    except (KeyError, TypeError, ValueError):
        current_app.logger.error("revoked eventsub_id=%s has no broadcaster_user_id", eventsub_id)
        return None

    broadcaster = twitch.get_broadcaster(broadcaster_id)
    if (
        broadcaster is None
        or eventsub_id != broadcaster.eventsub_id
        or condition.get("reward_id") != broadcaster.reward_id
    ):
        current_app.logger.info(
            "revoked eventsub_id=%s is not the current eventsub for broadcaster_id=%s",
            eventsub_id,
            broadcaster_id,
        )
        return None
    return broadcaster


def recreate_eventsub(app: Flask, subscription: dict[str, Any]) -> None:
    """Recreate a revoked eventsub.

    This runs after the response to the revocation message has been sent, so it needs its own app
    context.

    :param app: the flask app
    :param subscription: the revoked subscription from the eventsub revocation message
    """
    with app.app_context():
        # check again in case the broadcaster changed their config in the meantime
        broadcaster = get_revoked_broadcaster(subscription)
        if broadcaster is None:
            return

        current_app.logger.info("recreating eventsub for broadcaster_id=%s", broadcaster.id)
        try:
            new_eventsub_id = twitch.update_eventsub(broadcaster, broadcaster.reward_id)
        except (RequestException, KeyError, TypeError, SQLAlchemyError) as exp:
            current_app.logger.error(
                "could not recreate eventsub for broadcaster_id=%s: %s", broadcaster.id, exp
            )
            db.session.rollback()
            return
        current_app.logger.info(
            "recreated eventsub for broadcaster_id=%s eventsub_id=%s",
            broadcaster.id,
            new_eventsub_id,
        )
