"""Default values used for testing."""

MESSAGE_ID = "f929cb30-aa0f-4320-a630-351b23dff92a"
MESSAGE_TIMESTAMP = "2000-01-01T00:00:00.000Z"
MESSAGE_DATA = "test"
ROLE = "broadcaster"
# hmacs generated using the secret key "secret1234!"
# correct message hmac
MESSAGE_HMAC = "8afac673b554fc414e0740ea9edb567830e97f7465eb3c381023d04beb2f45e2"
# incorrect message hmac
MESSAGE_BAD_HMAC = "4b6915b3e283e23d92f775d37d7430a7729ee0f83bb8a0405fc717ddc7763b82"

AUTH_ACCESS_TOKEN = "ndwul0n9x8g6257uaei2pyczh22fz"
AUTH_REFRESH_TOKEN = "fi02f7fs1nbpsddfvb709r07y2xbonrk4w7zxjx5woutm568e"
AUTH_CODE = "88va56epq1t98c4km4lune8l4alzv"
AUTH_RESPONSE_JSON = {
    "access_token": AUTH_ACCESS_TOKEN,
    "expires_in": 14442,
    "id_token": (
        "eyJhbGciOiJSUzI1NisInR5cCI6IkpXVCIsImtpZCI6IjEifQ.eyJhdWQiOiJob2Y1Z3d4MHN1Nm9"
        "3Zm55czBueWFuOWM4N3pyNnQiLCJleHAiOjE2NDQ1MTg2NTEsImlhdCI6MTY0NDUxNzc1MSwiaXNz"
        "IjoiaHR0cHM6Ly9pZC50d2l0Y2gudHYvb2F1dGgyIiwic3ViIjoiNzEzOTM2NzMzIiwiZW1haWwiO"
        "iJzY290d2h0QGp1c3Rpbi50diIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlfQ.uMGOyvmiXHbdUAuQ4j5"
        "oExRIO3PyrM7fbhSkbT8r1tIQi5DKlS705oRiQOUGz2_j4yUWIx4zlvYWDbgLWpYS2VtSuXXBb2Gb"
        "mnCR2kG2PKxbfnY9j4F2RkQfwhYnlz0PToxpoqm_NMEIX3ROzaKs6ixgNQyDRkLS8ik39rEoAy1pE"
        "AVwbEj7-NrOYKfvm_W-RCt0Q1ppqHqhSY94jIJ38dYiT47d84c36bY5WBTs7hZniP9vIyDqFel6WO"
        "5zWOCCa-qCRS7NMc6TZNVU-2VLTQFL0ABoLSP-E6Y_i4KTp-6NyWHUBXJYoMJekrIQW8_zM-ptskn"
        "53--3HMtKCKuhiA"
    ),
    "refresh_token": AUTH_REFRESH_TOKEN,
    "scope": [
        "channel:read:redemptions",
    ],
    "token_type": "bearer",
}
AUTH_URL = "https://id.twitch.tv/oauth2/token"
BROADCASTER_NAME = "twitchdev"
BROADCASTER_ID = 141981764
CHANNEL_ID = BROADCASTER_ID
EVENTSUB_ID = "26b1c993-bfcf-44d9-b876-379dacafe75a"
REWARD_ID = "536b13c5-8f49-49b9-81e1-18e52b028919"
TEST_USER_NAME = "testuser"
TEST_USER_ID = 11223344
EVENTSUB_JSON = {
    "total": 1,
    "data": [
        {
            "id": EVENTSUB_ID,
            "status": "enabled",
            "type": "channel.channel_points_custom_reward_redemption.add",
            "version": "1",
            "condition": {
                "broadcaster_user_id": str(BROADCASTER_ID),
                "reward_id": REWARD_ID,
            },
            "created_at": "2023-09-22T12:13:50.019162515Z",
            "transport": {
                "method": "webhook",
                "callback": "https://verifiedfirst.jaedolph.net/eventsub",
            },
            "cost": 0,
        }
    ],
    "total_cost": 0,
    "max_total_cost": 10000,
    "pagination": {},
}

CHALLENGE = "pogchamp-kappa-360noscope-vohiyo"
EVENTSUB_CHALLENGE_JSON = {
    "challenge": CHALLENGE,
    "subscription": {
        "id": EVENTSUB_ID,
        "status": "webhook_callback_verification_pending",
        "type": "channel.channel_points_custom_reward_redemption.add",
        "version": "1",
        "cost": 0,
        "condition": {
            "broadcaster_user_id": str(BROADCASTER_ID),
            "reward_id": REWARD_ID,
        },
        "transport": {
            "method": "webhook",
            "callback": "https://verifiedfirst.jaedolph.net/eventsub",
        },
        "created_at": "2023-09-22T12:13:50.019162515Z",
    },
}

EVENTSUB_NOTIFICATION_JSON = {
    "subscription": {
        "id": EVENTSUB_ID,
        "status": "enabled",
        "type": "channel.channel_points_custom_reward_redemption.add",
        "version": "1",
        "condition": {
            "broadcaster_user_id": str(BROADCASTER_ID),
            "reward_id": REWARD_ID,
        },
        "transport": {
            "method": "webhook",
            "callback": "https://verifiedfirst-test.jaedolph.net/eventsub",
        },
        "created_at": "2023-10-05T10:37:16.223825195Z",
        "cost": 0,
    },
    "event": {
        "broadcaster_user_id": str(BROADCASTER_ID),
        "broadcaster_user_login": "testbroadcaster",
        "broadcaster_user_name": "testbroadcaster",
        "id": "d3979e74-c857-4956-ae56-ce77d08e70a7",
        "user_id": TEST_USER_ID,
        "user_login": TEST_USER_NAME,
        "user_name": TEST_USER_NAME,
        "user_input": "",
        "status": "fulfilled",
        "redeemed_at": "2023-10-05T10:38:17.44291232Z",
        "reward": {
            "id": REWARD_ID,
            "title": "First Testing",
            "prompt": "",
            "cost": 1,
        },
    },
}


EVENTSUB_REVOCATION_JSON = {
    "subscription": {
        "id": EVENTSUB_ID,
        "status": "authorization_revoked",
        "type": "channel.channel_points_custom_reward_redemption.add",
        "version": "1",
        "cost": 0,
        "condition": {
            "broadcaster_user_id": str(BROADCASTER_ID),
            "reward_id": REWARD_ID,
        },
        "transport": {
            "method": "webhook",
            "callback": "https://verifiedfirst.jaedolph.net/eventsub",
        },
        "created_at": "2023-09-22T12:13:50.019162515Z",
    }
}

REWARDS_JSON = {
    "data": [
        {
            "broadcaster_name": BROADCASTER_NAME,
            "broadcaster_login": BROADCASTER_NAME,
            "broadcaster_id": BROADCASTER_ID,
            "id": "92af127c-7326-4483-a52b-b0da0be61c01",
            "image": None,
            "background_color": "#00E5CB",
            "is_enabled": True,
            "cost": 50000,
            "title": "game analysis",
            "prompt": "",
            "is_user_input_required": False,
            "max_per_stream_setting": {"is_enabled": False, "max_per_stream": 0},
            "max_per_user_per_stream_setting": {
                "is_enabled": False,
                "max_per_user_per_stream": 0,
            },
            "global_cooldown_setting": {"is_enabled": False, "global_cooldown_seconds": 0},
            "is_paused": False,
            "is_in_stock": True,
            "default_image": {
                "url_1x": "https://static-cdn.jtvnw.net/custom-reward-images/default-1.png",
                "url_2x": "https://static-cdn.jtvnw.net/custom-reward-images/default-2.png",
                "url_4x": "https://static-cdn.jtvnw.net/custom-reward-images/default-4.png",
            },
            "should_redemptions_skip_request_queue": False,
            "redemptions_redeemed_current_stream": None,
            "cooldown_expires_at": None,
        },
        {
            "broadcaster_name": BROADCASTER_NAME,
            "broadcaster_login": BROADCASTER_NAME,
            "broadcaster_id": BROADCASTER_ID,
            "id": "536b13c5-8f49-49b9-81e1-18e52b028919",
            "image": None,
            "background_color": "#00E5CB",
            "is_enabled": True,
            "cost": 1,
            "title": "first",
            "prompt": "",
            "is_user_input_required": False,
            "max_per_stream_setting": {"is_enabled": True, "max_per_stream": 1},
            "max_per_user_per_stream_setting": {
                "is_enabled": False,
                "max_per_user_per_stream": 0,
            },
            "global_cooldown_setting": {"is_enabled": False, "global_cooldown_seconds": 0},
            "is_paused": False,
            "is_in_stock": True,
            "default_image": {
                "url_1x": "https://static-cdn.jtvnw.net/custom-reward-images/default-1.png",
                "url_2x": "https://static-cdn.jtvnw.net/custom-reward-images/default-2.png",
                "url_4x": "https://static-cdn.jtvnw.net/custom-reward-images/default-4.png",
            },
            "should_redemptions_skip_request_queue": False,
            "redemptions_redeemed_current_stream": None,
            "cooldown_expires_at": None,
        },
    ]
}
