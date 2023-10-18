"""Auth routes."""
from flask import (
    Blueprint,
    Response,
    make_response,
    render_template,
    abort,
    jsonify,
    request,
    current_app,
)
from requests import RequestException

from verifiedfirst import twitch, verify

bp = Blueprint("auth", __name__)


@bp.route("/auth", methods=["GET"])
def auth() -> Response:
    """Endpoint to redirect twitch oauth requests to. Ensures that api auth tokens are stored in the
    database under the appropriate broadcaster.

    :return: javascript that sends a message to the parent window (AUTH_SUCCESSFUL or AUTH_FAILED)
    """
    current_app.logger.debug(request.headers)

    if "error" in request.args:
        return make_response(render_template("auth.html", auth_msg="AUTH_FAILED"))
    try:
        code = request.args["code"]
        current_app.logger.debug("code=%s", code)
        access_token, refresh_token = twitch.get_auth_tokens(code)
        twitch.update_broadcaster_details(access_token, refresh_token)
        auth_msg = "AUTH_SUCCESSFUL"
    except Exception as exp:  # pylint: disable=broad-exception-caught
        current_app.logger.error("auth failed: %s", exp)
        auth_msg = "AUTH_FAILED"

    return make_response(render_template("auth.html", auth_msg=auth_msg))


@bp.route("/auth/check", methods=["GET"])
@verify.token_required
def auth_check(channel_id: int, role: str) -> Response:
    """Checks if the broadcaster auth is valid."""

    # pylint: disable=duplicate-code
    if role != "broadcaster":
        abort(403, "user role is not broadcaster")

    # check broadcaster exists in database
    broadcaster = twitch.get_broadcaster(channel_id)
    if broadcaster is None:
        abort(403, "broadcaster is not authed yet")
    # pylint: disable=

    try:
        twitch.get_broadcaster_from_token(broadcaster.access_token)
    except RequestException:
        abort(403, "broadcaster auth is invalid")

    return make_response(jsonify({"auth_status": "OK"}))
