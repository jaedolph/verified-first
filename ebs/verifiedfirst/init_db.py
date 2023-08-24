from verifiedfirst.web import app
from verifiedfirst.extensions import db
from verifiedfirst.models.broadcasters import Broadcaster
from verifiedfirst.models.firsts import First


def main():
    with app.app_context():
        db.drop_all()
        db.create_all()

        for i in range(1, 5):
            first = First(broadcaster_id=25819608, name="user1")
            db.session.add(first)
            db.session.commit()
        for i in range(1, 2):
            first = First(broadcaster_id=25819608, name="user2")
            db.session.add(first)
            db.session.commit()
        for i in range(1, 3):
            first = First(broadcaster_id=25819608, name="user3")
            db.session.add(first)
            db.session.commit()
        for i in range(1, 2):
            first = First(broadcaster_id=25819608, name="user4")
            db.session.add(first)
            db.session.commit()


if __name__ == "__main__":
    main()
