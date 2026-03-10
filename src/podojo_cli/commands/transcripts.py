from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..client import PodojoClient

app = typer.Typer(help="Manage transcripts")
console = Console()


@app.command("list")
def list_transcripts(project: str = typer.Argument(help="Project name")):
    """List transcripts for a project."""
    client = PodojoClient()
    data = client.list_transcripts(project)

    table = Table(title=f"Transcripts — {project} ({data['total']} total)")
    table.add_column("Batch ID")
    table.add_column("Name")

    for t in data["interviews"]:
        table.add_row(t.get("batch_id", ""), t.get("batch_name", ""))

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
