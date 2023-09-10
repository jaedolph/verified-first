"""verify.py."""
import base64
import hashlib
import hmac
import logging
from typing import Tuple

import jwt
from flask import Request

from verifiedfirst.config import Config

LOG = logging.getLogger("verifiedfirst")


def get_hmac(hmac_message: bytes) -> str:
    """Calculates the hmac of a message.

    :param hmac_message: concatenated hmac message
    :return: hmac hex string
    """
    hmac_value = hmac.new(
        Config.EVENTSUB_SECRET.encode("utf-8"), hmac_message, hashlib.sha256
    ).hexdigest()

    LOG.info("calculated hmac as sha256=%s", hmac_value)

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

    hmac_message = message_id.encode("utf-8") + message_timestamp.encode("utf-8") + body
    hmac_value = f"sha256={get_hmac(hmac_message)}"

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
        token = headers["Authorization"].split(" ")[1].strip()
    except KeyError as exp:
        LOG.info("could not get auth token from headers: %s", exp)

    LOG.debug("token=%s", token)
    payload = None
    try:
        payload = jwt.decode(
            token, key=base64.b64decode(Config.EXTENSION_SECRET), algorithms=["HS256"]
        )
        LOG.debug("payload: %s", payload)
        channel_id = int(payload["channel_id"])
        role = payload["role"]
        assert isinstance(channel_id, int)
        assert isinstance(role, str)
    except (jwt.exceptions.InvalidSignatureError, AssertionError, KeyError, ValueError) as exp:
        LOG.error("error: %s", exp)
        raise PermissionError() from exp

    return channel_id, role
