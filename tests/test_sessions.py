from podojo_cli.main import app


VALID_SESSION_YAML = """\
session_id: test-session-1
client: Test Corp
title: Test Session
logo: https://example.com/logo.png
prototype_url: https://example.com/proto
steps:
  - type: screen
    variant: question
    title: First Question
    text: What do you see?
  - type: prototype
    title: Try the Flow
"""

LIST_RESPONSE = {
    "sessions": [
        {
            "session_id": "sess-1",
            "title": "Session One",
            "client": "Acme",
            "step_count": 3,
            "last_updated": "2026-03-01T12:00:00",
        },
        {
            "session_id": "sess-2",
            "title": "Session Two",
            "client": "Beta",
            "step_count": 5,
            "last_updated": "2026-03-02T12:00:00",
        },
    ],
    "total": 2,
}

GET_RESPONSE = {
    "id": "abc123",
    "session_id": "sess-1",
    "title": "Session One",
    "client": "Acme",
    "logo": "https://example.com/logo.png",
    "prototype_url": "https://example.com/proto",
    "steps": [{"type": "screen", "variant": "question", "title": "Q1"}],
    "created_at": "2026-03-01T12:00:00",
    "created_by": "user@example.com",
    "last_updated": "2026-03-01T12:00:00",
}


def test_list_sessions(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/sessions?skip=0&limit=50",
        json=LIST_RESPONSE,
    )

    result = runner.invoke(app, ["sessions", "list"])

    assert result.exit_code == 0
    assert "Session One" in result.output
    assert "Session Two" in result.output
    assert "Acme" in result.output


def test_list_sessions_empty(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/sessions?skip=0&limit=50",
        json={"sessions": [], "total": 0},
    )

    result = runner.invoke(app, ["sessions", "list"])

    assert result.exit_code == 0
    assert "No sessions found" in result.output


def test_get_session(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/sessions/sess-1",
        json=GET_RESPONSE,
    )

    result = runner.invoke(app, ["sessions", "get", "sess-1"])

    assert result.exit_code == 0
    assert "session_id: sess-1" in result.output
    assert "title: Session One" in result.output
    # Server-managed fields should be stripped
    assert "created_at" not in result.output
    assert "created_by" not in result.output


def test_get_session_not_found(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/sessions/nonexistent",
        status_code=404,
        json={"detail": "Session not found"},
    )

    result = runner.invoke(app, ["sessions", "get", "nonexistent"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_create_session(runner, httpx_mock, tmp_path):
    yaml_file = tmp_path / "session.yaml"
    yaml_file.write_text(VALID_SESSION_YAML)

    httpx_mock.add_response(
        url="http://test.local/api/v1/sessions",
        method="POST",
        json={"session_id": "test-session-1", "id": "abc123"},
    )

    result = runner.invoke(app, ["sessions", "create", "-f", str(yaml_file)])

    assert result.exit_code == 0
    assert "test-session-1" in result.output


def test_create_session_file_not_found(runner):
    result = runner.invoke(app, ["sessions", "create", "-f", "/nonexistent/session.yaml"])

    assert result.exit_code == 1
    assert "File not found" in result.output


def test_create_session_invalid_yaml(runner, tmp_path):
    yaml_file = tmp_path / "bad.yaml"
    yaml_file.write_text(":\n  invalid: [yaml\n  broken")

    result = runner.invoke(app, ["sessions", "create", "-f", str(yaml_file)])

    assert result.exit_code == 1
    assert "Invalid YAML" in result.output


def test_create_session_missing_fields(runner, tmp_path):
    yaml_file = tmp_path / "incomplete.yaml"
    yaml_file.write_text("title: Just a title\n")

    result = runner.invoke(app, ["sessions", "create", "-f", str(yaml_file)])

    assert result.exit_code == 1
    assert "Missing required field" in result.output
    assert "'session_id'" in result.output


def test_create_session_invalid_step_type(runner, tmp_path):
    yaml_file = tmp_path / "badstep.yaml"
    yaml_file.write_text(
        "session_id: test\n"
        "client: Test\n"
        "title: Test\n"
        "logo: https://example.com/logo.png\n"
        "prototype_url: https://example.com/proto\n"
        "steps:\n"
        "  - type: invalid\n"
        "    title: Bad Step\n"
    )

    result = runner.invoke(app, ["sessions", "create", "-f", str(yaml_file)])

    assert result.exit_code == 1
    assert "'type' must be 'screen' or 'prototype'" in result.output


def test_create_session_duplicate(runner, httpx_mock, tmp_path):
    yaml_file = tmp_path / "session.yaml"
    yaml_file.write_text(VALID_SESSION_YAML)

    httpx_mock.add_response(
        url="http://test.local/api/v1/sessions",
        method="POST",
        status_code=409,
        json={"detail": "Session with this ID already exists"},
    )

    result = runner.invoke(app, ["sessions", "create", "-f", str(yaml_file)])

    assert result.exit_code == 1
    assert "already exists" in result.output


def test_update_session(runner, httpx_mock, tmp_path):
    yaml_file = tmp_path / "update.yaml"
    yaml_file.write_text("title: Updated Title\n")

    httpx_mock.add_response(
        url="http://test.local/api/v1/sessions/sess-1",
        method="PUT",
        json={"session_id": "sess-1", "title": "Updated Title"},
    )

    result = runner.invoke(app, ["sessions", "update", "sess-1", "-f", str(yaml_file)])

    assert result.exit_code == 0
    assert "Updated session" in result.output


def test_update_session_not_found(runner, httpx_mock, tmp_path):
    yaml_file = tmp_path / "update.yaml"
    yaml_file.write_text("title: Updated Title\n")

    httpx_mock.add_response(
        url="http://test.local/api/v1/sessions/nonexistent",
        method="PUT",
        status_code=404,
        json={"detail": "Session not found"},
    )

    result = runner.invoke(app, ["sessions", "update", "nonexistent", "-f", str(yaml_file)])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_delete_session(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/sessions/sess-1",
        method="DELETE",
        json={"status": "deleted", "session_id": "sess-1"},
    )

    result = runner.invoke(app, ["sessions", "delete", "sess-1", "--yes"])

    assert result.exit_code == 0
    assert "Deleted session" in result.output


def test_delete_session_not_found(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/sessions/nonexistent",
        method="DELETE",
        status_code=404,
        json={"detail": "Session not found"},
    )

    result = runner.invoke(app, ["sessions", "delete", "nonexistent", "--yes"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_validate_valid(runner, tmp_path):
    yaml_file = tmp_path / "session.yaml"
    yaml_file.write_text(VALID_SESSION_YAML)

    result = runner.invoke(app, ["sessions", "validate", str(yaml_file)])

    assert result.exit_code == 0
    assert "Valid session config" in result.output


def test_validate_invalid(runner, tmp_path):
    yaml_file = tmp_path / "bad.yaml"
    yaml_file.write_text("title: Just a title\n")

    result = runner.invoke(app, ["sessions", "validate", str(yaml_file)])

    assert result.exit_code == 1
    assert "Missing required field" in result.output


def test_example(runner):
    result = runner.invoke(app, ["sessions", "example"])

    assert result.exit_code == 0
    assert "session_id:" in result.output
    assert "steps:" in result.output
    assert "prototype" in result.output
    assert "screen" in result.output
