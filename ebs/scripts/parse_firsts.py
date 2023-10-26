"""Used to import firsts from a csv."""
import csv
from datetime import datetime

import requests
from flask import current_app
from requests import Request

from verifiedfirst import create_app, db, twitch
from verifiedfirst.models.firsts import First

BROADCASTER_ID = "12345678"
CSV_FILE = "/tmp/firsts.csv"


def check_user(broadcaster, display_name):
    username = display_name.strip().lower()
    req = Request(
        method="GET",
        url=f"{current_app.config['TWITCH_API_BASEURL']}/users",
        headers={"Client-ID": current_app.config["CLIENT_ID"]},
        params={
            "login": str(username),
        },
    )

    resp = requests.get(
        "https://api.twitch.tv/helix/users",
        params={
            "login": username,
        },
        timeout=5,
        headers={
            "Client-Id": current_app.config["CLIENT_ID"],
        },
    )
    resp = twitch.request_twitch_api_broadcaster(broadcaster, req)
    resp.raise_for_status()
    try:
        user = resp.json()["data"][0]["login"]
        print(f"{user} is valid")
    except IndexError:
        print(f"user {username} not found")
        user = username

    return user


def main():
    firsts = []
    with create_app().app_context():
        broadcaster = twitch.get_broadcaster(BROADCASTER_ID)
        with open(CSV_FILE, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            months = reader.fieldnames[1:]
            for row in reader:
                username = check_user(broadcaster, row["Name"])
                for month in months:
                    date = datetime.strptime(month, "%b %y")
                    count = row[month]
                    if count == "":
                        count = 0
                    for _ in range(0, int(count)):
                        firsts.append((username, date))
        for first in firsts:
            name = first[0]
            date = first[1]
            print(name, date)
            first_entry = First(broadcaster_id=broadcaster.id, name=name, timestamp=date)
            db.session.add(first_entry)
            db.session.commit()


if __name__ == "__main__":
    main()
