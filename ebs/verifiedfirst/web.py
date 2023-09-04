import logging
from functools import wraps

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from verifiedfirst import twitch, verify
from verifiedfirst.config import Config

app = Flask(__name__)
CORS(app)
app.config.from_object(Config)

logging.basicConfig(
    filename="record.log",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s",
)


def token_required(func):
    @wraps(func)
    def decorated_function():
        token = verify.verify_jwt(request)
        if not token:
            return jsonify({"error": "could not verify auth token"}), 403

        try:
            channel_id = token["channel_id"]
            role = token["role"]
        except KeyError as exp:
            error_msg = f"could not parse user attributes from jwt, {exp}"
            app.logger.error(error_msg)
            return jsonify({}), 400
        app.logger.debug("authenticated request for channel_id=%s role=%s", channel_id, role)
        return func(channel_id, role)

    return decorated_function


@app.route("/firsts", methods=["GET"])
@token_required
def firsts(channel_id, _):

    firsts_dict = twitch.get_firsts(channel_id)
    if not firsts_dict:
        return {}, 404

    resp = jsonify(firsts_dict)

    return resp


@app.route("/eventsub/create", methods=["POST"])
@token_required
def eventsub_create(channel_id, role):
    if role != "broadcaster":
        return jsonify({"error": "user role is not broadcaster"}), 403

    reward_id = request.args["reward_id"]

    # check broadcaster exists in database
    if twitch.get_broadcaster(channel_id) is None:
        return jsonify({"error": "broadcaster is not authed yet"}), 404

    reward_id = twitch.update_reward(channel_id, reward_id)

    eventsub_id = twitch.update_eventsub(channel_id, reward_id)

    return jsonify({"eventsub_id": eventsub_id})


@app.route("/rewards", methods=["GET"])
@token_required
def rewards(channel_id, role):
    if role != "broadcaster":
        return jsonify({"error": "user role is not broadcaster"}), 403

    rewards_dict = twitch.get_rewards(channel_id)

    return jsonify(rewards_dict)


@app.route("/auth", methods=["GET"])
def auth():
    app.logger.debug(request.headers)

    if "error" in request.args:
        return render_template("auth.html", auth_msg="AUTH_FAILED")
    try:
        code = request.args["code"]
        access_token, refresh_token = twitch.get_auth_tokens(code)
        twitch.update_broadcaster_details(access_token, refresh_token)
        auth_msg = "AUTH_SUCCESSFUL"
    except Exception as exp:
        app.logger.error("auth failed: %s", exp)
        auth_msg = "AUTH_FAILED"

    return render_template("auth.html", auth_msg=auth_msg)


@app.route("/eventsub", methods=["POST"])
def eventsub():
    request_data = request.get_json()

    message_type = request.headers["Twitch-Eventsub-Message-Type"]

    app.logger.debug("eventsub_headers=%s", request.headers)
    app.logger.debug("eventsub_data=%s", request_data)

    if not verify.verify_eventsub_message(request):
        return "failed to verify hmac", 403

    app.logger.info("hmac verified")

    if message_type == "webhook_callback_verification":
        challenge = request_data["challenge"]
        app.logger.info("responding to challenge: %s", challenge)
        return challenge

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

    return jsonify(first)
