import yaml

from podojo_cli.commands.aiinterviews import EXAMPLE_YAML
from podojo_cli.main import app


VALID_AI_INTERVIEW_YAML = """\
interview_id: test-interview-1
title: Test AI Interview
questions:
  - section: Intro
    text: Walk me through your last purchase.
    max_follow_ups: 3
    probe_for: Specific steps and pain points.
  - text: What would you improve?
closing_message: Thank you for your time!
"""

LIST_RESPONSE = {
    "ai_interviews": [
        {
            "id": "abc1",
            "interview_id": "ai-1",
            "title": "Interview One",
            "language": "en-US",
            "question_count": 3,
            "project_name": "proj-1",
            "live": True,
            "created_at": "2026-06-01T12:00:00",
            "created_by": "user@example.com",
            "last_updated": "2026-06-01T12:00:00",
        },
        {
            "id": "abc2",
            "interview_id": "ai-2",
            "title": "Interview Two",
            "language": "de-DE",
            "question_count": 5,
            "project_name": "proj-2",
            "live": False,
            "created_at": "2026-06-02T12:00:00",
            "created_by": "user@example.com",
            "last_updated": "2026-06-02T12:00:00",
        },
    ],
    "total": 2,
    "skip": 0,
    "limit": 50,
}

GET_RESPONSE = {
    "id": "abc123",
    "interview_id": "ai-1",
    "title": "Interview One",
    "language": "en-US",
    "project_name": "proj-1",
    "overview": "Study overview",
    "decision": "Improve the thing",
    "questions": [{"text": "Walk me through your last purchase.", "max_follow_ups": 2}],
    "closing_message": "Thanks!",
    "live": False,
    "group": "test-group",
    "created_at": "2026-06-01T12:00:00",
    "created_by": "user@example.com",
    "last_updated": "2026-06-01T12:00:00",
}


def test_list_ai_interviews(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/ai-interviews?skip=0&limit=50",
        json=LIST_RESPONSE,
    )

    result = runner.invoke(app, ["aiinterviews", "list"])

    assert result.exit_code == 0
    assert "Interview One" in result.output
    assert "Interview Two" in result.output


def test_list_ai_interviews_empty(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/ai-interviews?skip=0&limit=50",
        json={"ai_interviews": [], "total": 0, "skip": 0, "limit": 50},
    )

    result = runner.invoke(app, ["aiinterviews", "list"])

    assert result.exit_code == 0
    assert "No AI interviews found" in result.output


def test_get_ai_interview(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/ai-interviews/ai-1",
        json=GET_RESPONSE,
    )

    result = runner.invoke(app, ["aiinterviews", "get", "ai-1"])

    assert result.exit_code == 0
    assert "interview_id: ai-1" in result.output
    assert "title: Interview One" in result.output
    # Server-managed fields should be stripped
    assert "created_at" not in result.output
    assert "created_by" not in result.output
    assert "group: test-group" not in result.output
    # URLs should be displayed
    assert "http://interviews.test.local/preview/test-group/ai-1" in result.output
    assert "http://interviews.test.local/test-group/ai-1" in result.output


def test_get_ai_interview_not_found(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/ai-interviews/nonexistent",
        status_code=404,
        json={"detail": "AI interview not found"},
    )

    result = runner.invoke(app, ["aiinterviews", "get", "nonexistent"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_create_ai_interview(runner, httpx_mock, tmp_path):
    yaml_file = tmp_path / "interview.yaml"
    yaml_file.write_text(VALID_AI_INTERVIEW_YAML)

    httpx_mock.add_response(
        url="http://test.local/api/v1/ai-interviews",
        method="POST",
        json={
            "id": "abc123",
            "interview_id": "test-interview-1",
            "title": "Test AI Interview",
            "group": "test-group",
        },
    )

    result = runner.invoke(app, ["aiinterviews", "create", "-f", str(yaml_file)])

    assert result.exit_code == 0
    assert "test-interview-1" in result.output
    assert "http://interviews.test.local/preview/test-group/test-interview-1" in result.output
    assert "http://interviews.test.local/test-group/test-interview-1" in result.output


def test_create_ai_interview_file_not_found(runner):
    result = runner.invoke(app, ["aiinterviews", "create", "-f", "/nonexistent/interview.yaml"])

    assert result.exit_code == 1
    assert "File not found" in result.output


def test_create_ai_interview_invalid_yaml(runner, tmp_path):
    yaml_file = tmp_path / "bad.yaml"
    yaml_file.write_text(":\n  invalid: [yaml\n  broken")

    result = runner.invoke(app, ["aiinterviews", "create", "-f", str(yaml_file)])

    assert result.exit_code == 1
    assert "Invalid YAML" in result.output


def test_create_ai_interview_missing_fields(runner, tmp_path):
    yaml_file = tmp_path / "incomplete.yaml"
    yaml_file.write_text("title: Just a title\n")

    result = runner.invoke(app, ["aiinterviews", "create", "-f", str(yaml_file)])

    assert result.exit_code == 1
    assert "Missing required field" in result.output
    assert "'interview_id'" in result.output


def test_create_ai_interview_question_missing_text(runner, tmp_path):
    yaml_file = tmp_path / "badquestion.yaml"
    yaml_file.write_text(
        "interview_id: test\n"
        "title: Test\n"
        "closing_message: Thanks!\n"
        "questions:\n"
        "  - section: Intro\n"
    )

    result = runner.invoke(app, ["aiinterviews", "create", "-f", str(yaml_file)])

    assert result.exit_code == 1
    assert "Question 1: missing required field 'text'" in result.output


def test_create_ai_interview_invalid_max_follow_ups(runner, tmp_path):
    yaml_file = tmp_path / "badfollowups.yaml"
    yaml_file.write_text(
        "interview_id: test\n"
        "title: Test\n"
        "closing_message: Thanks!\n"
        "questions:\n"
        "  - text: A question\n"
        "    max_follow_ups: -1\n"
    )

    result = runner.invoke(app, ["aiinterviews", "create", "-f", str(yaml_file)])

    assert result.exit_code == 1
    assert "'max_follow_ups' must be an integer >= 0" in result.output


def test_create_ai_interview_duplicate(runner, httpx_mock, tmp_path):
    yaml_file = tmp_path / "interview.yaml"
    yaml_file.write_text(VALID_AI_INTERVIEW_YAML)

    httpx_mock.add_response(
        url="http://test.local/api/v1/ai-interviews",
        method="POST",
        status_code=409,
        json={"detail": "AI interview with this ID already exists"},
    )

    result = runner.invoke(app, ["aiinterviews", "create", "-f", str(yaml_file)])

    assert result.exit_code == 1
    assert "already exists" in result.output


def test_update_ai_interview(runner, httpx_mock, tmp_path):
    yaml_file = tmp_path / "update.yaml"
    yaml_file.write_text("title: Updated Title\n")

    httpx_mock.add_response(
        url="http://test.local/api/v1/ai-interviews/ai-1",
        method="PUT",
        json={"interview_id": "ai-1", "title": "Updated Title"},
    )

    result = runner.invoke(app, ["aiinterviews", "update", "ai-1", "-f", str(yaml_file)])

    assert result.exit_code == 0
    assert "Updated AI interview" in result.output


def test_update_ai_interview_not_found(runner, httpx_mock, tmp_path):
    yaml_file = tmp_path / "update.yaml"
    yaml_file.write_text("title: Updated Title\n")

    httpx_mock.add_response(
        url="http://test.local/api/v1/ai-interviews/nonexistent",
        method="PUT",
        status_code=404,
        json={"detail": "AI interview not found"},
    )

    result = runner.invoke(app, ["aiinterviews", "update", "nonexistent", "-f", str(yaml_file)])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_delete_ai_interview(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/ai-interviews/ai-1",
        method="DELETE",
        json={"status": "deleted", "interview_id": "ai-1"},
    )

    result = runner.invoke(app, ["aiinterviews", "delete", "ai-1", "--yes"])

    assert result.exit_code == 0
    assert "Deleted AI interview" in result.output


def test_delete_ai_interview_not_found(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/ai-interviews/nonexistent",
        method="DELETE",
        status_code=404,
        json={"detail": "AI interview not found"},
    )

    result = runner.invoke(app, ["aiinterviews", "delete", "nonexistent", "--yes"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_validate_valid(runner, tmp_path):
    yaml_file = tmp_path / "interview.yaml"
    yaml_file.write_text(VALID_AI_INTERVIEW_YAML)

    result = runner.invoke(app, ["aiinterviews", "validate", str(yaml_file)])

    assert result.exit_code == 0
    assert "Valid AI interview config" in result.output


def test_validate_invalid(runner, tmp_path):
    yaml_file = tmp_path / "bad.yaml"
    yaml_file.write_text("title: Just a title\n")

    result = runner.invoke(app, ["aiinterviews", "validate", str(yaml_file)])

    assert result.exit_code == 1
    assert "Missing required field" in result.output


SCREENING_YAML = VALID_AI_INTERVIEW_YAML + """\
screening_questions:
  - text: Do you currently drive for a ridehailing platform?
    options:
      - text: "Yes"
        qualifies: true
      - text: "No"
  - text: How many rides did you complete last month?
    options:
      - text: 0 rides
      - text: 1-10 rides
        qualifies: true
      - text: More than 10 rides
        qualifies: true
rejection_message: You did not meet the research criteria for this study.
"""


def test_validate_with_screening(runner, tmp_path):
    yaml_file = tmp_path / "interview.yaml"
    yaml_file.write_text(SCREENING_YAML)

    result = runner.invoke(app, ["aiinterviews", "validate", str(yaml_file)])

    assert result.exit_code == 0
    assert "Valid AI interview config" in result.output


def test_validate_screening_question_needs_two_options(runner, tmp_path):
    yaml_file = tmp_path / "interview.yaml"
    yaml_file.write_text(
        VALID_AI_INTERVIEW_YAML
        + "screening_questions:\n"
        + "  - text: Only one way to answer?\n"
        + "    options:\n"
        + "      - text: \"Yes\"\n"
        + "        qualifies: true\n"
    )

    result = runner.invoke(app, ["aiinterviews", "validate", str(yaml_file)])

    assert result.exit_code == 1
    assert "'options' must list at least 2 options" in result.output


def test_validate_screening_question_needs_a_qualifying_option(runner, tmp_path):
    yaml_file = tmp_path / "interview.yaml"
    yaml_file.write_text(
        VALID_AI_INTERVIEW_YAML
        + "screening_questions:\n"
        + "  - text: Nobody can pass this one\n"
        + "    options:\n"
        + "      - text: A\n"
        + "      - text: B\n"
    )

    result = runner.invoke(app, ["aiinterviews", "validate", str(yaml_file)])

    assert result.exit_code == 1
    assert "needs at least one option with 'qualifies: true'" in result.output


def test_validate_screening_option_qualifies_must_be_bool(runner, tmp_path):
    yaml_file = tmp_path / "interview.yaml"
    yaml_file.write_text(
        VALID_AI_INTERVIEW_YAML
        + "screening_questions:\n"
        + "  - text: Q\n"
        + "    options:\n"
        + "      - text: A\n"
        + "        qualifies: yep\n"
        + "      - text: B\n"
        + "        qualifies: true\n"
    )

    result = runner.invoke(app, ["aiinterviews", "validate", str(yaml_file)])

    assert result.exit_code == 1
    assert "'qualifies' must be true or false" in result.output


def test_example(runner):
    result = runner.invoke(app, ["aiinterviews", "example"])

    assert result.exit_code == 0
    assert "interview_id:" in result.output
    assert "questions:" in result.output
    assert "closing_message:" in result.output
    assert "max_follow_ups:" in result.output
    assert "screening_questions:" in result.output
    assert "rejection_message:" in result.output


def test_example_validates(runner, tmp_path):
    data = yaml.safe_load(EXAMPLE_YAML)
    assert isinstance(data, dict)

    yaml_file = tmp_path / "example.yaml"
    yaml_file.write_text(EXAMPLE_YAML)

    result = runner.invoke(app, ["aiinterviews", "validate", str(yaml_file)])

    assert result.exit_code == 0
    assert "Valid AI interview config" in result.output
