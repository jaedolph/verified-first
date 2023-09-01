import logging

from verifiedfirst.config import Config
import hmac
import hashlib
import jwt
import base64

LOG = logging.getLogger()


def get_hmac(hmac_message):
    hmac_value = hmac.new(
        Config.EVENTSUB_SECRET.encode("utf-8"), hmac_message, hashlib.sha256
    ).hexdigest()

    LOG.info(f"calculated hmac as sha256={hmac_value}")

    return hmac_value


def verify_eventsub_message(request):
    headers = request.headers
    body = request.data

    LOG.info(f"body type = {type(body)}")

    message_id = headers["Twitch-Eventsub-Message-Id"]
    message_timestamp = headers["Twitch-Eventsub-Message-Timestamp"]
    message_signature = headers["Twitch-Eventsub-Message-Signature"]

    hmac_message = message_id.encode("utf-8") + message_timestamp.encode("utf-8") + body
    LOG.info(f"type {type(hmac_message)} hmac_message = {hmac_message}")

    hmac_value = f"sha256={get_hmac(hmac_message)}"

    if hmac_value == message_signature:
        return True

    return False


def verify_jwt(request):
    headers = request.headers

    try:
        token = headers["Authorization"].split(" ")[1].strip()
    except KeyError as exp:
        LOG.info(f"could not get auth token from headers: {exp}")
        return None

    LOG.debug(f"token: {token}")
    payload = None
    try:
        payload = jwt.decode(
            token, key=base64.b64decode(Config.EXTENSION_SECRET), algorithms=["HS256"]
        )
    except jwt.exceptions.InvalidSignatureError as exp:
        LOG.error(f"error: {exp}")

    LOG.debug(f"payload: {payload}")
    return payload
