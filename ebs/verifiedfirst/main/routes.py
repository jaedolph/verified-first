"""Main routes."""
from datetime import datetime

from flask import Blueprint, Response, abort, jsonify, make_response, request, current_app
from markupsafe import escape
from requests import RequestException

from verifiedfirst import twitch, verify

bp = Blueprint("main", __name__)


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

    reward_id = request.args["reward_id"]

    if reward_id == "undefined":
        abort(400, "reward id is undefined")

    # check broadcaster exists in database
    broadcaster = twitch.get_broadcaster(channel_id)
    if broadcaster is None:
        abort(403, "broadcaster is not authed yet")

    reward_id = twitch.update_reward(broadcaster, reward_id)

    eventsub_id = twitch.update_eventsub(broadcaster, reward_id)

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

        current_app.logger.info(
            "adding first for broadcaster_id=%s user_id=%s user_name=%s reward_id=%s",
            broadcaster_id,
            user_id,
            user_name,
            reward_id,
        )
        # TODO: check reward id is correct, check for duplicate message ids
        first = twitch.add_first(broadcaster_id, user_name)

        return make_response(jsonify(first))

    if message_type == "revocation":
        eventsub_id = request_data["subscription"]["id"]
        broadcaster_id = request_data["subscription"]["condition"]["broadcaster_user_id"]
        current_app.logger.info(
            "revoking eventsub for broadcaster_id=%s eventsub_id=%s", broadcaster_id, eventsub_id
        )
        twitch.delete_eventsub(eventsub_id)
        return make_response(jsonify({"eventsub_id": eventsub_id}))

    abort(401, "could not process eventsub")
