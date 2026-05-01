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
