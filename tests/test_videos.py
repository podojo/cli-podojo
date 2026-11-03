from podojo_cli.main import app


def test_list_videos_keeps_batch_ids_whole_off_terminal(runner, httpx_mock, monkeypatch):
    monkeypatch.setenv("COLUMNS", "80")
    batch_id = "62d1b9bf-8f03-41d1-b5e0-d0c4bd0e7eb6"
    httpx_mock.add_response(
        method="GET",
        url="http://test.local/api/v1/projects/Alpha/videos",
        json={
            "project": "Alpha",
            "total": 1,
            "videos": [
                {
                    "batch_id": batch_id,
                    "batch_name": "RapidUsertest 32721 1 (3)",
                    "batch_timestamp": "2026-09-17T14:10:00",
                    "duration_minutes": 12.4,
                },
            ],
        },
    )

    result = runner.invoke(app, ["videos", "list", "Alpha"])

    assert result.exit_code == 0
    assert batch_id in result.output
    assert "RapidUsertest 32721 1 (3)" in result.output
