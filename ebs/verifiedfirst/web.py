import logging
import os
from verifiedfirst.extensions import db
from verifiedfirst.config import Config
from verifiedfirst.models.broadcasters import Broadcaster
from verifiedfirst.models.firsts import First
from verifiedfirst import twitch

from flask import Flask, jsonify, request, Response

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

logging.basicConfig(
    filename="record.log",
    level=logging.DEBUG,
    format=f"%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s",
)

# @app.route("/broadcasters", methods=["GET"])
# def broadcasters():
#     broadcasters = Broadcaster.query.all()
#     return jsonify(broadcasters)


@app.route("/firsts", methods=["GET"])
def firsts():
    broadcaster_id = int(request.args["broadcaster_id"])

    resp = jsonify(twitch.get_firsts(broadcaster_id))
    resp.headers["Access-Control-Allow-Origin"] = "*"

    return resp


@app.route("/eventsub/create", methods=["GET"])
def eventsub_create():
    broadcaster_id = int(request.args["broadcaster_id"])
    broadcaster = Broadcaster.query.filter(Broadcaster.id == broadcaster_id).one()

    reward_id = twitch.update_reward(broadcaster.access_token, broadcaster.id, "First")

    eventsub_id = twitch.update_eventsub(broadcaster_id, reward_id)

    return jsonify({"eventsub_id": eventsub_id})


@app.route("/rewards", methods=["GET"])
def rewards():
    broadcaster_id = int(request.args["broadcaster_id"])

    broadcaster = Broadcaster.query.filter(Broadcaster.id == broadcaster_id).one()
    rewards = twitch.get_rewards(broadcaster.access_token, broadcaster.id)
    return jsonify(rewards)


@app.route("/auth", methods=["GET"])
def auth():
    code = request.args["code"]
    access_token, refresh_token = twitch.get_auth_tokens(code)
    broadcaster_name, _ = twitch.update_broadcaster_details(access_token, refresh_token)

    return f"Auth updated for {broadcaster_name}"


@app.route("/eventsub", methods=["POST"])
def eventsub():
    request_data = request.get_json()

    message_type = request.headers["Twitch-Eventsub-Message-Type"]

    app.logger.info(f"{request.headers}")
    app.logger.info(f"{request_data}")

    if not twitch.verify_eventsub_message(request):
        return "failed to verify hmac", 403

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


# @app.route('/auth', methods =['GET'])
# def auth():
#     code = request.args["code"]
#     access_token, refresh_token = get_auth_tokens(code)
#     broadcaster_name, broadcaster_id = update_broadcaster_details(access_token, refresh_token)

#     reward_id = update_reward(access_token, broadcaster_id, "first-testing")
#     update_eventsub(access_token, broadcaster_id, reward_id)

#     return "OK"

# @app.route('/broadcasters', methods =['GET'])
# def broadcasters():
#     conn = get_db_connection()
#     conn.row_factory = sqlite3.Row
#     broadcasters = conn.execute('SELECT * FROM broadcasters').fetchall()
#     conn.close()

#     broadcasters_list = []

#     for broadcaster in broadcasters:
#         app.logger.info("broadcaster")
#         broadcasters_list.append({
#             "name": broadcaster["broadcaster_name"],
#             "id": broadcaster["broadcaster_id"],
#             "reward_id": broadcaster["reward_id"],
#             "reward_name": broadcaster["reward_name"],
#         })

#     return jsonify(broadcasters_list)


# @app.route('/firsts', methods =['GET'])
# def firsts():

#     broadcaster_id = int(request.args["broadcaster_id"])

#     resp = jsonify(get_firsts(broadcaster_id))
#     resp.headers['Access-Control-Allow-Origin'] = '*'
#     return resp

# @app.route('/eventsub', methods =['POST'])
# def eventsub():
#     request_data = request.get_json()

#     message_type = request.headers["Twitch-Eventsub-Message-Type"]

#     app.logger.info(f"{request.headers}")
#     app.logger.info(f"{request_data}")

#     if not verify_eventsub_message(request):
#         return "failed to verify hmac", 403

#     if message_type == "webhook_callback_verification":
#         challenge = request_data["challenge"]
#         app.logger.info(f"responding to challenge {challenge}")
#         return challenge

#     if message_type == "notification":
#         broadcaster_id = request_data["event"]["broadcaster_user_id"]
#         user_id = request_data["event"]["user_id"]
#         user_name = request_data["event"]["user_login"]
#         reward_id = request_data["event"]["reward"]["id"]

#         app.logger.info(f"Adding first for broadcaster_id={broadcaster_id} user_id={user_id} user_name={user_name} reward_id={reward_id}")
#         # TODO: check reward id is correct, check for duplicate message ids
#         first = add_first(broadcaster_id, user_id, user_name)

#     return jsonify({"test": "test"})
