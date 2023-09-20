"""Perform initial load of the database."""

from verifiedfirst import create_app
from verifiedfirst.database import db


def main() -> None:
    """Initializes the database."""
    with create_app().app_context():
        db.drop_all()
        db.create_all()


if __name__ == "__main__":
    main()
