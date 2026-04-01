from datetime import datetime

from verifiedfirst import create_app, db, twitch
from verifiedfirst.models.firsts import First

BROADCASTER_ID = "25819608"

with create_app().app_context():
    broadcaster = twitch.get_broadcaster(BROADCASTER_ID)

    #First(broadcaster_id=broadcaster.id, name="test1", timestamp=datetime(2023, 12, 15))
    db.session.add(First(broadcaster_id=broadcaster.id, name="test1"))
    db.session.add(First(broadcaster_id=broadcaster.id, name="test1"))
    db.session.add(First(broadcaster_id=broadcaster.id, name="test2"))
    db.session.add(First(broadcaster_id=broadcaster.id, name="test3"))


    db.session.commit()
