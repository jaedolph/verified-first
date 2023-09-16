"""init_db.py."""

from verifiedfirst.extensions import db
from verifiedfirst.app_init import app


def main() -> None:
    """Initializes the database."""
    with app.app_context():
        db.drop_all()
        db.create_all()


if __name__ == "__main__":
    main()
