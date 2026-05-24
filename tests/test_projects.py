from podojo_cli.commands.projects import strip_images
from podojo_cli.main import app


def test_list_projects(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/projects?skip=0&limit=50",
        json={
            "projects": [
                {"name": "Alpha", "brief": "First project"},
                {"name": "Beta", "brief": "Second project"},
            ],
            "total": 2,
            "skip": 0,
            "limit": 50,
        },
    )

    result = runner.invoke(app, ["projects", "list"])

    assert result.exit_code == 0
    assert "Alpha" in result.output
    assert "Beta" in result.output


def test_list_projects_empty(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/projects?skip=0&limit=50",
        json={
            "projects": [],
            "total": 0,
            "skip": 0,
            "limit": 50,
        },
    )

    result = runner.invoke(app, ["projects", "list"])

    assert result.exit_code == 0


def test_create_project(runner, httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="http://test.local/api/v1/projects",
        match_json={"name": "Gamma", "brief": "Third project"},
        json={
            "id": "abc123",
            "name": "Gamma",
            "brief": "Third project",
            "message": "Project created successfully",
        },
    )

    result = runner.invoke(app, ["projects", "create", "Gamma", "--brief", "Third project"])

    assert result.exit_code == 0
    assert "Gamma" in result.output
    assert "abc123" in result.output


def test_create_project_duplicate(runner, httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="http://test.local/api/v1/projects",
        status_code=409,
        json={"detail": "Project with this name already exists"},
    )

    result = runner.invoke(app, ["projects", "create", "Gamma"])

    assert result.exit_code == 1
    assert "already exists" in result.output


def test_strip_images_base64_reference_defs():
    text = (
        "# Title\n\n"
        "Paragraph with ![][image1] inline reference.\n\n"
        "[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA>\n"
        "[image2]: <data:image/jpeg;base64,/9j/4AAQSkZJRg==>\n"
    )
    cleaned, count = strip_images(text)
    assert "data:image" not in cleaned
    assert "![]" not in cleaned
    assert "image1" not in cleaned
    assert "# Title" in cleaned
    assert "Paragraph with  inline reference." in cleaned
    assert count == 3


def test_strip_images_inline_and_html():
    text = (
        "Inline: ![alt](https://example.com/x.png)\n"
        'HTML: <img src="https://example.com/y.jpg" alt="y">\n'
        "Reference: ![alt][ref]\n"
    )
    cleaned, count = strip_images(text)
    assert "example.com" not in cleaned
    assert "<img" not in cleaned
    assert "![alt]" not in cleaned
    assert count == 3


def test_strip_images_keeps_regular_links():
    text = "See [the doc](https://example.com/doc) and [ref][label]."
    cleaned, count = strip_images(text)
    assert cleaned == text
    assert count == 0


def test_upload_doc_strips_images_before_upload(runner, tmp_path, httpx_mock):
    md = (
        "# Brief\n\nBody text ![][image1] continues.\n\n"
        "[image1]: <data:image/png;base64,AAAA>\n"
    )
    file = tmp_path / "brief.md"
    file.write_text(md, encoding="utf-8")

    httpx_mock.add_response(
        method="PUT",
        url="http://test.local/api/v1/projects/Alpha/documents/research_brief",
        match_json={"content": "# Brief\n\nBody text  continues.\n"},
        json={"ok": True},
    )

    result = runner.invoke(app, ["projects", "upload-doc", "Alpha", str(file), "--type", "brief"])

    assert result.exit_code == 0
    assert "Stripped" in result.output
    assert "2 image" in result.output


def test_upload_doc_no_images_no_strip_message(runner, tmp_path, httpx_mock):
    file = tmp_path / "brief.md"
    file.write_text("# Brief\n\nJust text, no images.\n", encoding="utf-8")

    httpx_mock.add_response(
        method="PUT",
        url="http://test.local/api/v1/projects/Alpha/documents/research_brief",
        json={"ok": True},
    )

    result = runner.invoke(app, ["projects", "upload-doc", "Alpha", str(file), "--type", "brief"])

    assert result.exit_code == 0
    assert "Stripped" not in result.output


def test_upload_doc_agent_report(runner, tmp_path, httpx_mock):
    file = tmp_path / "agent.md"
    file.write_text("# Agent Report\n\nFindings.\n", encoding="utf-8")

    httpx_mock.add_response(
        method="PUT",
        url="http://test.local/api/v1/projects/Alpha/documents/agent_report",
        match_json={"content": "# Agent Report\n\nFindings.\n"},
        json={"ok": True},
    )

    result = runner.invoke(app, ["projects", "upload-doc", "Alpha", str(file), "--type", "agent"])

    assert result.exit_code == 0
    assert "Uploaded" in result.output
