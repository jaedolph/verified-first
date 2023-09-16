"""app_init.py."""
import logging

from flask import Flask
from flask_cors import CORS

from verifiedfirst.config import Config

app = Flask(__name__)
CORS(app)
app.config.from_object(Config)

logging.basicConfig(
    filename="record.log",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s",
)
