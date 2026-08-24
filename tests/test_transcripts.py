from podojo_cli.main import app


def test_list_transcripts(runner, httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url="http://test.local/api/v1/projects/Alpha/transcripts",
        json={
            "project": "Alpha",
            "total": 2,
            "interviews": [
                {
                    "batch_id": "batch-1",
                    "batch_name": "session_1",
                    "date": "2026-05-01T12:00:00",
                },
                {
                    "batch_id": "batch-2",
                    "batch_name": "session_2",
                    "date": "2026-05-02T12:00:00",
                },
            ],
        },
    )

    result = runner.invoke(app, ["transcripts", "list", "Alpha"])

    assert result.exit_code == 0
    assert "batch-1" in result.output
    assert "session_2" in result.output
