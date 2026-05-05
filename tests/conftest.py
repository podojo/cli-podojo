from pathlib import Path

import keyring
import pytest
from typer.testing import CliRunner

from podojo_cli.main import app


class InMemoryKeyring(keyring.backend.KeyringBackend):
    priority = 10

    def __init__(self):
        self._store = {}

    def set_password(self, service, username, password):
        self._store[(service, username)] = password

    def get_password(self, service, username):
        return self._store.get((service, username))

    def delete_password(self, service, username):
        try:
            del self._store[(service, username)]
        except KeyError:
            raise keyring.errors.PasswordDeleteError()


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_keyring():
    backend = InMemoryKeyring()
    keyring.set_keyring(backend)
    return backend


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    monkeypatch.setenv("PODOJO_BASE_URL", "http://test.local")
    monkeypatch.setenv("PODOJO_API_KEY", "test-key")
    monkeypatch.setattr("podojo_cli.config.CONFIG_PATH", Path("/nonexistent/.podojo.toml"))


@pytest.fixture(autouse=True)
def disable_version_check(monkeypatch):
    monkeypatch.setattr("podojo_cli.main.check_for_update", lambda: None)
