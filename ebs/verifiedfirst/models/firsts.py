"""firsts.py."""

from dataclasses import dataclass
from datetime import datetime, UTC
from typing import ClassVar, Optional

from verifiedfirst.database import db


# pylint: disable=invalid-name
@dataclass
class First(db.Model):  # type: ignore
    """Database model to store "first" channel point redemptions."""

    __allow_unmapped__ = True

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String, nullable=False)
    timestamp: datetime = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    broadcaster_id: int = db.Column(db.Integer, nullable=False)
    user_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("twitch_user.id"), nullable=True)
    user: ClassVar = db.relationship("User", foreign_keys="[First.user_id]")
