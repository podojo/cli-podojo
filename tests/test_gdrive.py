from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from podojo_cli.main import app


@pytest.fixture
def md_file(tmp_path):
    f = tmp_path / "report.md"
    f.write_text("# Hello\n\nSome content.")
    return f


@pytest.fixture
def credentials_file(tmp_path):
    f = tmp_path / "key.json"
    f.write_text('{"type": "service_account"}')
    return f


def test_setup_saves_credentials_path(runner, credentials_file, monkeypatch, tmp_path):
    config_path = tmp_path / ".podojo.toml"
    monkeypatch.setattr("podojo_cli.config.CONFIG_PATH", config_path)

    result = runner.invoke(app, ["gdrive", "setup", str(credentials_file)])

    assert result.exit_code == 0
    assert "Credentials saved" in result.output
    assert str(credentials_file) in config_path.read_text()


def test_setup_missing_file(runner):
    result = runner.invoke(app, ["gdrive", "setup", "/nonexistent/key.json"])

    assert result.exit_code == 1
    assert "File not found" in result.output


def test_upload_success(runner, md_file, monkeypatch, tmp_path):
    config_path = tmp_path / ".podojo.toml"
    config_path.write_text('gdrive_credentials = "/fake/key.json"\n')
    monkeypatch.setattr("podojo_cli.config.CONFIG_PATH", config_path)

    mock_upload = MagicMock(return_value=("doc-id-123", "https://docs.google.com/document/d/doc-id-123/edit"))
    with patch("podojo_cli.commands.gdrive.upload_md_as_doc", mock_upload):
        result = runner.invoke(app, ["gdrive", "upload", str(md_file)])

    assert result.exit_code == 0
    assert "https://docs.google.com/document/d/doc-id-123/edit" in result.output
    mock_upload.assert_called_once_with(str(md_file), "/fake/key.json", title=None, folder_id=None)


def test_upload_with_title_and_folder(runner, md_file, monkeypatch, tmp_path):
    config_path = tmp_path / ".podojo.toml"
    config_path.write_text('gdrive_credentials = "/fake/key.json"\n')
    monkeypatch.setattr("podojo_cli.config.CONFIG_PATH", config_path)

    mock_upload = MagicMock(return_value=("doc-id-456", "https://docs.google.com/document/d/doc-id-456/edit"))
    with patch("podojo_cli.commands.gdrive.upload_md_as_doc", mock_upload):
        result = runner.invoke(app, ["gdrive", "upload", str(md_file), "--title", "My Report", "--folder-id", "folder-abc"])

    assert result.exit_code == 0
    mock_upload.assert_called_once_with(str(md_file), "/fake/key.json", title="My Report", folder_id="folder-abc")


def test_upload_missing_file(runner, monkeypatch, tmp_path):
    config_path = tmp_path / ".podojo.toml"
    config_path.write_text('gdrive_credentials = "/fake/key.json"\n')
    monkeypatch.setattr("podojo_cli.config.CONFIG_PATH", config_path)

    result = runner.invoke(app, ["gdrive", "upload", "/nonexistent/report.md"])

    assert result.exit_code == 1
    assert "File not found" in result.output


def test_upload_no_credentials_configured(runner, md_file):
    result = runner.invoke(app, ["gdrive", "upload", str(md_file)])

    assert result.exit_code == 1
    assert "No credentials configured" in result.output
