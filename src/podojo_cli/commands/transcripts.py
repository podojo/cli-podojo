from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..client import PodojoClient

app = typer.Typer(help="Manage transcripts")
console = Console()


def _format_date(value) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return str(value)


_QUALITY_COLORS = {"good": "green", "review": "yellow", "exclude": "red"}


def _format_quality(value) -> str:
    if not value:
        return ""
    color = _QUALITY_COLORS.get(value, "white")
    return f"[{color}]{value}[/{color}]"


@app.command("list")
def list_transcripts(project: str = typer.Argument(help="Project name")):
    """List transcripts for a project."""
    client = PodojoClient()
    data = client.list_transcripts(project)

    table = Table(title=f"Transcripts — {project} ({data['total']} total)")
    table.add_column("Date")
    table.add_column("Batch ID")
    table.add_column("Name")
    table.add_column("Quality")

    for t in data["interviews"]:
        table.add_row(
            _format_date(t.get("date")),
            t.get("batch_id", ""),
            t.get("batch_name", ""),
            _format_quality(t.get("quality_label")),
        )

    console.print(table)


@app.command("download")
def download_transcript(
    project: str = typer.Argument(help="Project name"),
    batch_id: str = typer.Argument(help="Batch ID"),
    output: Path = typer.Option(None, "-o", "--output", help="Output file path"),
):
    """Download a transcript."""
    client = PodojoClient()
    text = client.download_transcript(project, batch_id)

    if output:
        output.write_text(text)
        console.print(f"Saved to {output}")
    else:
        console.print(text)
