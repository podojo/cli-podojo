import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from podojo_cli.main import app


CLIPS = [
    {
        "batch_id": "batch-1",
        "participant": "P01 — Alice",
        "country": "UK",
        "topic": "Confused by checkout",
        "start": "01:00",
        "end": "01:30",
    }
]


def test_create_showreel(runner, httpx_mock, tmp_path):
    clips_file = tmp_path / "clips.json"
    clips_file.write_text(json.dumps(CLIPS))
    output_file = tmp_path / "out.mp4"

    httpx_mock.add_response(
        url="http://test.local/api/v1/videos/batch-1",
        json={"url": "http://storage.test/video.mp4", "filename": "video.mp4"},
    )
    httpx_mock.add_response(
        url="http://storage.test/video.mp4",
        content=b"fake-video-bytes",
    )

    with (
        patch("podojo_cli.commands.showreel.make_title_card") as mock_title,
        patch("podojo_cli.commands.showreel.extract_clip") as mock_clip,
        patch("podojo_cli.commands.showreel.concatenate") as mock_concat,
        patch("podojo_cli.commands.showreel._check_ffmpeg"),
        patch("os.path.getsize", return_value=1024 * 1024),
    ):
        result = runner.invoke(app, ["showreel", "create", str(clips_file), "-o", str(output_file)])

    assert result.exit_code == 0, result.output
    mock_title.assert_called_once_with("P01 — Alice", "UK", "Confused by checkout", mock_title.call_args[0][3])
    mock_clip.assert_called_once()
    mock_concat.assert_called_once()


def test_create_showreel_missing_ffmpeg(runner, tmp_path):
    clips_file = tmp_path / "clips.json"
    clips_file.write_text(json.dumps(CLIPS))

    import shutil
    with patch.object(shutil, "which", return_value=None):
        result = runner.invoke(app, ["showreel", "create", str(clips_file)])

    assert result.exit_code != 0
