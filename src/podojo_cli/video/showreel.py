"""FFmpeg-based showreel generation from a list of clips."""

import os
import subprocess
from pathlib import Path

WIDTH = 1280
HEIGHT = 720
FPS = 30
# Subtitled clips leave a band below the picture, so captions never cover the UI
CAPTION_BAND = 100
AUDIO_OPTS = ["-c:a", "aac", "-ac", "1", "-ar", "16000", "-b:a", "64k"]
TITLE_DURATION = 4
ASS_HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Helvetica,30,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,60,60,12,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _video_opts(picture_height: int, extra_filter: str = "") -> list[str]:
    scale_pad = f"scale=-2:{picture_height},pad={WIDTH}:{HEIGHT}:(ow-iw)/2:0:color=0x1a1a2e"
    return [
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-vf", f"{scale_pad}{extra_filter}", "-r", str(FPS), "-pix_fmt", "yuv420p",
    ]


def _run(cmd):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-800:]}")


def has_filters(ffmpeg: str, filters: tuple[str, ...]) -> bool:
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-filters"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30,
    )
    available = {line.split()[1] for line in result.stdout.splitlines() if len(line.split()) > 1}
    return all(name in available for name in filters)


def _ass_time(ms: int) -> str:
    cs = ms // 10
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _ass_text(text: str) -> str:
    return " ".join(text.replace("\\", "/").replace("{", "(").replace("}", ")").split())


def write_subtitles(cues: list[dict], dst: str):
    with open(dst, "w", encoding="utf-8") as f:
        f.write(ASS_HEADER)
        for cue in cues:
            start, end = _ass_time(cue["start_ms"]), _ass_time(cue["end_ms"])
            f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{_ass_text(cue['text'])}\n")


def extract_clip(src: str, start: str, end: str, dst: str, subtitles: str | None = None):
    if subtitles:
        path = Path(subtitles).as_posix().replace(":", "\\:")
        video_opts = _video_opts(HEIGHT - CAPTION_BAND, f",ass='{path}'")
    else:
        video_opts = _video_opts(HEIGHT)
    _run([
        "ffmpeg", "-y", "-ss", start, "-to", end, "-i", src,
        *video_opts, *AUDIO_OPTS, dst,
    ])


def make_title_card(participant: str, country: str, topic: str, dst: str):
    def esc(t):
        return t.replace(":", "\\:").replace("'", "'\\''")

    vf = (
        f"drawtext=text='{esc(participant)}':fontsize=48:fontcolor=white:"
        f"x=(w-text_w)/2:y=(h/2)-80:font=Helvetica,"
        f"drawtext=text='{esc(country)}':fontsize=32:fontcolor=0xBBBBBB:"
        f"x=(w-text_w)/2:y=(h/2)-20:font=Helvetica,"
        f"drawtext=text='{esc(topic)}':fontsize=36:fontcolor=0x34D399:"
        f"x=(w-text_w)/2:y=(h/2)+40:font=Helvetica"
    )

    _run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x1a1a2e:s={WIDTH}x{HEIGHT}:d={TITLE_DURATION}:r={FPS}",
        "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
        "-t", str(TITLE_DURATION),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        *AUDIO_OPTS,
        "-shortest",
        dst,
    ])


def concatenate(parts: list[str], output: str):
    concat_list = os.path.join(os.path.dirname(output), "_concat.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")

    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c", "copy", output,
    ])

    os.remove(concat_list)
