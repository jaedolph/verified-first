"""Sets the default config for every channel that has configured the extension. This script was
required due to the default value of the title not working correctly in v0.2.
"""
import base64
import json
import time

import jwt
import requests
from flask import current_app

from verifiedfirst import create_app
from verifiedfirst.models.broadcasters import Broadcaster

VERSION = "1"


def get_jwt_headers(broadcaster):
    jwt_payload = {
        "exp": int(time.time() + 10),
        "user_id": str(broadcaster.id),
        "role": "broadcaster",
    }

    jwt_token = jwt.encode(
        payload=jwt_payload,
        key=base64.b64decode(current_app.config["EXTENSION_SECRET"]),
    )

    headers = {
        "Authorization": "Bearer " + jwt_token,
        "Client-Id": current_app.config["CLIENT_ID"],
    }
    return headers


def get_config(broadcaster):
    headers = get_jwt_headers(broadcaster)
    resp = requests.get(
        "https://api.twitch.tv/helix/extensions/configurations",
        params={
            "extension_id": current_app.config["CLIENT_ID"],
            "broadcaster_id": str(broadcaster.id),
            "segment": "broadcaster",
            "version": VERSION,
        },
        timeout=5,
        headers=headers,
    )

    resp.raise_for_status()

    try:
        current_config = json.loads(resp.json()["data"][0]["content"])
    except Exception:
        current_config = None

    return current_config


def update_config(broadcaster):
    headers = get_jwt_headers(broadcaster)
    config = {
        "title": "Verified First Chatters",
        "timeRange": "all_time",
    }

    if broadcaster.reward_id:
        config["rewardId"] = broadcaster.reward_id

    data = {
        "extension_id": current_app.config["CLIENT_ID"],
        "segment": "broadcaster",
        "version": VERSION,
        "content": json.dumps(config),
    }

    print(f"setting config for {broadcaster.name} to: {data}")

    resp = requests.put(
        "https://api.twitch.tv/helix/extensions/configurations",
        params={
            "extension_id": current_app.config["CLIENT_ID"],
            "broadcaster_id": str(broadcaster.id),
            "segment": "broadcaster",
            "version": VERSION,
        },
        timeout=5,
        headers=headers,
        json=data,
    )
    resp.raise_for_status()


def main():
    with create_app().app_context():
        broadcasters = Broadcaster.query.filter(Broadcaster.reward_id != "").all()

        for broadcaster in broadcasters:
            config = get_config(broadcaster)
            print(f"current config for {broadcaster.name}: {config}")
            if config is None:
                print(f"updating config for {broadcaster.name}")
                update_config(broadcaster)
            else:
                print(f"skipping config update for {broadcaster.name}, already configured")


if __name__ == "__main__":
    main()
