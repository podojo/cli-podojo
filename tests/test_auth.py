from unittest.mock import patch

from podojo_cli.config import KEYRING_SERVICE, KEYRING_USERNAME
from podojo_cli.main import app


def test_login_valid_key(runner, httpx_mock, mock_keyring):
    httpx_mock.add_response(
        url="http://test.local/api/v1/projects?limit=1",
        status_code=200,
        json=[],
    )

    result = runner.invoke(app, ["auth", "login", "--key", "valid-key-abc"])

    assert result.exit_code == 0
    assert "Logged in successfully" in result.output
    assert mock_keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME) == "valid-key-abc"


def test_login_prompted(runner, httpx_mock, mock_keyring):
    httpx_mock.add_response(
        url="http://test.local/api/v1/projects?limit=1",
        status_code=200,
        json=[],
    )

    result = runner.invoke(app, ["auth", "login"], input="prompted-key\n")

    assert result.exit_code == 0
    assert "Logged in successfully" in result.output
    assert mock_keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME) == "prompted-key"


def test_login_invalid_key(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/projects?limit=1",
        status_code=401,
    )

    result = runner.invoke(app, ["auth", "login", "--key", "bad-key"])

    assert result.exit_code != 0
    assert "Invalid API key" in result.output


def test_logout(runner, mock_keyring):
    mock_keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, "some-key")

    result = runner.invoke(app, ["auth", "logout"])

    assert result.exit_code == 0
    assert mock_keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME) is None
