# Verified First Leaderboard
Twitch extension to track who gets to your stream first.

## Configuring the extension for your stream

1. Create a new channel points reward called "First" (or something similar). Set the cost to 1
   point. Tick "Cooldown & Limits" and set "Limit Redemptions Per Stream" to 1 so that only one
   viewer can claim it per stream.

2. Install the "Verified First Leaderboard" extension.

4. Click the gear icon to configure the extension.

5. Click the "Connect to twitch" button to allow the extension to view your channel point rewards.

6. Select your "First" reward from the drop down menu and click "Submit".


## Development

Run tox tests for EBS:
```
tox -c ebs/tox.ini
```