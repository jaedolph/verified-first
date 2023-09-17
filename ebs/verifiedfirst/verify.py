"""Functions related to verification of auth tokens."""
from functools import wraps
from typing import Callable, TypeVar, Tuple, cast
import base64
import hashlib
import hmac

import jwt
from flask import Request, current_app, abort
from flask import request as flask_request


R = TypeVar("R")


def token_required(func: Callable[[int, str], R]) -> Callable[[int, str], R]:
    """Decorator to validate JWT and get the associated channel_id and role.

    :param func: function to decorate
    :return: decorated function
    """

    @wraps(func)
    def decorated_function() -> R:
        try:
            channel_id, role = verify_jwt(flask_request)
        except PermissionError as exp:
            error_msg = f"authentication failed: {exp}"
            current_app.logger.debug(error_msg)
            return abort(401, error_msg)

        current_app.logger.debug(
            "authenticated request for channel_id=%s role=%s", channel_id, role
        )
        return func(channel_id, role)

    return cast(Callable[[int, str], R], decorated_function)


def get_hmac(hmac_message: bytes) -> str:
    """Calculates the hmac of a message.

    :param hmac_message: concatenated hmac message
    :return: hmac hex string
    """
    hmac_value = hmac.new(
        current_app.config["EVENTSUB_SECRET"].encode("utf-8"), hmac_message, hashlib.sha256
    ).hexdigest()

    current_app.logger.info("calculated hmac as sha256=%s", hmac_value)

    return hmac_value


def verify_eventsub_message(request: Request) -> bool:
    """Verifies the integrity of an eventsub request.

    :param request: Request object to verify
    :return: True if the eventsub request is verified
    """
    headers = request.headers
    body = request.data

    message_id = headers["Twitch-Eventsub-Message-Id"]
    message_timestamp = headers["Twitch-Eventsub-Message-Timestamp"]
    message_signature = headers["Twitch-Eventsub-Message-Signature"]

    print(message_id, message_timestamp, message_signature, body)

    hmac_message = message_id.encode("utf-8") + message_timestamp.encode("utf-8") + body
    print(hmac_message)
    try:
        hmac_value = f"sha256={get_hmac(hmac_message)}"
        print(hmac_value)
    except TypeError as exp:
        current_app.logger.debug("failed to get hmac, %s", exp)
        return False

    if hmac_value == message_signature:
        return True

    return False


def verify_jwt(request: Request) -> Tuple[int, str]:
    """Verifies and decodes auth information from a JWT.

    :param request: Request object containing the JWT
    :raises PermissionError: if verifying or decoding the JWT fails
    :return: the channel id the request was made for and the role of the user making the request
    """
    headers = request.headers

    try:
        auth_header = headers["Authorization"]
        current_app.logger.debug("auth_header=%s", auth_header)
        token = auth_header.split(" ")[1].strip()
        current_app.logger.debug("token=%s", token)
    except KeyError as exp:
        error_msg = "could not get auth token from headers"
        current_app.logger.debug(error_msg)
        raise PermissionError(error_msg) from exp

    payload = None
    try:
        payload = jwt.decode(
            token,
            key=base64.b64decode(current_app.config["EXTENSION_SECRET"]),
            algorithms=["HS256"],
        )
        current_app.logger.debug("payload: %s", payload)
        channel_id = int(payload["channel_id"])
        role = payload["role"]
        assert isinstance(channel_id, int)
        assert isinstance(role, str)
    except (jwt.exceptions.PyJWTError, AssertionError, KeyError, ValueError) as exp:
        error_message = f"could not validate jwt, {exp}"
        current_app.logger.debug(error_message)
        raise PermissionError(error_message) from exp

    return channel_id, role
