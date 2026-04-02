"""users.py."""

from dataclasses import dataclass
from datetime import datetime, UTC

from verifiedfirst.database import db


# pylint: disable=invalid-name
@dataclass
class User(db.Model):  # type: ignore
    """Database model to cache Twitch user information."""

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String, nullable=False)
    last_seen: datetime = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
