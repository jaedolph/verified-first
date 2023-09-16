"""web.py."""
from functools import wraps
from typing import Callable, TypeVar, cast

from flask import Response, abort, jsonify, make_response, render_template, request
from werkzeug.exceptions import BadRequest, Forbidden, NotFound, Unauthorized

from verifiedfirst import twitch, verify
from verifiedfirst.app_init import app

R = TypeVar("R")


def token_required(func: Callable[[int, str], R]) -> Callable[[int, str], R]:
    """Decorator to validate JWT and get the associated channel_id and role.

    :param func: function to decorate
    :return: decorated function
    """

    @wraps(func)
    def decorated_function() -> R:
        try:
            channel_id, role = verify.verify_jwt(request)
        except PermissionError as exp:
            error_msg = f"authentication failed: {exp}"
            app.logger.debug(error_msg)
            return abort(401, error_msg)

        app.logger.debug("authenticated request for channel_id=%s role=%s", channel_id, role)
        return func(channel_id, role)

    return cast(Callable[[int, str], R], decorated_function)


@app.errorhandler(400)
def bad_request(exception: BadRequest) -> Response:
    """400 error response (bad request).

    :param exception: the exception that was raised
    :return: json formatted response
    """
    return make_response(jsonify({"error": exception.description}), 400)


@app.errorhandler(401)
def authorization_error(exception: Unauthorized) -> Response:
    """401 error response (unauthorized).

    :param exception: the exception that was raised
    :return: json formatted response
    """
    return make_response(jsonify({"error": exception.description}), 401)


@app.errorhandler(403)
def forbidden(exception: Forbidden) -> Response:
    """403 error response (forbidden).

    :param exception: the exception that was raised
    :return: json formatted response
    """
    return make_response(jsonify({"error": exception.description}), 403)


@app.errorhandler(404)
def not_found(exception: NotFound) -> Response:
    """404 error response (not found).

    :param exception: the exception that was raised
    :return: json formatted response
    """
    return make_response(jsonify({"error": exception.description}), 404)


@app.route("/firsts", methods=["GET"])
@token_required
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

    firsts_dict = twitch.get_firsts(broadcaster)
    if not firsts_dict:
        abort(404, "could not get firsts")

    resp = make_response(jsonify(firsts_dict))

    return resp


@app.route("/eventsub/create", methods=["POST"])
@token_required
def eventsub_create(channel_id: int, role: str) -> Response:
    """Create an eventsub to listen for channel point redemption events.

    :param channel_id: id of the channel the extension is running on.
    :param role: role of the user making the request
    :return: the eventsub id in json format
    """
    app.logger.debug("method: %s", request.method)
    app.logger.debug("args: %s", request.args)

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


@app.route("/rewards", methods=["GET"])
@token_required
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

    rewards_dict = twitch.get_rewards(broadcaster)

    return make_response(jsonify(rewards_dict))


@app.route("/auth", methods=["GET"])
def auth() -> Response:
    """Endpoint to redirect twitch oauth requests to. Ensures that api auth tokens are stored in the
    database under the appropriate broadcaster.

    :return: javascript that sends a message to the parent window (AUTH_SUCCESSFUL or AUTH_FAILED)
    """
    app.logger.debug(request.headers)

    if "error" in request.args:
        return make_response(render_template("auth.html", auth_msg="AUTH_FAILED"))
    try:
        code = request.args["code"]
        access_token, refresh_token = twitch.get_auth_tokens(code)
        twitch.update_broadcaster_details(access_token, refresh_token)
        auth_msg = "AUTH_SUCCESSFUL"
    except Exception as exp:  # pylint: disable=broad-exception-caught
        app.logger.error("auth failed: %s", exp)
        auth_msg = "AUTH_FAILED"

    return make_response(render_template("auth.html", auth_msg=auth_msg))


@app.route("/eventsub", methods=["POST"])
def eventsub() -> Response:
    """Endpoint for receiving eventsub requests from the twitch api.

    :return: the "first" event that was added to the database in json format
    """
    request_data = request.get_json()

    message_type = request.headers["Twitch-Eventsub-Message-Type"]

    app.logger.debug("eventsub_headers=%s", request.headers)
    app.logger.debug("eventsub_data=%s", request_data)

    if not verify.verify_eventsub_message(request):
        abort(401, "could not verify hmac in eventsub message")

    app.logger.info("hmac verified")

    if message_type == "webhook_callback_verification":
        challenge = request_data["challenge"]
        app.logger.info("responding to challenge: %s", challenge)
        return make_response(challenge)

    if message_type == "notification":
        broadcaster_id = request_data["event"]["broadcaster_user_id"]
        user_id = request_data["event"]["user_id"]
        user_name = request_data["event"]["user_login"]
        reward_id = request_data["event"]["reward"]["id"]

        app.logger.info(
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
        app.logger.info(
            "revoking eventsub for broadcaster_id=%s eventsub_id=%s", broadcaster_id, eventsub_id
        )
        twitch.delete_eventsub(eventsub_id)
        return make_response(jsonify({"eventsub_id": eventsub_id}))

    abort(401, "could not process eventsub")
