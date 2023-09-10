"""broadcasters.py."""
from dataclasses import dataclass

from verifiedfirst.extensions import db


# pylint: disable=invalid-name
@dataclass
class Broadcaster(db.Model):  # type: ignore
    """Database model to store information about each channel/broadcaster."""

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String, nullable=False)
    access_token: str = db.Column(db.String, nullable=False)
    refresh_token: str = db.Column(db.String, nullable=False)
    reward_name: str = db.Column(db.String)
    reward_id: str = db.Column(db.String)
    eventsub_id: str = db.Column(db.String)
