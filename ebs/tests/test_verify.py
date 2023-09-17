"""test_verify.py"""
import pytest # pylint: disable=unused-import

from verifiedfirst import verify

# some mock values for testing
MESSAGE_ID = "f929cb30-aa0f-4320-a630-351b23dff92a"
MESSAGE_TIMESTAMP = "2000-01-01T00:00:00.000Z"
MESSAGE_DATA = "test"
# hmacs generated using the secret key "secret1234!"
# correct message hmac
MESSAGE_HMAC = "8afac673b554fc414e0740ea9edb567830e97f7465eb3c381023d04beb2f45e2"
# incorrect message hmac
MESSAGE_BAD_HMAC = "4b6915b3e283e23d92f775d37d7430a7729ee0f83bb8a0405fc717ddc7763b82"


def test_get_hmac(app, mocker): # pylint: disable=unused-argument
    """Test the get_hmac function generates a correct hmac
    """

    message = (MESSAGE_ID + MESSAGE_TIMESTAMP + MESSAGE_DATA).encode("utf-8")
    hmac = verify.get_hmac(message)
    assert hmac == MESSAGE_HMAC


def test_verify_eventsub_message(app, mocker): # pylint: disable=unused-argument
    """Test the verify_eventsub_message function
    """

    mock_request = mocker.Mock()
    mock_get_hmac = mocker.patch("verifiedfirst.verify.get_hmac")

    mock_get_hmac.return_value = MESSAGE_HMAC

    headers = {
        "Twitch-Eventsub-Message-Id": MESSAGE_ID,
        "Twitch-Eventsub-Message-Timestamp": MESSAGE_TIMESTAMP,
        "Twitch-Eventsub-Message-Signature": "sha256=" + MESSAGE_HMAC,
    }
    mock_request.headers = headers
    mock_request.data = MESSAGE_DATA.encode("utf-8")

    # test that verification works on good signature
    verified = verify.verify_eventsub_message(mock_request)
    assert verified

    # test that verification fails when the hmac function throws an exception
    mock_get_hmac.side_effect = TypeError("Strings must be encoded before hashing")
    verified = verify.verify_eventsub_message(mock_request)
    assert not verified

    mock_get_hmac.reset_mock(return_value=False, side_effect=True)
    # test that verification fails when the signature is incorrect
    headers["Twitch-Eventsub-Message-Signature"] = "sha256=" + MESSAGE_BAD_HMAC
    mock_request.headers = headers
    verified = verify.verify_eventsub_message(mock_request)
    assert not verified
