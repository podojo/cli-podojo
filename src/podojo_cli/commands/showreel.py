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
from ..video.showreel import extract_clip, make_title_card, concatenate

app = typer.Typer(help="Generate video showreels")
console = Console()


def _check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        console.print("[red]Error:[/red] ffmpeg not found. Install it with: brew install ffmpeg")
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


@app.command("create")
def create_showreel(
    clips_json: Path = typer.Argument(help="Path to clips JSON file"),
    output: Path = typer.Option("showreel.mp4", "-o", "--output", help="Output .mp4 path"),
):
    """Create a video showreel from a clips JSON config.

    The clips JSON should be a list of objects with these fields:
      batch_id   - video batch ID to fetch from the API
      participant - display name (e.g. "P09 — Umid")
      country    - participant country
      topic      - short description of what the clip shows
      start      - clip start time (MM:SS or HH:MM:SS)
      end        - clip end time (MM:SS or HH:MM:SS)
    """
    _check_ffmpeg()

    with open(clips_json) as f:
        clips = json.load(f)

    if not clips:
        console.print("[yellow]No clips found in JSON.[/yellow]")
        raise typer.Exit(0)

    client = PodojoClient()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

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

        for i, clip in enumerate(clips, 1):
            participant = clip["participant"]
            country = clip["country"]
            topic = clip["topic"]
            src = str(video_paths[clip["batch_id"]])

            console.print(f"  [{i}/{len(clips)}] {participant} — {topic}")

            title_dst = str(tmp / f"_title_{i:02d}.mp4")
            clip_dst = str(tmp / f"_clip_{i:02d}.mp4")

            make_title_card(participant, country, topic, title_dst)
            extract_clip(src, clip["start"], clip["end"], clip_dst)

            parts.extend([title_dst, clip_dst])

        console.print("\nConcatenating…")
        concatenate(parts, str(output))

    size_mb = os.path.getsize(output) / (1024 * 1024)
    console.print(f"\n[green]Done![/green] {output} ({size_mb:.1f} MB)")
