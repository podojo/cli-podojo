import json
import os
import shutil
import tempfile
from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn

from ..client import PodojoClient
from ..video.showreel import concatenate, extract_clip, has_filters, make_title_card, write_subtitles
from .usertests import _format_api_error

app = typer.Typer(help="Generate video showreels")
console = Console()

# Homebrew's ffmpeg-full has the text filters but isn't linked onto the PATH
FFMPEG_FULL_PATHS = (
    "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",
    "/usr/local/opt/ffmpeg-full/bin/ffmpeg",
)


def _check_ffmpeg(filters: tuple[str, ...] = ("drawtext",)):
    """Puts the first ffmpeg that has the filters on the PATH for this run."""
    installed = [path for path in map(shutil.which, ("ffmpeg", *FFMPEG_FULL_PATHS)) if path]
    if not installed:
        console.print("[red]Error:[/red] ffmpeg not found. Install it with: brew install ffmpeg-full")
        raise typer.Exit(1)

    for path in installed:
        if has_filters(path, filters):
            os.environ["PATH"] = f"{os.path.dirname(path)}{os.pathsep}{os.environ['PATH']}"
            return

    console.print(
        f"[red]Error:[/red] your ffmpeg lacks the {', '.join(filters)} filters. "
        "Install the full build with: brew install ffmpeg-full"
    )
    raise typer.Exit(1)


def _download_video(url: str, dest: Path):
    with httpx.stream("GET", url, follow_redirects=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest, "wb") as f, Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            DownloadColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"  Downloading {dest.name}…", total=total or None)
            for chunk in r.iter_bytes(chunk_size=8192):
                f.write(chunk)
                progress.update(task, advance=len(chunk))


def _fetch_subtitles(client: PodojoClient, clips: list[dict]) -> tuple[list[list[dict]], list[str]]:
    """The cues of each clip plus the clips left without subtitles. Runs before
    any video is downloaded, so a failed translation stops early."""
    console.print(f"\nFetching subtitles for {len(clips)} clip(s)…")
    subtitles, skipped = [], []

    for clip in clips:
        label = f"{clip['participant']} — {clip['topic']}"
        try:
            result = client.get_subtitles(clip["batch_id"], clip["start"], clip["end"])
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 409:
                console.print(f"[red]Error:[/red] {_format_api_error(e)}")
                raise typer.Exit(1)
            subtitles.append([])
            skipped.append(f"{label}: transcribed before subtitles were available")
            continue

        subtitles.append(result["cues"])
        if result["language"] == "en":
            skipped.append(f"{label}: already in English")

    return subtitles, skipped


@app.command("create")
def create_showreel(
    clips_json: Path = typer.Argument(help="Path to clips JSON file"),
    output: Path = typer.Option("showreel.mp4", "-o", "--output", help="Output .mp4 path"),
    subtitles: bool = typer.Option(False, "--subtitles", help="Burn English subtitles into non-English clips"),
):
    """Create a video showreel from a clips JSON config.

    The clips JSON should be a list of objects with these fields:
      batch_id   - video batch ID to fetch from the API
      participant - display name (e.g. "P09 — Umid")
      country    - participant country
      topic      - short description of what the clip shows
      start      - clip start time (MM:SS or HH:MM:SS)
      end        - clip end time (MM:SS or HH:MM:SS)

    With --subtitles, clips from non-English sessions get English subtitles.
    English clips stay as they are, and so do clips from sessions transcribed
    before subtitles were available; both are listed at the end.
    """
    _check_ffmpeg(("drawtext", "ass") if subtitles else ("drawtext",))

    with open(clips_json, encoding="utf-8") as f:
        clips = json.load(f)

    if not clips:
        console.print("[yellow]No clips found in JSON.[/yellow]")
        raise typer.Exit(0)

    client = PodojoClient()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    clip_cues, skipped = _fetch_subtitles(client, clips) if subtitles else ([[] for _ in clips], [])

    with tempfile.TemporaryDirectory(prefix="podojo-showreel-") as tmp:
        tmp = Path(tmp)

        # Download each unique batch_id once
        video_paths: dict[str, Path] = {}
        unique_ids = {c["batch_id"] for c in clips}
        console.print(f"\nDownloading {len(unique_ids)} video(s)…")

        for batch_id in unique_ids:
            data = client.get_video_url(batch_id)
            dest = tmp / f"{batch_id}.mp4"
            _download_video(data["url"], dest)
            video_paths[batch_id] = dest

        # Build segments
        parts: list[str] = []
        console.print(f"\nProcessing {len(clips)} clip(s)…")

        for i, (clip, cues) in enumerate(zip(clips, clip_cues), 1):
            participant = clip["participant"]
            country = clip["country"]
            topic = clip["topic"]
            src = str(video_paths[clip["batch_id"]])

            console.print(f"  [{i}/{len(clips)}] {participant} — {topic}")

            title_dst = str(tmp / f"_title_{i:02d}.mp4")
            clip_dst = str(tmp / f"_clip_{i:02d}.mp4")

            make_title_card(participant, country, topic, title_dst)
            subtitles_path = None
            if cues:
                subtitles_path = str(tmp / f"_subtitles_{i:02d}.ass")
                write_subtitles(cues, subtitles_path)
            extract_clip(src, clip["start"], clip["end"], clip_dst, subtitles_path)

            parts.extend([title_dst, clip_dst])

        console.print("\nConcatenating…")
        concatenate(parts, str(output))

    size_mb = os.path.getsize(output) / (1024 * 1024)
    console.print(f"\n[green]Done![/green] {output} ({size_mb:.1f} MB)")

    if skipped:
        console.print(f"\n[yellow]{len(skipped)} clip(s) without subtitles:[/yellow]")
        for line in skipped:
            console.print(f"  {line}", markup=False)
