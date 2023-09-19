"""firsts.py."""
from dataclasses import dataclass
from datetime import datetime

from verifiedfirst.database import db


# pylint: disable=invalid-name
@dataclass
class First(db.Model):  # type: ignore
    """Database model to store "first" channel point redemptions."""

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String, nullable=False)
    timestamp: datetime = db.Column(db.DateTime, default=datetime.utcnow)
    broadcaster_id: int = db.Column(db.Integer, nullable=False)
