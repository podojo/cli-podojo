"""FFmpeg-based showreel generation from a list of clips."""

import os
import subprocess

WIDTH = 1280
HEIGHT = 720
FPS = 30
SCALE_PAD = f"scale=-2:{HEIGHT},pad={WIDTH}:{HEIGHT}:(ow-iw)/2:0:color=0x1a1a2e"
VIDEO_OPTS = [
    "-c:v", "libx264", "-preset", "medium", "-crf", "18",
    "-vf", SCALE_PAD, "-r", str(FPS), "-pix_fmt", "yuv420p",
]
AUDIO_OPTS = ["-c:a", "aac", "-ac", "1", "-ar", "16000", "-b:a", "64k"]
TITLE_DURATION = 4


def _run(cmd):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-800:]}")


def extract_clip(src: str, start: str, end: str, dst: str):
    _run([
        "ffmpeg", "-y", "-ss", start, "-to", end, "-i", src,
        *VIDEO_OPTS, *AUDIO_OPTS, dst,
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
    with open(concat_list, "w") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")

    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c", "copy", output,
    ])

    os.remove(concat_list)
