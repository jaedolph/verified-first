"""Perform initial load of the database."""

from flask import current_app
from verifiedfirst.database import db


def main() -> None:
    """Initializes the database."""
    with current_app.app_context():
        db.drop_all()
        db.create_all()


if __name__ == "__main__":
    main()
