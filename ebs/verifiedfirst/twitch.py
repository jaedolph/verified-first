import requests

from verifiedfirst.extensions import db
from verifiedfirst.config import Config
from verifiedfirst.models.broadcasters import Broadcaster
from verifiedfirst.models.firsts import First
from collections import defaultdict
import logging

LOG = logging.getLogger()


def get_auth_tokens(code):
    req = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": Config.CLIENT_ID,
            "client_secret": Config.CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": Config.REDIRECT_URI,
        },
    )
    auth = req.json()

    LOG.debug(f"auth: {auth}")
    req.raise_for_status()

    access_token = auth["access_token"]
    refresh_token = auth["refresh_token"]

    return access_token, refresh_token


def get_broadcaster(token):
    req = requests.get(
        f"{Config.TWITCH_API_BASEURL}/users",
        headers={"Authorization": f"Bearer {token}", "Client-ID": Config.CLIENT_ID},
        timeout=Config.REQUEST_TIMEOUT,
    )

    user = req.json()["data"][0]

    broadcaster_name = user["login"]
    broadcaster_id = user["id"]

    return broadcaster_name, broadcaster_id


def update_broadcaster_details(access_token, refresh_token):
    broadcaster_name, broadcaster_id = get_broadcaster(access_token)

    db.session.merge(
        Broadcaster(
            id=broadcaster_id,
            name=broadcaster_name,
            access_token=access_token,
            refresh_token=refresh_token,
        )
    )
    db.session.commit()

    return broadcaster_name, broadcaster_id


def get_rewards(access_token, broadcaster_id):
    req = requests.get(
        f"{Config.TWITCH_API_BASEURL}/channel_points/custom_rewards",
        headers={"Authorization": f"Bearer {access_token}", "Client-ID": Config.CLIENT_ID},
        params={
            "broadcaster_id": broadcaster_id,
            "only_manageable_rewards": "False",
        },
        timeout=Config.REQUEST_TIMEOUT,
    )
    req.raise_for_status()

    try:
        rewards = req.json()["data"]
    except KeyError as exp:
        raise requests.RequestException("could not get rewards") from exp

    return rewards


def get_firsts(broadcaster_id):
    firsts = First.query.filter(First.broadcaster_id == broadcaster_id).all()

    first_counts = defaultdict(lambda: 0)
    for first in firsts:
        user_name = first.name
        first_counts[user_name] += 1

    return first_counts


def create_eventsub(access_token, broadcaster_id, reward_id):
    eventsub_create = requests.post(
        f"{Config.TWITCH_API_BASEURL}/eventsub/subscriptions",
        headers={"Authorization": f"Bearer {access_token}", "Client-ID": Config.CLIENT_ID},
        json={
            "type": "channel.channel_points_custom_reward_redemption.add",
            "version": "1",
            "condition": {
                "broadcaster_user_id": str(broadcaster_id),
                "reward_id": str(reward_id),
            },
            "transport": {
                "method": "webhook",
                "callback": Config.EVENTSUB_CALLBACK_URL,
                "secret": Config.EVENTSUB_SECRET,
            },
        },
        timeout=Config.REQUEST_TIMEOUT,
    )

    LOG.info(f"{eventsub_create.json()}")

    eventsub_create.raise_for_status()

    try:
        eventsub_id = eventsub_create.json()["data"][0]["id"]
    except KeyError as exp:
        raise requests.RequestException("could not create eventsub") from exp

    return eventsub_id


def get_eventsubs(access_token):
    req = requests.get(
        f"{Config.TWITCH_API_BASEURL}/eventsub/subscriptions",
        headers={"Authorization": f"Bearer {access_token}", "Client-ID": Config.CLIENT_ID},
        timeout=Config.REQUEST_TIMEOUT,
    )
    req.raise_for_status()

    try:
        eventsubs = req.json()["data"]
    except KeyError as exp:
        raise requests.RequestException("could not get eventsubs") from exp

    return eventsubs


def delete_eventsub(access_token, eventsub_id):
    eventsub_delete = requests.delete(
        f"{Config.TWITCH_API_BASEURL}/eventsub/subscriptions",
        headers={"Authorization": f"Bearer {access_token}", "Client-ID": Config.CLIENT_ID},
        params={"id": eventsub_id},
        timeout=Config.REQUEST_TIMEOUT,
    )

    LOG.info(f"{eventsub_delete.text}")
    eventsub_delete.raise_for_status()


def update_eventsub(broadcaster_id, reward_id):
    LOG.info(f"broadcaster_id = {broadcaster_id}")

    # check if eventsub id exists in the db
    broadcaster = Broadcaster.query.filter(Broadcaster.id == broadcaster_id).one()
    db_eventsub_id = broadcaster.eventsub_id
    LOG.info(f"db_eventsub_id = {db_eventsub_id}")

    # check if eventsub id exists in the twitch API
    existing_eventsubs = get_eventsubs(Config.APP_ACCESS_TOKEN)
    eventsub_id = None
    for eventsub in existing_eventsubs:
        eventsub_id = eventsub["id"]
        if eventsub["condition"]["reward_id"] == reward_id:
            pass
            LOG.info(
                f"found existing eventsub_id={eventsub_id} for broadcaster_id={broadcaster_id}"
            )
        else:
            LOG.info(
                f"deleting old eventsub eventsub_id={eventsub_id} for broadcaster_id={broadcaster_id}"
            )
            delete_eventsub(Config.APP_ACCESS_TOKEN, eventsub_id)

    LOG.info(f"{existing_eventsubs}")
    # create eventsub if it doesn't exist
    if eventsub_id is None:
        LOG.info(f"creating new eventsub for broadcaster_id={broadcaster_id}")
        eventsub_id = create_eventsub(Config.APP_ACCESS_TOKEN, broadcaster_id, reward_id)

    # update eventsub details to the database if required
    if db_eventsub_id != eventsub_id:
        LOG.info(
            f"updating database with eventsub details, eventsub_id={eventsub_id} broadcaster_id={broadcaster_id}"
        )
        broadcaster.eventsub_id = eventsub_id
        db.session.commit()

    return eventsub_id


def update_reward(broadcaster_id, reward_id):
    LOG.info(f"broadcaster_id = {broadcaster_id}")

    # # check if reward id exists in the db
    broadcaster = Broadcaster.query.filter(Broadcaster.id == broadcaster_id).one()
    db_reward_id = broadcaster.reward_id
    LOG.info(f"db_reward_id = {db_reward_id}")

    # update reward details in the database if required
    if db_reward_id != reward_id:
        LOG.info(
            f"updating database with reward details, reward_id={reward_id} broadcaster_id={broadcaster_id}"
        )
        broadcaster.reward_id = reward_id
        db.session.commit()

    return reward_id


def add_first(broadcaster_id, user_name):
    first = First(broadcaster_id=broadcaster_id, name=user_name)
    db.session.add(first)
    db.session.commit()

    return first
