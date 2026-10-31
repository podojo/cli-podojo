import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import typer

from podojo_cli.commands.showreel import FFMPEG_FULL_PATHS, _check_ffmpeg
from podojo_cli.main import app
from podojo_cli.video.showreel import extract_clip, has_filters, write_subtitles


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


SUBTITLES_URL = "http://test.local/api/v1/videos/batch-1/subtitles"
CUES = [{"start_ms": 1200, "end_ms": 4300, "text": "I couldn't find the field"}]


def _mock_video(httpx_mock):
    httpx_mock.add_response(
        url="http://test.local/api/v1/videos/batch-1",
        json={"url": "http://storage.test/video.mp4", "filename": "video.mp4"},
    )
    httpx_mock.add_response(url="http://storage.test/video.mp4", content=b"fake-video-bytes")


def _create(runner, tmp_path, *args):
    clips_file = tmp_path / "clips.json"
    clips_file.write_text(json.dumps(CLIPS))

    with (
        patch("podojo_cli.commands.showreel.make_title_card"),
        patch("podojo_cli.commands.showreel.extract_clip") as mock_clip,
        patch("podojo_cli.commands.showreel.write_subtitles") as mock_write,
        patch("podojo_cli.commands.showreel.concatenate"),
        patch("podojo_cli.commands.showreel._check_ffmpeg") as mock_check,
        patch("os.path.getsize", return_value=1024 * 1024),
    ):
        result = runner.invoke(app, ["showreel", "create", str(clips_file), "-o", str(tmp_path / "out.mp4"), *args])

    return result, mock_clip, mock_write, mock_check


def test_subtitles_are_fetched_before_the_video_and_burned_in(runner, httpx_mock, tmp_path):
    httpx_mock.add_response(url=SUBTITLES_URL, json={"language": "de", "cues": CUES})
    _mock_video(httpx_mock)

    result, mock_clip, mock_write, mock_check = _create(runner, tmp_path, "--subtitles")

    assert result.exit_code == 0, result.output
    mock_check.assert_called_once_with(("drawtext", "ass"))
    first = httpx_mock.get_requests()[0]
    assert str(first.url) == SUBTITLES_URL
    assert json.loads(first.content) == {"start": "01:00", "end": "01:30"}
    subtitles_path = mock_clip.call_args.args[4]
    mock_write.assert_called_once_with(CUES, subtitles_path)
    assert "without subtitles" not in result.output


def test_no_subtitles_requested_makes_no_subtitles_call(runner, httpx_mock, tmp_path):
    _mock_video(httpx_mock)

    result, mock_clip, mock_write, mock_check = _create(runner, tmp_path)

    assert result.exit_code == 0, result.output
    mock_check.assert_called_once_with(("drawtext",))
    assert SUBTITLES_URL not in [str(r.url) for r in httpx_mock.get_requests()]
    assert mock_clip.call_args.args[4] is None
    mock_write.assert_not_called()


def test_english_clip_is_left_alone_and_listed(runner, httpx_mock, tmp_path):
    httpx_mock.add_response(url=SUBTITLES_URL, json={"language": "en", "cues": []})
    _mock_video(httpx_mock)

    result, mock_clip, mock_write, _ = _create(runner, tmp_path, "--subtitles")

    assert result.exit_code == 0, result.output
    assert mock_clip.call_args.args[4] is None
    mock_write.assert_not_called()
    assert "1 clip(s) without subtitles" in result.output
    assert "already in English" in result.output


def test_silent_clip_is_not_listed_as_skipped(runner, httpx_mock, tmp_path):
    httpx_mock.add_response(url=SUBTITLES_URL, json={"language": "de", "cues": []})
    _mock_video(httpx_mock)

    result, mock_clip, _, _ = _create(runner, tmp_path, "--subtitles")

    assert result.exit_code == 0, result.output
    assert mock_clip.call_args.args[4] is None
    assert "without subtitles" not in result.output


def test_older_session_is_left_alone_and_listed(runner, httpx_mock, tmp_path):
    httpx_mock.add_response(url=SUBTITLES_URL, status_code=409, json={"detail": "no word timings"})
    _mock_video(httpx_mock)

    result, mock_clip, _, _ = _create(runner, tmp_path, "--subtitles")

    assert result.exit_code == 0, result.output
    assert mock_clip.call_args.args[4] is None
    assert "transcribed before subtitles were available" in result.output


def test_failed_translation_stops_before_any_video_is_downloaded(runner, httpx_mock, tmp_path):
    httpx_mock.add_response(url=SUBTITLES_URL, status_code=502, json={"detail": "Translating the subtitles failed"})

    result, mock_clip, _, _ = _create(runner, tmp_path, "--subtitles")

    assert result.exit_code == 1
    assert "Translating the subtitles failed" in result.output
    assert len(httpx_mock.get_requests()) == 1
    mock_clip.assert_not_called()


def test_write_subtitles(tmp_path):
    path = tmp_path / "clip.ass"

    write_subtitles([
        {"start_ms": 1230, "end_ms": 62_050, "text": "Hello [PERSON_NAME], {odd}\\text\nüber"},
        {"start_ms": 3_600_000, "end_ms": 3_601_000, "text": "Later"},
    ], str(path))

    lines = path.read_text(encoding="utf-8").splitlines()
    assert "PlayResX: 1280" in lines
    assert lines[-2:] == [
        "Dialogue: 0,0:00:01.23,0:01:02.05,Default,,0,0,0,,Hello [PERSON_NAME], (odd)/text über",
        "Dialogue: 0,1:00:00.00,1:00:01.00,Default,,0,0,0,,Later",
    ]


def test_extract_clip_without_subtitles_keeps_the_full_picture():
    with patch("podojo_cli.video.showreel._run") as mock_run:
        extract_clip("in.mp4", "00:10", "00:20", "out.mp4")

    cmd = mock_run.call_args.args[0]
    assert cmd[cmd.index("-vf") + 1] == "scale=-2:720,pad=1280:720:(ow-iw)/2:0:color=0x1a1a2e"


def test_extract_clip_with_subtitles_leaves_a_band_for_them():
    with patch("podojo_cli.video.showreel._run") as mock_run:
        extract_clip("in.mp4", "00:10", "00:20", "out.mp4", "C:/tmp/clip.ass")

    cmd = mock_run.call_args.args[0]
    assert cmd[cmd.index("-vf") + 1] == (
        "scale=-2:620,pad=1280:720:(ow-iw)/2:0:color=0x1a1a2e,ass='C\\:/tmp/clip.ass'"
    )


def test_has_filters_reads_the_filter_list():
    listing = """Filters:
  T.. = Timeline support
 T.C drawtext          V->V       Draw text on top of video frames using libfreetype library.
 TSC overlay           VV->V      Overlay a video source on top of the input.
"""
    with patch("subprocess.run", return_value=MagicMock(stdout=listing)):
        assert has_filters("ffmpeg", ("drawtext",))
        assert not has_filters("ffmpeg", ("drawtext", "ass"))


def _which(*installed):
    return lambda name: name if name in installed else None


def test_check_ffmpeg_keeps_a_capable_ffmpeg(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin")
    with (
        patch("shutil.which", side_effect=_which("ffmpeg")),
        patch("podojo_cli.commands.showreel.has_filters", return_value=True),
    ):
        _check_ffmpeg()


def test_check_ffmpeg_falls_back_to_ffmpeg_full(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin")
    full = FFMPEG_FULL_PATHS[0]
    with (
        patch("shutil.which", side_effect=_which("ffmpeg", full)),
        patch("podojo_cli.commands.showreel.has_filters", side_effect=lambda path, filters: path == full),
    ):
        _check_ffmpeg(("drawtext", "ass"))

    assert os.environ["PATH"].startswith(os.path.dirname(full))


def test_check_ffmpeg_explains_missing_filters(capsys):
    with (
        patch("shutil.which", side_effect=_which("ffmpeg")),
        patch("podojo_cli.commands.showreel.has_filters", return_value=False),
        pytest.raises(typer.Exit),
    ):
        _check_ffmpeg(("drawtext", "ass"))

    assert "brew install ffmpeg-full" in capsys.readouterr().out
