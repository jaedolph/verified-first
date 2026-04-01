"""firsts.py."""

from dataclasses import dataclass
from datetime import datetime, UTC

from verifiedfirst.database import db


# pylint: disable=invalid-name
@dataclass
class First(db.Model):  # type: ignore
    """Database model to store "first" channel point redemptions."""

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String, nullable=False)
    timestamp: datetime = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    broadcaster_id: int = db.Column(db.Integer, nullable=False)
