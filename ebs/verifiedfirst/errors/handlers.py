"""Error handlers."""
from typing import cast

from flask import Blueprint, Response, jsonify
from werkzeug.exceptions import BadRequest, Forbidden, InternalServerError, NotFound, Unauthorized

bp = Blueprint("errors", __name__)


@bp.app_errorhandler(400)  # type: ignore
def bad_request(exception: BadRequest) -> Response:
    """400 error response (bad request).

    :param exception: the exception that was raised
    :return: json formatted response
    """
    response = jsonify({"error": exception.description})
    response.status_code = 400
    return cast(Response, response)


@bp.app_errorhandler(401)  # type: ignore
def unauthorized(exception: Unauthorized) -> Response:
    """401 error response (unauthorized).

    :param exception: the exception that was raised
    :return: json formatted response
    """
    response = jsonify({"error": exception.description})
    response.status_code = 401
    return cast(Response, response)


@bp.app_errorhandler(403)  # type: ignore
def forbidden(exception: Forbidden) -> Response:
    """403 error response (forbidden).

    :param exception: the exception that was raised
    :return: json formatted response
    """
    response = jsonify({"error": exception.description})
    response.status_code = 403
    return cast(Response, response)


@bp.app_errorhandler(404)  # type: ignore
def not_found(exception: NotFound) -> Response:
    """404 error response (not found).

    :param exception: the exception that was raised
    :return: json formatted response
    """
    response = jsonify({"error": exception.description})
    response.status_code = 404
    return cast(Response, response)


@bp.app_errorhandler(500)  # type: ignore
def internal_server_error(exception: InternalServerError) -> Response:
    """500 error response (internal server error).

    :param exception: the exception that was raised
    :return: json formatted response
    """
    response = jsonify({"error": exception.description})
    response.status_code = 500
    return cast(Response, response)
