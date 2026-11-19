"""Functions related to the twitch api."""

from collections import defaultdict
from typing import Any, List, Tuple
from datetime import datetime, timedelta, UTC

from flask import current_app
from requests import Request, Response, Session, codes, post
from requests.exceptions import RequestException
from sqlalchemy.exc import NoResultFound, SQLAlchemyError

from verifiedfirst.models.broadcasters import Broadcaster
from verifiedfirst.models.firsts import First
from verifiedfirst.models.users import User
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
    """Request the twitch api with a user (broadcaster) token.

    If the request fails due to the auth token being expired, the token is attempted to be refreshed
    and the request is retried.

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
        if exp.response is None or exp.response.status_code != codes.unauthorized:
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
        if exp.response is None or exp.response.status_code != codes.unauthorized:
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

    # Aggregate by user_id for rows that have one (using the current cached username),
    # and by name for legacy rows with no user_id.
    counts_by_user_id: dict[int, int] = defaultdict(lambda: 0)
    counts_by_name: dict[str, int] = defaultdict(lambda: 0)
    for first in firsts:
        if first.user_id is not None:
            counts_by_user_id[first.user_id] += 1
        else:
            counts_by_name[first.name] += 1

    first_counts: dict[str, Any] = {}
    for user_id, count in counts_by_user_id.items():
        user = db.session.get(User, user_id)
        if user is None:
            raise ValueError(f"User {user_id} referenced in firsts but not found in database")
        first_counts[user.name] = count
    for name, count in counts_by_name.items():
        first_counts[name] = first_counts.get(name, 0) + count

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
        # keep the response so callers can tell why it failed (e.g. 403 if the broadcaster
        # hasn't authorized the extension)
        raise RequestException(
            "could not create eventsub", response=getattr(exp, "response", None)
        ) from exp

    return eventsub_id


def list_eventsubs(params: dict[str, Any]) -> List[Any]:
    """Get every eventsub the application has created that matches the query params, following the
    pagination cursor until the last page.

    This includes eventsubs created by other deployments sharing the same client id (e.g. test), so
    callers should check the transport callback before acting on them.

    :param params: query params to filter the eventsubs by e.g. {"user_id": 1234}
    :raises RequestException: if any request fails
    :return: list of eventsubs
    """
    eventsubs: List[Any] = []
    cursor = None
    while True:
        page_params = dict(params)
        if cursor:
            page_params["after"] = cursor
        req = Request(
            method="GET",
            url=f"{current_app.config['TWITCH_API_BASEURL']}/eventsub/subscriptions",
            params=page_params,
            headers={"Client-ID": current_app.config["CLIENT_ID"]},
        )

        resp = request_twitch_api_app(req)

        try:
            page = resp.json()
            page_eventsubs = page["data"]
            assert isinstance(page_eventsubs, list)
            cursor = page.get("pagination", {}).get("cursor")
        except (KeyError, TypeError, AttributeError, AssertionError) as exp:
            raise RequestException("could not get eventsubs") from exp

        eventsubs.extend(page_eventsubs)
        if not cursor:
            return eventsubs


def get_eventsubs(broadcaster: Broadcaster) -> List[Any]:
    """Get list of eventsubs the application has created for a broadcaster.

    :param broadcaster: broadcaster to get eventsubs for
    :raises RequestException: if the request fails
    :return: list of eventsubs
    """
    return list_eventsubs({"user_id": broadcaster.id})


def get_all_eventsubs() -> List[Any]:
    """Get every channel points redemption eventsub the application has created, for all
    broadcasters.

    :raises RequestException: if any request fails
    :return: list of eventsubs
    """
    return list_eventsubs({"type": "channel.channel_points_custom_reward_redemption.add"})


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


def update_eventsub(
    broadcaster: Broadcaster, reward_id: str, existing_eventsubs: List[Any] | None = None
) -> str:
    """Configure eventsubs for channel points events to ensure the application is listening for the
    correct reward redemptions for a specific broadcaster.

    Only eventsubs pointing at this instance's EVENTSUB_CALLBACK_URL are reused or deleted. The
    client id may be shared with other deployments (e.g. test), and their eventsubs are left alone.

    :param broadcaster: broadcaster to update eventsub data for
    :param reward_id: id of the reward to update the eventsub for
    :param existing_eventsubs: the broadcaster's eventsubs if they have already been fetched from
        the twitch api, otherwise they are fetched
    :return: id of the eventsub
    """
    broadcaster_id = broadcaster.id
    current_app.logger.info("updating eventsub for broadcaster_id=%s", broadcaster_id)

    # check if eventsub id exists in the db
    db_eventsub_id = broadcaster.eventsub_id
    current_app.logger.debug("db_eventsub_id=%s", db_eventsub_id)

    # check if eventsub id exists in the twitch API
    if existing_eventsubs is None:
        existing_eventsubs = get_eventsubs(broadcaster)
    current_app.logger.debug("existing_eventsubs=%s", existing_eventsubs)
    matching_eventsubs = []
    for eventsub in existing_eventsubs:
        current_app.logger.debug("eventsub=%s", eventsub)
        eventsub_id = eventsub["id"]
        # an eventsub pointing at a different callback url belongs to another deployment sharing
        # the client id, it would never deliver events to this instance and isn't ours to delete
        if eventsub["transport"]["callback"] != current_app.config["EVENTSUB_CALLBACK_URL"]:
            current_app.logger.debug(
                "ignoring eventsub_id=%s for another callback url", eventsub_id
            )
            continue
        if eventsub["condition"]["reward_id"] == reward_id and eventsub["status"] == "enabled":
            matching_eventsubs.append(eventsub_id)
        else:
            current_app.logger.info(
                "deleting old eventsub eventsub_id=%s for broadcaster_id=%s",
                eventsub_id,
                broadcaster_id,
            )
            delete_eventsub(eventsub_id)

    # keep a single matching eventsub, preferring the one already in the database
    matching_eventsub = None
    if matching_eventsubs:
        if db_eventsub_id in matching_eventsubs:
            matching_eventsub = db_eventsub_id
        else:
            matching_eventsub = matching_eventsubs[0]
        current_app.logger.info(
            "found existing eventsub_id=%s for broadcaster_id=%s",
            matching_eventsub,
            broadcaster_id,
        )
        for eventsub_id in matching_eventsubs:
            if eventsub_id != matching_eventsub:
                current_app.logger.info(
                    "deleting duplicate eventsub eventsub_id=%s for broadcaster_id=%s",
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


# Twitch /users endpoint accepts up to 100 logins or ids per request
USERS_BATCH_SIZE = 100


def lookup_users(param: str, values: List[str] | List[int]) -> List[dict[str, Any]]:
    """Look up Twitch users by login name or id, in batches of USERS_BATCH_SIZE.

    :param param: query parameter to look users up by, either "login" or "id"
    :param values: login names or ids to look up
    :raises RequestException: if any request fails
    :return: user data returned by the Twitch API for each user that was found
    """
    users: List[dict[str, Any]] = []
    for i in range(0, len(values), USERS_BATCH_SIZE):
        batch = values[i : i + USERS_BATCH_SIZE]
        req = Request(
            method="GET",
            url=f"{current_app.config['TWITCH_API_BASEURL']}/users",
            headers={"Client-ID": current_app.config["CLIENT_ID"]},
            params=[(param, value) for value in batch],
        )
        try:
            resp = request_twitch_api_app(req)
            batch_users = resp.json()["data"]
            assert isinstance(batch_users, list)
        except (RequestException, KeyError, AssertionError) as exp:
            raise RequestException(f"could not look up users by {param}") from exp
        users.extend(batch_users)

    return users


def get_users_by_login(logins: List[str]) -> dict[str, int]:
    """Look up Twitch users by login name and return a mapping of login -> user_id.

    Logins not found in the API response (e.g. because the username no longer exists) are omitted
    from the result.

    :param logins: list of Twitch login names to look up
    :raises RequestException: if the request fails
    :return: dict mapping login name to numeric Twitch user id
    """
    return {user["login"]: int(user["id"]) for user in lookup_users("login", logins)}


def get_users_by_id(user_ids: List[int]) -> dict[int, dict[str, Any]]:
    """Look up Twitch users by id and return a mapping of user_id -> user data.

    Ids not found in the API response (e.g. because the account has been deleted or suspended) are
    omitted from the result.

    :param user_ids: list of numeric Twitch user ids to look up
    :raises RequestException: if the request fails
    :return: dict mapping numeric Twitch user id to the user data returned by the Twitch API
    """
    return {int(user["id"]): user for user in lookup_users("id", user_ids)}


def refresh_profile_images(users: List[User]) -> None:
    """Refresh the cached profile image url for any users whose cached value is missing or stale.

    This is called while handling viewer requests, so to keep those requests fast at most one batch
    of users (a single Twitch API request) is refreshed per call, oldest first. Any remaining stale
    users are refreshed by later calls.

    If the Twitch API can't be reached the existing cached values are kept, and no further refreshes
    are attempted for PROFILE_IMAGE_RETRY_DELAY seconds, so an outage only results in out of date
    (or missing) images rather than an error or slow requests.

    :param users: users to refresh profile images for
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    retry_after = current_app.config["PROFILE_IMAGE_RETRY_AFTER"]
    if retry_after is not None and now < retry_after:
        return

    max_age = timedelta(seconds=current_app.config["PROFILE_IMAGE_MAX_AGE"])
    stale_users = [
        user
        for user in users
        if user.profile_image_updated is None or now - user.profile_image_updated > max_age
    ]
    if not stale_users:
        return

    stale_users.sort(key=lambda user: user.profile_image_updated or datetime.min)
    stale_users = stale_users[:USERS_BATCH_SIZE]

    try:
        twitch_users = get_users_by_id([user.id for user in stale_users])
    except RequestException as exp:
        current_app.config["PROFILE_IMAGE_RETRY_AFTER"] = now + timedelta(
            seconds=current_app.config["PROFILE_IMAGE_RETRY_DELAY"]
        )
        current_app.logger.warning("could not refresh profile images: %s", exp)
        return
    current_app.config["PROFILE_IMAGE_RETRY_AFTER"] = None

    for user in stale_users:
        # users missing from the response no longer exist on twitch, so stop showing their image
        twitch_user = twitch_users.get(user.id, {})
        user.profile_image_url = twitch_user.get("profile_image_url") or None
        user.profile_image_updated = now
    try:
        db.session.commit()
    except SQLAlchemyError as exp:
        # e.g. the database is locked by another worker refreshing the same users
        db.session.rollback()
        current_app.logger.warning("could not save refreshed profile images: %s", exp)


def get_avatars(broadcaster: Broadcaster) -> dict[str, str]:
    """Get the profile image url of each user that has a "first" for a specific broadcaster.

    Legacy "firsts" without a user id can't be looked up, so those users are omitted.

    :param broadcaster: broadcaster to get avatars for
    :return: dictionary of profile image urls by user e.g {"user1": "https://..."}
    """
    users = (
        User.query.join(First, First.user_id == User.id)
        .filter(First.broadcaster_id == broadcaster.id)
        .distinct()
        .all()
    )
    refresh_profile_images(users)

    return {user.name: user.profile_image_url for user in users if user.profile_image_url}


def upsert_user(user_id: int, user_name: str) -> User:
    """Insert or update a user in the User cache table.

    :param user_id: numeric Twitch user id
    :param user_name: current Twitch login name for the user
    :return: User object
    """
    user = db.session.get(User, user_id)
    if user is None:
        user = User(id=user_id, name=user_name)
        db.session.add(user)
    else:
        user.name = user_name
        user.last_seen = datetime.now(UTC).replace(tzinfo=None)
    db.session.commit()
    return user


def add_first(broadcaster_id: int, user_id: int, user_name: str) -> First:
    """Adds a "first" entry to the database.

    :param broadcaster_id: id of the broadcaster to add the first entry for
    :param user_id: numeric Twitch id of the user who was first
    :param user_name: login name of the user who was first
    :return: First object that was created
    """
    upsert_user(user_id, user_name)
    first = First(broadcaster_id=broadcaster_id, name=user_name, user_id=user_id)
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
