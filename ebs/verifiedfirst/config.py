import os


class Config:
    basedir = os.path.abspath(os.path.dirname(__file__))

    CLIENT_ID = os.environ.get("CLIENT_ID")
    CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
    EXTENSION_SECRET = os.environ.get("EXTENSION_SECRET")
    APP_ACCESS_TOKEN = os.environ.get("APP_ACCESS_TOKEN")
    REDIRECT_URI = os.environ.get("REDIRECT_URI")
    TWITCH_API_BASEURL = os.environ.get("TWITCH_API_BASEURL")
    EVENTSUB_CALLBACK_URL = os.environ.get("EVENTSUB_CALLBACK_URL")
    REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT"))
    EVENTSUB_SECRET = os.environ.get("EVENTSUB_SECRET")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "app.db")
