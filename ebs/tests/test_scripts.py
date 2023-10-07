"""Integration tests for console scripts."""

import subprocess
import sys
import signal
import time
from threading import Timer

import requests

from verifiedfirst import create_app
from verifiedfirst.database import db
from verifiedfirst.models.broadcasters import Broadcaster
from verifiedfirst.models.firsts import First

from . import defaults

USERS = {
    "user1": 5,
    "user2": 3,
    "user3": 1,
}


def test_init_db(integrationtestconfig):
    """Test that the database can be loaded using the init_db.py script."""

    # run the init_db console script
    initdb = subprocess.run(
        [sys.executable, "verifiedfirst/init_db.py"],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    assert initdb.returncode == 0

    with create_app(integrationtestconfig).app_context():
        # check that a broadcaster can be created
        expected_broadcaster = Broadcaster(
            id=defaults.BROADCASTER_ID,
            name=defaults.BROADCASTER_NAME,
            access_token=defaults.AUTH_ACCESS_TOKEN,
            refresh_token=defaults.AUTH_REFRESH_TOKEN,
        )

        db.session.add(expected_broadcaster)
        db.session.commit()
        broadcaster = Broadcaster.query.filter(Broadcaster.id == defaults.BROADCASTER_ID).one()
        assert broadcaster.name == defaults.BROADCASTER_NAME
        assert broadcaster.id == defaults.BROADCASTER_ID
        assert broadcaster.access_token == defaults.AUTH_ACCESS_TOKEN
        assert broadcaster.refresh_token == defaults.AUTH_REFRESH_TOKEN

        # test that firsts can be added
        for user, count in USERS.items():
            for _ in range(0, count):
                first = First(broadcaster_id=defaults.BROADCASTER_ID, name=user)
                db.session.add(first)
                db.session.commit()


def test_main(integrationtestconfig, generate_jwt):  # pylint: disable=unused-argument
    """Test that the verifiedfirst web server can be run using the __main__.py script."""

    # # run the verifiedfirst web server
    with subprocess.Popen(
        [sys.executable, "verifiedfirst/__main__.py"], stdin=subprocess.PIPE, stderr=subprocess.PIPE
    ) as webserver:
        # add a kill timer in case the service hangs
        timer = Timer(5, webserver.kill)
        timer.start()

        # give the server some time to start up
        time.sleep(1)

        # test getting firsts
        headers = {
            "Authorization": "Bearer " + generate_jwt(),
        }
        resp = requests.get("http://localhost:5000/firsts", headers=headers, timeout=2)
        firsts = resp.json()

        assert resp.status_code == 200
        assert len(firsts.keys()) == 3
        assert firsts["user1"] == USERS["user1"]
        assert firsts["user2"] == USERS["user2"]
        assert firsts["user3"] == USERS["user3"]

        # close the webserver
        webserver.send_signal(signal.SIGINT)
        webserver.wait(1)
        timer.cancel()

        # ensure the webserver closed gracefully
        assert webserver.returncode == 0
