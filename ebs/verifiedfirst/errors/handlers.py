"""Error handlers."""
from flask import Blueprint, Response, jsonify, make_response
from werkzeug.exceptions import BadRequest, Forbidden, NotFound, Unauthorized, InternalServerError

bp = Blueprint("errors", __name__)


@bp.app_errorhandler(400)  # type: ignore
def bad_request(exception: BadRequest) -> Response:
    """400 error response (bad request).

    :param exception: the exception that was raised
    :return: json formatted response
    """
    return make_response(jsonify({"error": exception.description}), 400)


@bp.app_errorhandler(401)  # type: ignore
def authorization_error(exception: Unauthorized) -> Response:
    """401 error response (unauthorized).

    :param exception: the exception that was raised
    :return: json formatted response
    """
    return make_response(jsonify({"error": exception.description}), 401)


@bp.app_errorhandler(403)  # type: ignore
def forbidden(exception: Forbidden) -> Response:
    """403 error response (forbidden).

    :param exception: the exception that was raised
    :return: json formatted response
    """
    return make_response(jsonify({"error": exception.description}), 403)


@bp.app_errorhandler(404)  # type: ignore
def not_found(exception: NotFound) -> Response:
    """404 error response (not found).

    :param exception: the exception that was raised
    :return: json formatted response
    """
    return make_response(jsonify({"error": exception.description}), 404)


@bp.app_errorhandler(500)  # type: ignore
def internal_server_error(exception: InternalServerError) -> Response:
    """500 error response (internal server error).

    :param exception: the exception that was raised
    :return: json formatted response
    """
    return make_response(jsonify({"error": exception.description}), 500)