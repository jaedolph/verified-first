from verifiedfirst.extensions import db
from dataclasses import dataclass
from datetime import datetime


@dataclass
class First(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String, nullable=False)
    timestamp: datetime = db.Column(db.DateTime, default=datetime.utcnow)
    broadcaster_id: int = db.Column(db.Integer, nullable=False)
