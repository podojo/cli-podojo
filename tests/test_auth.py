from unittest.mock import patch

from podojo_cli.main import app


def test_login_valid_key(runner, httpx_mock, tmp_path):
    httpx_mock.add_response(
        url="http://test.local/api/v1/projects?limit=1",
        status_code=200,
        json=[],
    )

    config_path = tmp_path / ".podojo.toml"
    with patch("podojo_cli.config.CONFIG_PATH", config_path):
        result = runner.invoke(app, ["auth", "login", "valid-key-abc"])

    assert result.exit_code == 0
    assert "Logged in successfully" in result.output
    assert 'api_key = "valid-key-abc"' in config_path.read_text()


def test_login_invalid_key(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/projects?limit=1",
        status_code=401,
    )

    result = runner.invoke(app, ["auth", "login", "bad-key"])

    assert result.exit_code != 0
    assert "Invalid API key" in result.output


def test_logout(runner, tmp_path):
    config_path = tmp_path / ".podojo.toml"
    config_path.write_text('api_key = "some-key"\n')

    with patch("podojo_cli.config.CONFIG_PATH", config_path):
        result = runner.invoke(app, ["auth", "logout"])

    assert result.exit_code == 0
    assert "api_key" not in config_path.read_text() if config_path.exists() else True
