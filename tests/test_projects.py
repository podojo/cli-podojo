from podojo_cli.main import app


def test_list_projects(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/projects?skip=0&limit=50",
        json=[
            {"project_name": "Alpha", "description": "First project"},
            {"project_name": "Beta", "description": "Second project"},
        ],
    )

    result = runner.invoke(app, ["projects", "list"])

    assert result.exit_code == 0
    assert "Alpha" in result.output
    assert "Beta" in result.output


def test_list_projects_empty(runner, httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/projects?skip=0&limit=50",
        json=[],
    )

    result = runner.invoke(app, ["projects", "list"])

    assert result.exit_code == 0
