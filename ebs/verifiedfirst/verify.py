import base64
import hashlib
import hmac
import logging

import jwt
from verifiedfirst.config import Config

LOG = logging.getLogger("verifiedfirst")


def get_hmac(hmac_message):
    hmac_value = hmac.new(
        Config.EVENTSUB_SECRET.encode("utf-8"), hmac_message, hashlib.sha256
    ).hexdigest()

    LOG.info("calculated hmac as sha256=%s", hmac_value)

    return hmac_value


def verify_eventsub_message(request):
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


def verify_jwt(request):
    headers = request.headers

    try:
        token = headers["Authorization"].split(" ")[1].strip()
    except KeyError as exp:
        LOG.info("could not get auth token from headers: %s", exp)
        return None

    LOG.debug("token=%s", token)
    payload = None
    try:
        payload = jwt.decode(
            token, key=base64.b64decode(Config.EXTENSION_SECRET), algorithms=["HS256"]
        )
    except jwt.exceptions.InvalidSignatureError as exp:
        LOG.error("error: %s", exp)

    LOG.debug("payload: %s", payload)
    return payload
