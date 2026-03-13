from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from podojo_cli.main import app
from podojo_cli.gdrive.upload import CREDENTIALS_FILENAME


@pytest.fixture
def md_file(tmp_path):
    f = tmp_path / "report.md"
    f.write_text("# Hello\n\nSome content.")
    return f


@pytest.fixture
def credentials_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / CREDENTIALS_FILENAME
    f.write_text('{"type": "service_account"}')
    return f


def test_upload_success(runner, md_file, credentials_file):
    mock_upload = MagicMock(return_value=("doc-id-123", "https://docs.google.com/document/d/doc-id-123/edit"))
    with patch("podojo_cli.commands.gdrive.upload_md_as_doc", mock_upload):
        result = runner.invoke(app, ["gdrive", "upload", str(md_file), "--folder-id", "folder-abc"])

    assert result.exit_code == 0
    assert "https://docs.google.com/document/d/doc-id-123/edit" in result.output
    mock_upload.assert_called_once_with(str(md_file), folder_id="folder-abc", title=None)


def test_upload_with_title(runner, md_file, credentials_file):
    mock_upload = MagicMock(return_value=("doc-id-456", "https://docs.google.com/document/d/doc-id-456/edit"))
    with patch("podojo_cli.commands.gdrive.upload_md_as_doc", mock_upload):
        result = runner.invoke(app, ["gdrive", "upload", str(md_file), "--folder-id", "folder-abc", "--title", "My Report"])

    assert result.exit_code == 0
    mock_upload.assert_called_once_with(str(md_file), folder_id="folder-abc", title="My Report")


def test_upload_missing_file(runner, credentials_file):
    result = runner.invoke(app, ["gdrive", "upload", "/nonexistent/report.md", "--folder-id", "folder-abc"])

    assert result.exit_code == 1
    assert "File not found" in result.output


def test_upload_no_credentials_file(runner, md_file, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["gdrive", "upload", str(md_file), "--folder-id", "folder-abc"])

    assert result.exit_code == 1
    assert CREDENTIALS_FILENAME in result.output


def test_list_success(runner, credentials_file):
    mock_files = [
        {"name": "Report A", "mimeType": "application/vnd.google-apps.document", "webViewLink": "https://docs.google.com/document/d/abc/edit"},
        {"name": "Report B", "mimeType": "application/vnd.google-apps.document", "webViewLink": "https://docs.google.com/document/d/xyz/edit"},
    ]
    mock_list = MagicMock(return_value=mock_files)
    with patch("podojo_cli.commands.gdrive.list_files", mock_list):
        result = runner.invoke(app, ["gdrive", "list", "--folder-id", "folder-abc"])

    assert result.exit_code == 0
    assert "Report A" in result.output
    assert "Report B" in result.output
    mock_list.assert_called_once_with(folder_id="folder-abc")


def test_list_no_credentials_file(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["gdrive", "list", "--folder-id", "folder-abc"])

    assert result.exit_code == 1
    assert CREDENTIALS_FILENAME in result.output
