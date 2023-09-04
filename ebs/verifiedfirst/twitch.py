import logging
from collections import defaultdict

import requests
from verifiedfirst.config import Config
from verifiedfirst.extensions import db
from verifiedfirst.models.broadcasters import Broadcaster
from verifiedfirst.models.firsts import First

LOG = logging.getLogger("verifiedfirst")


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
        timeout=Config.REQUEST_TIMEOUT,
    )
    auth = req.json()

    LOG.debug("auth: %s", auth)
    req.raise_for_status()

    access_token = auth["access_token"]
    refresh_token = auth["refresh_token"]

    return access_token, refresh_token

def refresh_auth_token(broadcaster):
    req = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": Config.CLIENT_ID,
            "client_secret": Config.CLIENT_SECRET,
            "refresh_token": broadcaster.refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=Config.REQUEST_TIMEOUT,
    )
    auth = req.json()

    LOG.debug("auth: %s", auth)
    req.raise_for_status()

    access_token = auth["access_token"]
    refresh_token = auth["refresh_token"]

    broadcaster.access_token = access_token
    broadcaster.refresh_token = refresh_token
    db.session.commit()

    return broadcaster

def request_twitch_api(access_token, request):

    request.headers["Authorization"] = f"Bearer {access_token}"

    session = requests.Session()

    resp = session.send(
        request.prepare(),
        timeout=Config.REQUEST_TIMEOUT,
    )

    return resp



def request_twitch_api_broadcaster(broadcaster_id, request):

    broadcaster = Broadcaster.query.filter(Broadcaster.id == broadcaster_id).one()

    try:
        resp = request_twitch_api(broadcaster.access_token, request)
        resp.raise_for_status()
        return resp
    except requests.RequestException as exp:
        LOG.error("request to twitch api failed: %s", exp)
        if resp.status_code != requests.codes.unauthorized:
            raise exp

    # if we get an unauthorized response, try to refresh the token
    LOG.debug("refreshing auth token")
    broadcaster = refresh_auth_token(broadcaster)

    # retry the request with a new token
    LOG.debug("retrying with new auth token: %s", broadcaster.access_token)

    resp = request_twitch_api(broadcaster.access_token, request)

    return resp

def request_twitch_api_app(request):

    try:
        resp = request_twitch_api(Config.APP_ACCESS_TOKEN, request)
        resp.raise_for_status()
        return resp
    except requests.RequestException as exp:
        LOG.error("request to twitch api failed: %s", exp)
        raise exp

    # TODO: auto refresh app access token if we get an "UNAUTHORIZED" response


def get_broadcaster_from_token(access_token):
    req = requests.Request(
        method="GET",
        url=f"{Config.TWITCH_API_BASEURL}/users",
        headers={"Client-ID": Config.CLIENT_ID},
    )

    resp = request_twitch_api(access_token, req)

    resp.raise_for_status()

    user = resp.json()["data"][0]

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


def get_rewards(broadcaster_id):

    req = requests.Request(
        method="GET",
        url=f"{Config.TWITCH_API_BASEURL}/channel_points/custom_rewards",
        headers={"Client-ID": Config.CLIENT_ID},
        params={
            "broadcaster_id": broadcaster_id,
            "only_manageable_rewards": "False",
        },
    )
    resp = request_twitch_api_broadcaster(broadcaster_id, req)

    try:
        rewards = resp.json()["data"]
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


def create_eventsub(broadcaster_id, reward_id):
    req = requests.Request(
        method="POST",
        url=f"{Config.TWITCH_API_BASEURL}/eventsub/subscriptions",
        headers={"Client-ID": Config.CLIENT_ID},
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
    )

    resp = request_twitch_api_app(req)

    LOG.debug("response: %s", resp.json())

    try:
        eventsub_id = resp.json()["data"][0]["id"]
    except KeyError as exp:
        raise requests.RequestException("could not create eventsub") from exp

    return eventsub_id


def get_eventsubs():
    req = requests.Request(
        method="GET",
        url=f"{Config.TWITCH_API_BASEURL}/eventsub/subscriptions",
        headers={"Client-ID": Config.CLIENT_ID},
    )

    resp = request_twitch_api_app(req)

    try:
        eventsubs = resp.json()["data"]
    except KeyError as exp:
        raise requests.RequestException("could not get eventsubs") from exp

    return eventsubs


def delete_eventsub(eventsub_id):
    req = requests.Request(
        method="DELETE",
        url=f"{Config.TWITCH_API_BASEURL}/eventsub/subscriptions",
        headers={"Client-ID": Config.CLIENT_ID},
        params={"id": eventsub_id},
    )

    resp = request_twitch_api_app(req)

    LOG.debug("delete evensub response response=%s", resp.text)


def update_eventsub(broadcaster_id, reward_id):
    LOG.info("updating eventsub for broadcaster_id=%s", broadcaster_id)

    # check if eventsub id exists in the db
    broadcaster = Broadcaster.query.filter(Broadcaster.id == broadcaster_id).one()
    db_eventsub_id = broadcaster.eventsub_id
    LOG.debug("db_eventsub_id=%s", db_eventsub_id)

    # check if eventsub id exists in the twitch API
    existing_eventsubs = get_eventsubs()
    eventsub_id = None
    for eventsub in existing_eventsubs:
        eventsub_id = eventsub["id"]
        if eventsub["condition"]["reward_id"] == reward_id:
            LOG.info(
                "found existing eventsub_id=%s for broadcaster_id=%s",
                eventsub_id,
                broadcaster_id,
            )
        else:
            LOG.info(
                "deleting old eventsub eventsub_id=%s for broadcaster_id=%s",
                eventsub_id,
                broadcaster_id,
            )
            delete_eventsub(eventsub_id)

    LOG.debug("existing_eventsubs=%s", existing_eventsubs)
    # create eventsub if it doesn't exist
    if eventsub_id is None:
        LOG.info("creating new eventsub for broadcaster_id=%s", broadcaster_id)
        eventsub_id = create_eventsub(broadcaster_id, reward_id)

    # update eventsub details to the database if required
    if db_eventsub_id != eventsub_id:
        LOG.info(
            "updating database with eventsub details, eventsub_id=%s broadcaster_id=%s",
            eventsub_id,
            broadcaster_id,
        )
        broadcaster.eventsub_id = eventsub_id
        db.session.commit()

    return eventsub_id


def update_reward(broadcaster_id, reward_id):
    LOG.info("updating reward for broadcaster_id=%s", broadcaster_id)

    # # check if reward id exists in the db
    broadcaster = Broadcaster.query.filter(Broadcaster.id == broadcaster_id).one()
    db_reward_id = broadcaster.reward_id
    LOG.debug("db_reward_id=%s", db_reward_id)

    # update reward details in the database if required
    if db_reward_id != reward_id:
        LOG.info(
            "updating database with reward details, reward_id=%s broadcaster_id=%s",
            reward_id,
            broadcaster_id,
        )
        broadcaster.reward_id = reward_id
        db.session.commit()

    return reward_id


def add_first(broadcaster_id, user_name):
    first = First(broadcaster_id=broadcaster_id, name=user_name)
    db.session.add(first)
    db.session.commit()

    return first

def get_broadcaster(channel_id):

    return Broadcaster.query.filter(Broadcaster.id == channel_id).one()