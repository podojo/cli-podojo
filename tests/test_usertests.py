from podojo_cli.main import app


VALID_USERTEST_YAML = """\
usertest_id: test-usertest-1
client: Test Corp
title: Test User Test
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
    "usertests": [
        {
            "usertest_id": "ut-1",
            "title": "User Test One",
            "client": "Acme",
            "step_count": 3,
            "live": True,
            "last_updated": "2026-03-01T12:00:00",
        },
        {
            "usertest_id": "ut-2",
            "title": "User Test Two",
            "client": "Beta",
            "step_count": 5,
            "live": False,
            "last_updated": "2026-03-02T12:00:00",
        },
    ],
    "total": 2,
}

GET_RESPONSE = {
    "id": "abc123",
    "usertest_id": "ut-1",
    "title": "User Test One",
    "client": "Acme",
    "logo": "https://example.com/logo.png",
    "prototype_url": "https://example.com/proto",
    "steps": [{"type": "screen", "variant": "question", "title": "Q1"}],
    "group": "test-group",
    "created_at": "2026-03-01T12:00:00",
    "created_by": "user@example.com",
    "last_updated": "2026-03-01T12:00:00",
}


def test_list_usertests(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/usertests?skip=0&limit=50",
        json=LIST_RESPONSE,
    )

    result = runner.invoke(app, ["usertests", "list"])

    assert result.exit_code == 0
    assert "User Test One" in result.output
    assert "User Test Two" in result.output


def test_list_usertests_empty(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/usertests?skip=0&limit=50",
        json={"usertests": [], "total": 0},
    )

    result = runner.invoke(app, ["usertests", "list"])

    assert result.exit_code == 0
    assert "No user tests found" in result.output


def test_get_usertest(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/usertests/ut-1",
        json=GET_RESPONSE,
    )

    result = runner.invoke(app, ["usertests", "get", "ut-1"])

    assert result.exit_code == 0
    assert "usertest_id: ut-1" in result.output
    assert "title: User Test One" in result.output
    # Server-managed fields should be stripped
    assert "created_at" not in result.output
    assert "created_by" not in result.output
    # URLs should be displayed
    assert "https://usertests.podojo.com/preview/test-group/ut-1" in result.output
    assert "https://usertests.podojo.com/test-group?test=ut-1" in result.output


def test_get_usertest_not_found(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/usertests/nonexistent",
        status_code=404,
        json={"detail": "User test not found"},
    )

    result = runner.invoke(app, ["usertests", "get", "nonexistent"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_create_usertest(runner, httpx_mock, tmp_path):
    yaml_file = tmp_path / "usertest.yaml"
    yaml_file.write_text(VALID_USERTEST_YAML)

    httpx_mock.add_response(
        url="http://test.local/api/v1/usertests",
        method="POST",
        json={"usertest_id": "test-usertest-1", "id": "abc123", "group": "test-group"},
    )

    result = runner.invoke(app, ["usertests", "create", "-f", str(yaml_file)])

    assert result.exit_code == 0
    assert "test-usertest-1" in result.output
    assert "https://usertests.podojo.com/preview/test-group/test-usertest-1" in result.output
    assert "https://usertests.podojo.com/test-group?test=test-usertest-1" in result.output
    assert "podojo usertests snippet" in result.output


def test_create_usertest_collect_contact(runner, httpx_mock, tmp_path):
    yaml_file = tmp_path / "usertest.yaml"
    yaml_file.write_text(VALID_USERTEST_YAML + "collect_contact: true\n")

    httpx_mock.add_response(
        url="http://test.local/api/v1/usertests",
        method="POST",
        json={"usertest_id": "test-usertest-1", "id": "abc123", "group": "test-group"},
    )

    result = runner.invoke(app, ["usertests", "create", "-f", str(yaml_file)])

    assert result.exit_code == 0
    request = httpx_mock.get_requests()[-1]
    import json

    assert json.loads(request.content)["collect_contact"] is True


def test_create_usertest_file_not_found(runner):
    result = runner.invoke(app, ["usertests", "create", "-f", "/nonexistent/usertest.yaml"])

    assert result.exit_code == 1
    assert "File not found" in result.output


def test_create_usertest_invalid_yaml(runner, tmp_path):
    yaml_file = tmp_path / "bad.yaml"
    yaml_file.write_text(":\n  invalid: [yaml\n  broken")

    result = runner.invoke(app, ["usertests", "create", "-f", str(yaml_file)])

    assert result.exit_code == 1
    assert "Invalid YAML" in result.output


def test_create_usertest_missing_fields(runner, tmp_path):
    yaml_file = tmp_path / "incomplete.yaml"
    yaml_file.write_text("title: Just a title\n")

    result = runner.invoke(app, ["usertests", "create", "-f", str(yaml_file)])

    assert result.exit_code == 1
    assert "Missing required field" in result.output
    assert "'usertest_id'" in result.output


def test_create_usertest_invalid_step_type(runner, tmp_path):
    yaml_file = tmp_path / "badstep.yaml"
    yaml_file.write_text(
        "usertest_id: test\n"
        "client: Test\n"
        "title: Test\n"
        "logo: https://example.com/logo.png\n"
        "prototype_url: https://example.com/proto\n"
        "steps:\n"
        "  - type: invalid\n"
        "    title: Bad Step\n"
    )

    result = runner.invoke(app, ["usertests", "create", "-f", str(yaml_file)])

    assert result.exit_code == 1
    assert "'type' must be 'screen' or 'prototype'" in result.output


def test_create_usertest_duplicate(runner, httpx_mock, tmp_path):
    yaml_file = tmp_path / "usertest.yaml"
    yaml_file.write_text(VALID_USERTEST_YAML)

    httpx_mock.add_response(
        url="http://test.local/api/v1/usertests",
        method="POST",
        status_code=409,
        json={"detail": "User test with this ID already exists"},
    )

    result = runner.invoke(app, ["usertests", "create", "-f", str(yaml_file)])

    assert result.exit_code == 1
    assert "already exists" in result.output


def test_update_usertest(runner, httpx_mock, tmp_path):
    yaml_file = tmp_path / "update.yaml"
    yaml_file.write_text("title: Updated Title\n")

    httpx_mock.add_response(
        url="http://test.local/api/v1/usertests/ut-1",
        method="PUT",
        json={"usertest_id": "ut-1", "title": "Updated Title"},
    )

    result = runner.invoke(app, ["usertests", "update", "ut-1", "-f", str(yaml_file)])

    assert result.exit_code == 0
    assert "Updated user test" in result.output


def test_update_usertest_not_found(runner, httpx_mock, tmp_path):
    yaml_file = tmp_path / "update.yaml"
    yaml_file.write_text("title: Updated Title\n")

    httpx_mock.add_response(
        url="http://test.local/api/v1/usertests/nonexistent",
        method="PUT",
        status_code=404,
        json={"detail": "User test not found"},
    )

    result = runner.invoke(app, ["usertests", "update", "nonexistent", "-f", str(yaml_file)])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_delete_usertest(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/usertests/ut-1",
        method="DELETE",
        json={"status": "deleted", "usertest_id": "ut-1"},
    )

    result = runner.invoke(app, ["usertests", "delete", "ut-1", "--yes"])

    assert result.exit_code == 0
    assert "Deleted user test" in result.output


def test_delete_usertest_not_found(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/usertests/nonexistent",
        method="DELETE",
        status_code=404,
        json={"detail": "User test not found"},
    )

    result = runner.invoke(app, ["usertests", "delete", "nonexistent", "--yes"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_validate_valid(runner, tmp_path):
    yaml_file = tmp_path / "usertest.yaml"
    yaml_file.write_text(VALID_USERTEST_YAML)

    result = runner.invoke(app, ["usertests", "validate", str(yaml_file)])

    assert result.exit_code == 0
    assert "Valid user test config" in result.output


def test_validate_invalid(runner, tmp_path):
    yaml_file = tmp_path / "bad.yaml"
    yaml_file.write_text("title: Just a title\n")

    result = runner.invoke(app, ["usertests", "validate", str(yaml_file)])

    assert result.exit_code == 1
    assert "Missing required field" in result.output


SCREENING_YAML = VALID_USERTEST_YAML + """\
screening_questions:
  - text: Do you shop online?
    options:
      - text: "Yes"
        qualifies: true
      - text: "No"
  - text: How often do you shop online?
    options:
      - text: Never
      - text: Monthly
        qualifies: true
      - text: Weekly
        qualifies: true
rejection_message: You did not meet the research criteria for this study.
"""


def test_validate_with_screening(runner, tmp_path):
    yaml_file = tmp_path / "usertest.yaml"
    yaml_file.write_text(SCREENING_YAML)

    result = runner.invoke(app, ["usertests", "validate", str(yaml_file)])

    assert result.exit_code == 0
    assert "Valid user test config" in result.output


def test_validate_screening_question_needs_two_options(runner, tmp_path):
    yaml_file = tmp_path / "usertest.yaml"
    yaml_file.write_text(
        VALID_USERTEST_YAML
        + "screening_questions:\n"
        + "  - text: Only one way to answer?\n"
        + "    options:\n"
        + "      - text: \"Yes\"\n"
        + "        qualifies: true\n"
    )

    result = runner.invoke(app, ["usertests", "validate", str(yaml_file)])

    assert result.exit_code == 1
    assert "'options' must list at least 2 options" in result.output


def test_validate_screening_question_needs_a_qualifying_option(runner, tmp_path):
    yaml_file = tmp_path / "usertest.yaml"
    yaml_file.write_text(
        VALID_USERTEST_YAML
        + "screening_questions:\n"
        + "  - text: Nobody can pass this one\n"
        + "    options:\n"
        + "      - text: A\n"
        + "      - text: B\n"
    )

    result = runner.invoke(app, ["usertests", "validate", str(yaml_file)])

    assert result.exit_code == 1
    assert "needs at least one option with 'qualifies: true'" in result.output


def test_validate_screening_option_qualifies_must_be_bool(runner, tmp_path):
    yaml_file = tmp_path / "usertest.yaml"
    yaml_file.write_text(
        VALID_USERTEST_YAML
        + "screening_questions:\n"
        + "  - text: Q\n"
        + "    options:\n"
        + "      - text: A\n"
        + "        qualifies: yep\n"
        + "      - text: B\n"
        + "        qualifies: true\n"
    )

    result = runner.invoke(app, ["usertests", "validate", str(yaml_file)])

    assert result.exit_code == 1
    assert "'qualifies' must be true or false" in result.output


def test_example(runner):
    result = runner.invoke(app, ["usertests", "example"])

    assert result.exit_code == 0
    assert "usertest_id:" in result.output
    assert "steps:" in result.output
    assert "prototype" in result.output
    assert "screen" in result.output
    assert "screening_questions:" in result.output
    assert "rejection_message:" in result.output


def test_example_validates(runner, tmp_path):
    from podojo_cli.commands.usertests import EXAMPLE_YAML

    yaml_file = tmp_path / "example.yaml"
    yaml_file.write_text(EXAMPLE_YAML)

    result = runner.invoke(app, ["usertests", "validate", str(yaml_file)])

    assert result.exit_code == 0
    assert "Valid user test config" in result.output


def test_snippet(runner):
    result = runner.invoke(app, ["usertests", "snippet"])

    assert result.exit_code == 0
    assert "player.js" in result.output
    assert "rrweb.record" in result.output
