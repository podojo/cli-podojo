from podojo_cli.main import app


def test_upload_interview(runner, httpx_mock, tmp_path):
    httpx_mock.add_response(
        method="POST",
        url="http://test.local/api/v1/projects/Alpha/interviews",
        json={
            "batch_id": "batch-xyz",
            "filename": "session_20260501120000.mp4",
            "project_name": "Alpha",
            "message": "File successfully uploaded",
        },
    )

    file_path = tmp_path / "session.mp4"
    file_path.write_bytes(b"fake video bytes")

    result = runner.invoke(app, ["interviews", "upload", str(file_path), "--project", "Alpha"])

    assert result.exit_code == 0
    assert "session.mp4" in result.output
    assert "batch-xyz" in result.output


def test_upload_interview_url_encodes_project(runner, httpx_mock, tmp_path):
    httpx_mock.add_response(
        method="POST",
        url="http://test.local/api/v1/projects/Acme%20Q4/interviews",
        json={
            "batch_id": "batch-1",
            "filename": "x.mp4",
            "project_name": "Acme Q4",
            "message": "ok",
        },
    )

    file_path = tmp_path / "x.mp4"
    file_path.write_bytes(b"data")

    result = runner.invoke(app, ["interviews", "upload", str(file_path), "--project", "Acme Q4"])

    assert result.exit_code == 0


def test_upload_interview_unknown_project(runner, httpx_mock, tmp_path):
    httpx_mock.add_response(
        method="POST",
        url="http://test.local/api/v1/projects/Ghost/interviews",
        status_code=404,
        json={"detail": "Project 'Ghost' not found"},
    )

    file_path = tmp_path / "session.mp4"
    file_path.write_bytes(b"fake")

    result = runner.invoke(app, ["interviews", "upload", str(file_path), "--project", "Ghost"])

    assert result.exit_code == 1
    assert "not found" in result.output
    assert "projects create" in result.output


def test_upload_interview_bad_extension(runner, httpx_mock, tmp_path):
    httpx_mock.add_response(
        method="POST",
        url="http://test.local/api/v1/projects/Alpha/interviews",
        status_code=400,
        json={"detail": "File type not allowed"},
    )

    file_path = tmp_path / "notes.txt"
    file_path.write_text("hello")

    result = runner.invoke(app, ["interviews", "upload", str(file_path), "--project", "Alpha"])

    assert result.exit_code == 1
    assert "File type not allowed" in result.output


def test_upload_interview_missing_file(runner, tmp_path):
    missing = tmp_path / "does-not-exist.mp4"

    result = runner.invoke(app, ["interviews", "upload", str(missing), "--project", "Alpha"])

    assert result.exit_code != 0


def test_label_interview(runner, httpx_mock):
    httpx_mock.add_response(
        method="PUT",
        url="http://test.local/api/v1/interviews/batch-xyz/quality",
        json={
            "batch_id": "batch-xyz",
            "quality_label": "review",
            "message": "Quality label saved",
        },
    )

    result = runner.invoke(
        app, ["interviews", "label", "batch-xyz", "--quality", "review"]
    )

    assert result.exit_code == 0
    assert "batch-xyz" in result.output
    assert "review" in result.output


def test_label_interview_not_found(runner, httpx_mock):
    httpx_mock.add_response(
        method="PUT",
        url="http://test.local/api/v1/interviews/ghost/quality",
        status_code=404,
        json={"detail": "Interview not found"},
    )

    result = runner.invoke(app, ["interviews", "label", "ghost", "--quality", "good"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_label_interview_invalid_quality(runner):
    result = runner.invoke(
        app, ["interviews", "label", "batch-xyz", "--quality", "bogus"]
    )

    assert result.exit_code != 0
