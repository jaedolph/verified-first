"""Initialize the app."""
import logging
import sys
from typing import TypeVar

from flask import Flask
from flask_cors import CORS

from verifiedfirst.config import Config
from verifiedfirst.database import db

logging.basicConfig(
    stream=sys.stdout,
    format="%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s",
)


def create_app(config_class: type = Config) -> Flask:
    """Creates the verified first app.

    :param config_class: class to use for app configuration
    :return: initialized flask app
    """
    app = Flask(__name__)
    CORS(app)

    # validate and load config
    try:
        validate_config(config_class)
    except ValueError as exp:
        app.logger.error(exp)
        sys.exit(1)

    app.config.from_object(config_class)

    # set log level
    try:
        app.logger.setLevel(app.config["LOG_LEVEL"])
    except ValueError as exp:
        app.logger.error("error setting log level: %s", exp)
        sys.exit(1)

    # initialize database
    db.init_app(app)

    # import blueprints
    # pylint: disable=import-outside-toplevel
    import verifiedfirst.errors.handlers as error_handlers
    import verifiedfirst.main.routes as main_routes
    import verifiedfirst.auth.routes as auth_routes

    # pylint: disable=

    app.register_blueprint(error_handlers.bp)
    app.register_blueprint(main_routes.bp)
    app.register_blueprint(auth_routes.bp)

    return app


C = TypeVar("C", bound=Config)


def validate_config(config_class: type[C]) -> None:
    """Ensures config is correct.

    :param config_class: imported config class to validate
    :raises ValueError: if config is invalid
    """

    if not config_class.CLIENT_ID:
        raise ValueError(f"Missing env var {config_class.PREFIX}CLIENT_ID")

    if not config_class.CLIENT_SECRET:
        raise ValueError(f"Missing env var {config_class.PREFIX}CLIENT_SECRET")

    if not config_class.EXTENSION_SECRET:
        raise ValueError(f"Missing env var {config_class.PREFIX}EXTENSION_SECRET")

    if not config_class.REDIRECT_URI:
        raise ValueError(f"Missing env var {config_class.PREFIX}REDIRECT_URI")

    if not config_class.EVENTSUB_CALLBACK_URL:
        raise ValueError(f"Missing env var {config_class.PREFIX}EVENTSUB_CALLBACK_URL")

    if not config_class.EVENTSUB_SECRET:
        raise ValueError(f"Missing env var {config_class.PREFIX}EVENTSUB_SECRET")

    if not config_class.SQLALCHEMY_DATABASE_URI:
        raise ValueError(f"Missing env var {config_class.PREFIX}SQLALCHEMY_DATABASE_URI")
