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


BATCH_ID = "62d1b9bf-8f03-41d1-b5e0-d0c4bd0e7eb6"


def test_list_transcripts_keeps_batch_ids_whole_off_terminal(runner, httpx_mock, monkeypatch):
    monkeypatch.setenv("COLUMNS", "80")
    httpx_mock.add_response(
        method="GET",
        url="http://test.local/api/v1/projects/Alpha/transcripts",
        json={
            "project": "Alpha",
            "total": 1,
            "interviews": [
                {"batch_id": BATCH_ID, "batch_name": "RapidUsertest 32721 1 (3)", "date": "2026-09-17T14:10:00"},
            ],
        },
    )

    result = runner.invoke(app, ["transcripts", "list", "Alpha"])

    assert result.exit_code == 0
    assert BATCH_ID in result.output
    assert "RapidUsertest 32721 1 (3)" in result.output


def test_download_all_transcripts(runner, httpx_mock, tmp_path):
    httpx_mock.add_response(
        method="GET",
        url="http://test.local/api/v1/projects/Alpha/transcripts",
        json={
            "project": "Alpha",
            "total": 3,
            "interviews": [
                {"batch_id": BATCH_ID, "batch_name": "Session 1/2"},
                {"batch_id": "batch-2", "batch_name": "[DE] session_2"},
                {"batch_id": "batch-3", "batch_name": "session_3"},
            ],
        },
    )
    httpx_mock.add_response(
        method="GET", url=f"http://test.local/api/v1/projects/Alpha/transcripts/{BATCH_ID}", text="Hello"
    )
    httpx_mock.add_response(
        method="GET", url="http://test.local/api/v1/projects/Alpha/transcripts/batch-2", text="Hallo"
    )
    httpx_mock.add_response(
        method="GET", url="http://test.local/api/v1/projects/Alpha/transcripts/batch-3", text=""
    )
    folder = tmp_path / "transcripts"

    result = runner.invoke(app, ["transcripts", "download", "Alpha", "--all", "-o", str(folder)])

    assert result.exit_code == 0
    assert (folder / f"Session 1_2 - {BATCH_ID}.txt").read_text() == "Hello"
    assert (folder / "[DE] session_2 - batch-2.txt").read_text() == "Hallo"
    assert sorted(p.name for p in folder.iterdir()) == [f"Session 1_2 - {BATCH_ID}.txt", "[DE] session_2 - batch-2.txt"]
    assert "Downloaded 2 transcripts" in result.output
    assert "No transcript yet: session_3" in result.output


def test_download_transcript_needs_batch_id_or_all(runner):
    for args in (["Alpha"], ["Alpha", "batch-1", "--all"]):
        result = runner.invoke(app, ["transcripts", "download", *args])

        assert result.exit_code == 1
        assert "Pass either a batch ID or --all" in result.output
