from verifiedfirst.extensions import db
from verifiedfirst.web import app

if __name__ == "__main__":
    db.init_app(app)
    app.run(host="0.0.0.0")
