from dataclasses import dataclass

from verifiedfirst.extensions import db

#pylint: disable=invalid-name
@dataclass
class Broadcaster(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String, nullable=False)
    access_token: str = db.Column(db.String, nullable=False)
    refresh_token: str = db.Column(db.String, nullable=False)
    reward_name: str = db.Column(db.String)
    reward_id: int = db.Column(db.Integer)
    eventsub_id: int = db.Column(db.Integer)
