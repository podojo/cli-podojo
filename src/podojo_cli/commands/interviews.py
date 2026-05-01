from pathlib import Path

import httpx
import typer
from rich.console import Console

from ..client import PodojoClient

app = typer.Typer(help="Manage interviews")
console = Console()


@app.command("upload")
def upload_interview(
    file: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=False,
        readable=True,
        help="Audio/video file to upload",
    ),
    project: str = typer.Option(..., "--project", "-p", help="Existing project name"),
    audio_only: bool = typer.Option(False, "--audio-only", help="Skip video processing"),
    batch_name: str = typer.Option(
        None, "--name", "-n", help="Override interview name (defaults to filename)"
    ),
):
    """Upload an audio/video interview file to an existing project."""
    client = PodojoClient()
    size_mb = file.stat().st_size / (1024 * 1024)
    with console.status(f"Uploading {file.name} ({size_mb:.1f} MB)..."):
        try:
            result = client.upload_interview(
                project, file, audio_only=audio_only, batch_name=batch_name
            )
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            detail = ""
            try:
                detail = e.response.json().get("detail", "")
            except Exception:
                detail = e.response.text
            if status == 404:
                console.print(
                    f"[red]Project '{project}' not found.[/red] "
                    f"Create it first: [bold]podojo projects create \"{project}\"[/bold]"
                )
            elif status == 400:
                console.print(f"[red]{detail}[/red]")
            else:
                console.print(f"[red]{status}: {detail}[/red]")
            raise typer.Exit(code=1)

    console.print(
        f"Uploaded [bold]{file.name}[/bold] → {project} "
        f"(batch_id={result['batch_id']})"
    )
