from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from ..client import PodojoClient

app = typer.Typer(help="Manage videos")
console = Console()


@app.command("list")
def list_videos(project: str = typer.Argument(help="Project name")):
    """List videos for a project."""
    client = PodojoClient()
    data = client.list_videos(project)

    table = Table(title=f"Videos — {project} ({data['total']} total)")
    table.add_column("Batch ID")
    table.add_column("Name")
    table.add_column("Duration (min)")

    for v in data["videos"]:
        table.add_row(
            v.get("batch_id", ""),
            v.get("batch_name", ""),
            str(v.get("duration_minutes", "")),
        )

    console.print(table)


@app.command("download")
def download_video(
    batch_id: str = typer.Argument(help="Batch ID"),
    output: Path = typer.Option(None, "-o", "--output", help="Output file path"),
):
    """Download a video file."""
    client = PodojoClient()
    data = client.get_video_url(batch_id)
    url = data["url"]

    filename = output or Path(f"{data.get('batch_name', batch_id)}.mp4")

    with httpx.stream("GET", url) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(filename, "wb") as f, Progress() as progress:
            task = progress.add_task("Downloading...", total=total)
            for chunk in r.iter_bytes(chunk_size=8192):
                f.write(chunk)
                progress.update(task, advance=len(chunk))

    console.print(f"Saved to {filename}")
