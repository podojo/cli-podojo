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
