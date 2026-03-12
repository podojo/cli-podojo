from pathlib import Path

import pytest
from typer.testing import CliRunner

from podojo_cli.main import app


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    monkeypatch.setenv("PODOJO_BASE_URL", "http://test.local")
    monkeypatch.setenv("PODOJO_API_KEY", "test-key")
    monkeypatch.setattr("podojo_cli.config.CONFIG_PATH", Path("/nonexistent/.podojo.toml"))
