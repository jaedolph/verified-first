# Verified First Leaderboard
Twitch extension to track who gets to your stream first.

## Development

### Lint the frontend

Install dependencies (one-time setup):

```bash
npm install
```

Run ESLint:

```bash
npx eslint *.js
```

### Run tox tests for EBS

```
tox -c ebs/tox.ini
```

### Run locally for manual testing

**1. Start the EBS**

Install dependencies into a virtualenv (one-time setup):

```bash
cd ebs
python -m venv .venv
source .venv/bin/activate
pip install gunicorn .
```

Create an `ebs/test.env` file with the required configuration:

```bash
VFIRST_CLIENT_ID=<your Twitch client ID>
VFIRST_CLIENT_SECRET=<your Twitch client secret>
VFIRST_EXTENSION_SECRET=<your extension secret (base64)>
VFIRST_REDIRECT_URI=<your OAuth redirect URI>
VFIRST_EVENTSUB_CALLBACK_URL=<your EventSub callback URL>
VFIRST_EVENTSUB_SECRET=<your EventSub secret>
VFIRST_SQLALCHEMY_DATABASE_URI=sqlite:///verifiedfirst.db
```

Load the env file and initialise the database (first time, or to reset it):

```bash
set -a && source test.env && set +a
python verifiedfirst/init_db.py
```

> **Warning:** `init_db.py` drops and recreates all tables, so any existing data will be lost.

Start the server:

```bash
gunicorn --bind 0.0.0.0:5000 "verifiedfirst:create_app()"
```

**2. Serve the frontend**

In a separate terminal, from the project root:

```bash
npx http-server . -p 8000
```
