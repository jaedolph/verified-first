import pytest
import os

os.environ['VFIRST_CLIENT_ID'] = 'abcdefghijklmnopqrstuvwxyz1234'
os.environ['VFIRST_CLIENT_SECRET'] = "1234567890qwertyuiopasdfghjkla"
os.environ['VFIRST_EXTENSION_SECRET'] = "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYQo="
os.environ['VFIRST_REDIRECT_URI'] = "https://twitch.hv1.jaedolph.net/auth"
os.environ['VFIRST_TWITCH_API_BASEURL'] = "https://api.twitch.tv/helix"
os.environ['VFIRST_EVENTSUB_CALLBACK_URL'] = "https://verifiedfirst.jaedolph.net/eventsub"
os.environ['VFIRST_REQUEST_TIMEOUT'] = "5"
os.environ['VFIRST_EVENTSUB_SECRET'] = "secret1234!"
os.environ['VFIRST_SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/app.db"


from verifiedfirst.verify import get_hmac

def test_get_hmac(mocker, mg):
    mock_config = mocker.patch('verifiedfirst.app_init.app.config')
    config = {
        "EVENTSUB_SECRET": "secret1234!",
        "DEBUG": False,
    }
    mock_config.__getitem__.side_effect = config.__getitem__
    hmac = get_hmac(b"test")
    assert hmac == "4b6915b3e283e23d92f775d37d7430a7729ee0f83bb8a0405fc717ddc7763b82"
