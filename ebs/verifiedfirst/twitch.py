"""Functions related to the twitch api."""
from collections import defaultdict
from typing import Any, List, Tuple
from datetime import datetime

from flask import current_app
from requests import Request, Response, Session, codes, post
from requests.exceptions import RequestException
from sqlalchemy.exc import NoResultFound

from verifiedfirst.models.broadcasters import Broadcaster
from verifiedfirst.models.firsts import First
from verifiedfirst.database import db


def get_auth_tokens(code: str) -> Tuple[str, str]:
    """Get an auth token from the twitch api using the "OIDC authorization code grant flow".

    :param code: auth code to use to generate token
    :raises RequestException: if request fails
    :raises KeyError: if response doesn't contain expected values
    :return: valid access token
    """
    req = post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": current_app.config["CLIENT_ID"],
            "client_secret": current_app.config["CLIENT_SECRET"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": current_app.config["REDIRECT_URI"],
        },
        timeout=current_app.config["REQUEST_TIMEOUT"],
    )

    try:
        req.raise_for_status()
        auth = req.json()
        current_app.logger.debug("auth: %s", auth)

        access_token = auth["access_token"]
        refresh_token = auth["refresh_token"]
    except (RequestException, KeyError) as exp:
        raise exp

    return access_token, refresh_token


def get_app_access_token() -> str:
    """Gets an app access token using the "client credentials" twitch oauth flow.

    :raises RequestException: if request fails
    :raises KeyError: if response doesn't contain expected values
    :raises AssertionError: if the access token is in the wrong format
    :return: valid access token
    """
    req = post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": current_app.config["CLIENT_ID"],
            "client_secret": current_app.config["CLIENT_SECRET"],
            "grant_type": "client_credentials",
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=current_app.config["REQUEST_TIMEOUT"],
    )

    try:
        req.raise_for_status()
        auth = req.json()
        current_app.logger.debug("auth: %s", auth)

        access_token = auth["access_token"]
        assert isinstance(access_token, str)
    except (RequestException, KeyError, AssertionError) as exp:
        raise exp

    return access_token


def refresh_auth_token(broadcaster: Broadcaster) -> Broadcaster:
    """Refresh authorization token for a specific broadcaster.

    :param broadcaster: Broadcaster object to refresh token for
    :raises RequestException: if request fails
    :raises KeyError: if response doesn't contain expected values
    :return: Broadcaster object with updated auth tokens
    """
    req = post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": current_app.config["CLIENT_ID"],
            "client_secret": current_app.config["CLIENT_SECRET"],
            "refresh_token": broadcaster.refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=current_app.config["REQUEST_TIMEOUT"],
    )

    try:
        req.raise_for_status()
        auth = req.json()
        current_app.logger.debug("auth: %s", auth)

        access_token = auth["access_token"]
        refresh_token = auth["refresh_token"]
    except (RequestException, KeyError) as exp:
        raise exp

    broadcaster.access_token = access_token
    broadcaster.refresh_token = refresh_token
    db.session.commit()

    return broadcaster


def request_twitch_api(access_token: str, request: Request) -> Response:
    """Send request to twitch api.

    :param access_token: access token to use for authenticating the request
    :param request: request to send to the twitch api
    :return: response from the request
    """
    request.headers["Authorization"] = f"Bearer {access_token}"

    session = Session()

    resp = session.send(
        request.prepare(),
        timeout=current_app.config["REQUEST_TIMEOUT"],
    )

    return resp


def request_twitch_api_broadcaster(broadcaster: Broadcaster, request: Request) -> Response:
    """Request the twitch api with a user (broadcaster) token. If the request fails due to the auth
    token being expired, the token is attempted to be refreshed and the request is retried.

    :param broadcaster: broadcaster to perform the request for
    :param request: request to send to the twitch api
    :raises RequestException: if the request fails
    :return: response from the request
    """

    try:
        resp = request_twitch_api(broadcaster.access_token, request)
        resp.raise_for_status()
        return resp
    except RequestException as exp:
        current_app.logger.error("request to twitch api failed: %s", exp)
        if resp.status_code != codes.unauthorized:
            raise exp

    # if we get an unauthorized response, try to refresh the token
    current_app.logger.debug("refreshing auth token")
    try:
        broadcaster = refresh_auth_token(broadcaster)
    except RequestException as exp:
        current_app.logger.error("failed to refresh auth token: %s", exp)
        raise exp

    # retry the request with a new token
    current_app.logger.debug("retrying with new auth token: %s", broadcaster.access_token)

    resp = request_twitch_api(broadcaster.access_token, request)
    resp.raise_for_status()

    return resp


def request_twitch_api_app(request: Request) -> Response:
    """Request the twitch api using the application access token.

    :param request: request to send to the twitch api
    :raises RequestException: if the request fails
    :return: response from the twitch api
    """
    try:
        resp = request_twitch_api(current_app.config["APP_ACCESS_TOKEN"], request)
        resp.raise_for_status()
        return resp
    except RequestException as exp:
        current_app.logger.error("request to twitch api failed: %s", exp)
        if resp.status_code != codes.unauthorized:
            raise exp

    # if we get an unauthorized response, try to refresh the token
    current_app.logger.debug("refreshing auth token")
    try:
        access_token = get_app_access_token()
        current_app.config["APP_ACCESS_TOKEN"] = access_token
    except RequestException as exp:
        current_app.logger.error("failed to refresh auth token: %s", exp)
        raise exp

    # retry the request with a new token
    current_app.logger.debug(
        "retrying with new auth token: %s", current_app.config["APP_ACCESS_TOKEN"]
    )

    resp = request_twitch_api(current_app.config["APP_ACCESS_TOKEN"], request)
    resp.raise_for_status()

    return resp


def get_broadcaster_from_token(access_token: str) -> Tuple[str, int]:
    """Find the broadcaster that an access token belongs to.

    :param access_token: access token to check
    :raises RequestException: if the request fails
    :return: name and id of the broadcaster
    """
    req = Request(
        method="GET",
        url=f"{current_app.config['TWITCH_API_BASEURL']}/users",
        headers={"Client-ID": current_app.config["CLIENT_ID"]},
    )

    try:
        resp = request_twitch_api(access_token, req)
        resp.raise_for_status()
        user = resp.json()["data"][0]
        broadcaster_name = user["login"]
        broadcaster_id = int(user["id"])
        assert isinstance(broadcaster_name, str)
        assert isinstance(broadcaster_id, int)
    except (RequestException, KeyError, AssertionError, ValueError) as exp:
        raise RequestException(f"could not get broadcaster: {type(exp).__name__} {exp}") from exp

    return broadcaster_name, broadcaster_id


def update_broadcaster_details(access_token: str, refresh_token: str) -> Tuple[str, int]:
    """Update broadcaster details in the database.

    :param access_token: access token for the broadcaster
    :param refresh_token: refresh token for the broadcaster
    :return: broadcaster name and id
    """
    broadcaster_name, broadcaster_id = get_broadcaster_from_token(access_token)

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


def get_rewards(broadcaster: Broadcaster) -> list[Any]:
    """Get list of rewards from a broadcaster.

    :param broadcaster: broadcaster to get rewards for
    :raises RequestException: if the request to the twitch api fails
    :return: list of rewards
    """
    req = Request(
        method="GET",
        url=f"{current_app.config['TWITCH_API_BASEURL']}/channel_points/custom_rewards",
        headers={"Client-ID": current_app.config["CLIENT_ID"]},
        params={
            "broadcaster_id": broadcaster.id,
            "only_manageable_rewards": "False",
        },
    )

    try:
        resp = request_twitch_api_broadcaster(broadcaster, req)
        rewards = resp.json()["data"]
        assert isinstance(rewards, list)
    except (RequestException, KeyError, AssertionError) as exp:
        error_msg = f"could not get rewards: {exp}"
        current_app.logger.error(error_msg)
        raise RequestException() from exp

    return rewards


def get_firsts(
    broadcaster: Broadcaster, start_time: datetime | None = None, end_time: datetime | None = None
) -> dict[str, Any]:
    """Get total count of "firsts"for a specific broadcaster.

    :param broadcaster: broadcaster to count firsts for
    :param start_time: count firsts at or after this date
    :param end_time: count firsts at or before this date
    :return: dictionary of first counts by user e.g {"user1": 5, "user2": 3}
    """

    if start_time is None:
        start_time = datetime.min
    if end_time is None:
        end_time = datetime.max

    firsts = First.query.filter(
        First.broadcaster_id == broadcaster.id,
        First.timestamp >= start_time,
        First.timestamp <= end_time,
    ).all()

    first_counts: dict[str, Any] = defaultdict(lambda: 0)
    for first in firsts:
        user_name = first.name
        first_counts[user_name] += 1

    return first_counts


def create_eventsub(broadcaster: Broadcaster, reward_id: str) -> str:
    """Create an eventsub to listen for channel point redemption for a specific reward id.

    :param broadcaster: broadcaster to create the eventsub for
    :param reward_id: id of the reward to create an eventsub for
    :raises RequestException: if the request fails
    :return: id of the created eventsub
    """
    req = Request(
        method="POST",
        url=f"{current_app.config['TWITCH_API_BASEURL']}/eventsub/subscriptions",
        headers={"Client-ID": current_app.config["CLIENT_ID"]},
        json={
            "type": "channel.channel_points_custom_reward_redemption.add",
            "version": "1",
            "condition": {
                "broadcaster_user_id": str(broadcaster.id),
                "reward_id": str(reward_id),
            },
            "transport": {
                "method": "webhook",
                "callback": current_app.config["EVENTSUB_CALLBACK_URL"],
                "secret": current_app.config["EVENTSUB_SECRET"],
            },
        },
    )

    try:
        resp = request_twitch_api_app(req)
        current_app.logger.debug("response: %s", resp.text)
        eventsub_id = resp.json()["data"][0]["id"]
        assert isinstance(eventsub_id, str)
    except (RequestException, KeyError, AssertionError) as exp:
        raise RequestException("could not create eventsub") from exp

    return eventsub_id


def get_eventsubs(broadcaster: Broadcaster) -> List[Any]:
    """Get list of eventsubs the application has created.

    :param broadcaster: broadcaster to get eventsubs for
    :raises RequestException: if the request fails
    :return: list of eventsubs
    """
    req = Request(
        method="GET",
        url=f"{current_app.config['TWITCH_API_BASEURL']}/eventsub/subscriptions",
        params={"user_id": broadcaster.id},
        headers={"Client-ID": current_app.config["CLIENT_ID"]},
    )

    resp = request_twitch_api_app(req)

    try:
        eventsubs = resp.json()["data"]
        assert isinstance(eventsubs, list)
    except (KeyError, TypeError, AssertionError) as exp:
        raise RequestException("could not get eventsubs") from exp

    return eventsubs


def delete_eventsub(eventsub_id: str) -> None:
    """Delete an eventsub from the twitch api.

    :param eventsub_id: id of the eventsub to delete
    :raises RequestException: if the request fails
    """
    req = Request(
        method="DELETE",
        url=f"{current_app.config['TWITCH_API_BASEURL']}/eventsub/subscriptions",
        headers={"Client-ID": current_app.config["CLIENT_ID"]},
        params={"id": eventsub_id},
    )

    resp = request_twitch_api_app(req)
    current_app.logger.debug("delete eventsub response=%s", resp.text)


def update_eventsub(broadcaster: Broadcaster, reward_id: str) -> str:
    """Configure eventsubs for channel points events to ensure the application is listening for the
    correct reward redemptions for a specific broadcaster.

    :param broadcaster: broadcaster to update eventsub data for
    :param reward_id: id of the reward to update the eventsub for
    :return: id of the eventsub
    """
    broadcaster_id = broadcaster.id
    current_app.logger.info("updating eventsub for broadcaster_id=%s", broadcaster_id)

    # check if eventsub id exists in the db
    db_eventsub_id = broadcaster.eventsub_id
    current_app.logger.debug("db_eventsub_id=%s", db_eventsub_id)

    # check if eventsub id exists in the twitch API
    existing_eventsubs = get_eventsubs(broadcaster)
    matching_eventsub = None
    current_app.logger.debug("existing_eventsubs=%s", existing_eventsubs)
    for eventsub in existing_eventsubs:
        current_app.logger.debug("eventsub=%s", eventsub)
        eventsub_id = eventsub["id"]
        eventsub_status = eventsub["status"]
        eventsub_reward_id = eventsub["condition"]["reward_id"]
        if eventsub_reward_id == reward_id and eventsub_status == "enabled":
            current_app.logger.info(
                "found existing eventsub_id=%s for broadcaster_id=%s",
                eventsub_id,
                broadcaster_id,
            )
            matching_eventsub = eventsub_id
        else:
            current_app.logger.info(
                "deleting old eventsub eventsub_id=%s for broadcaster_id=%s",
                eventsub_id,
                broadcaster_id,
            )
            delete_eventsub(eventsub_id)

    # create eventsub if it doesn't exist
    if matching_eventsub is None:
        current_app.logger.info("creating new eventsub for broadcaster_id=%s", broadcaster_id)
        matching_eventsub = create_eventsub(broadcaster, reward_id)

    # update eventsub details to the database if required
    if db_eventsub_id != matching_eventsub:
        current_app.logger.info(
            "updating database with eventsub details, eventsub_id=%s broadcaster_id=%s",
            matching_eventsub,
            broadcaster_id,
        )
        broadcaster.eventsub_id = matching_eventsub
        db.session.commit()

    return matching_eventsub


def update_reward(broadcaster: Broadcaster, reward_id: str) -> str:
    """Updates reward details for a broadcaster.

    :param broadcaster: Broadcaster object to update the reward for
    :param reward_id: id of the reward to use to track "firsts"
    :return: id of the reward
    """
    current_app.logger.info("updating reward for broadcaster_id=%s", broadcaster.id)

    db_reward_id = broadcaster.reward_id
    current_app.logger.debug("db_reward_id=%s", db_reward_id)

    # update reward details in the database if required
    if db_reward_id != reward_id:
        current_app.logger.info(
            "updating database with reward details, reward_id=%s broadcaster_id=%s",
            reward_id,
            broadcaster.id,
        )
        broadcaster.reward_id = reward_id
        db.session.commit()

    return reward_id


def add_first(broadcaster_id: int, user_name: str) -> First:
    """Adds a "first" entry to the database.

    :param broadcaster_id: id of the broadcaster to add the first entry for
    :param user_name: name of the user who was first
    :return: First object that was created
    """
    first = First(broadcaster_id=broadcaster_id, name=user_name)
    db.session.add(first)
    db.session.commit()

    return first


def get_broadcaster(broadcaster_id: int) -> Broadcaster | None:
    """Get a broadcaster details from the database.

    :param broadcaster_id: id of the broadcaster to retrieve
    :return: matching broadcaster object or None
    """

    try:
        broadcaster = Broadcaster.query.filter(Broadcaster.id == broadcaster_id).one()
    except NoResultFound:
        broadcaster = None

    assert isinstance(broadcaster, Broadcaster) or broadcaster is None

    return broadcaster
