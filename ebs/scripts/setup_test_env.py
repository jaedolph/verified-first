from datetime import datetime

from verifiedfirst import create_app, db, twitch
from verifiedfirst.models.firsts import First
from verifiedfirst.models.broadcasters import Broadcaster

BROADCASTER_ID = "15991044"

with create_app().app_context():

    broadcaster = Broadcaster(
        id=BROADCASTER_ID,
        name="davekomodohype961",
        access_token="ndwul0n9x8g6257uaei2pyczh22fz",
        refresh_token="fi02f7fs1nbpsddfvb709r07y2xbonrk4w7zxjx5woutm568e",
    )

    print(broadcaster)
    db.session.add(broadcaster)
    db.session.commit()

    first_entry = First(broadcaster_id=broadcaster.id, name="liondeveloper306", timestamp=datetime(2023, 12, 15))
    db.session.add(first_entry)
    db.session.commit()
