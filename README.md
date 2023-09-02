# Verified First
Twitch extension to track who gets to your stream first


## Testing frontend
```
npm install http-server
node_modules/http-server/bin/http-server --cors=*
```

## Testing backend

Create .env file, use ebs/env.example as and example.

Create virtual env, and install:
```
python3 -m venv ebs/venv
source ebs/venv/bin/activate
pip3 install -e .
```

Initialise database:
```
source my_values.env
python3 ebs/verifiedfirst/init_db.py
```

Start webserver:
```
python3 verifiedfirst
```
