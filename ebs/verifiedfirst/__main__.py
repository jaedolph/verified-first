"""main.py."""
import verifiedfirst.web  # pylint: disable=unused-import
from verifiedfirst.app_init import app
from verifiedfirst.extensions import db

if __name__ == "__main__":
    db.init_app(app)
    app.run(host="0.0.0.0")
