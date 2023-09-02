import logging
import os
from verifiedfirst.extensions import db
from verifiedfirst.config import Config
from verifiedfirst.models.broadcasters import Broadcaster
from verifiedfirst.models.firsts import First
from verifiedfirst import twitch, verify
from flask_cors import CORS
from functools import wraps

from flask import Flask, jsonify, request, Response, render_template

app = Flask(__name__)
CORS(app)
app.config.from_object(Config)
db.init_app(app)

logging.basicConfig(
    filename="record.log",
    level=logging.DEBUG,
    format=f"%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s",
)


def token_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        token = verify.verify_jwt(request)
        if not token:
            return jsonify({"error": "could not verify auth token"}), 403

        try:
            channel_id = token["channel_id"]
            role = token["role"]
        except KeyError as exp:
            return jsonify({"error": "could not parse user attributes from jwt"}), 400
        app.logger.debug(f"authenticated request for channel_id={channel_id} role={role}")
        return func(channel_id, role)

    return decorated_function


@app.route("/firsts", methods=["GET"])
@token_required
def firsts(channel_id, role):
    firsts = twitch.get_firsts(channel_id)
    if not firsts:
        return {}, 404

    resp = jsonify(firsts)

    return resp


@app.route("/eventsub/create", methods=["POST"])
@token_required
def eventsub_create(channel_id, role):
    if role != "broadcaster":
        return jsonify({"error": "user role is not broadcaster"}), 403

    reward_id = request.args["reward_id"]

    broadcaster = Broadcaster.query.filter(Broadcaster.id == channel_id).one()

    if broadcaster is None:
        return jsonify({"error": "broadcaster is not authed yet"}), 404

    reward_id = twitch.update_reward(broadcaster.id, reward_id)

    eventsub_id = twitch.update_eventsub(channel_id, reward_id)

    return jsonify({"eventsub_id": eventsub_id})


@app.route("/rewards", methods=["GET"])
@token_required
def rewards(channel_id, role):
    if role != "broadcaster":
        return jsonify({"error": "user role is not broadcaster"}), 403

    broadcaster = Broadcaster.query.filter(Broadcaster.id == channel_id).one()
    rewards = twitch.get_rewards(broadcaster.access_token, broadcaster.id)

    return jsonify(rewards)


@app.route("/auth", methods=["GET"])
def auth():
    app.logger.debug(request.headers)

    auth_msg = "AUTH_FAILED"

    if "error" in request.args:
        return render_template("auth.html", auth_msg=auth_msg)

    try:
        code = request.args["code"]
        access_token, refresh_token = twitch.get_auth_tokens(code)
        twitch.update_broadcaster_details(access_token, refresh_token)
        auth_msg = "AUTH_SUCCESSFUL"
    except Exception as exp:
        app.logger.error(f"Auth failed: {exp}")

    return render_template("auth.html", auth_msg=auth_msg)


@app.route("/eventsub", methods=["POST"])
def eventsub():
    request_data = request.get_json()

    message_type = request.headers["Twitch-Eventsub-Message-Type"]

    app.logger.info(f"{request.headers}")
    app.logger.info(f"{request_data}")

    if not verify.verify_eventsub_message(request):
        return "failed to verify hmac", 403

    app.logger.info(f"hmac verified")

    if message_type == "webhook_callback_verification":
        challenge = request_data["challenge"]
        app.logger.info(f"responding to challenge {challenge}")
        return challenge

    if message_type == "notification":
        broadcaster_id = request_data["event"]["broadcaster_user_id"]
        user_id = request_data["event"]["user_id"]
        user_name = request_data["event"]["user_login"]
        reward_id = request_data["event"]["reward"]["id"]

        app.logger.info(
            f"Adding first for broadcaster_id={broadcaster_id} user_id={user_id} user_name={user_name} reward_id={reward_id}"
        )
        # TODO: check reward id is correct, check for duplicate message ids
        first = twitch.add_first(broadcaster_id, user_name)

    return jsonify(first)
