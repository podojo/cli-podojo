import re
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..client import PodojoClient
from ..tables import print_table

app = typer.Typer(help="Manage transcripts")
console = Console()


def _format_date(value) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return str(value)


def _filename(interview: dict) -> str:
    """Name plus batch ID, so a file maps back to its batch ID without a
    lookup. Characters file systems reject become "_"."""
    batch_id = interview["batch_id"]
    name = re.sub(r'[\x00-\x1f/\\:*?"<>|]', "_", (interview.get("batch_name") or "").strip())
    return f"{name} - {batch_id}.txt" if name else f"{batch_id}.txt"


@app.command("list")
def list_transcripts(project: str = typer.Argument(help="Project name")):
    """List transcripts for a project."""
    client = PodojoClient()
    data = client.list_transcripts(project)

    table = Table(title=f"Transcripts — {project} ({data['total']} total)")
    table.add_column("Date")
    table.add_column("Batch ID", no_wrap=True)
    table.add_column("Name")

    for t in data["interviews"]:
        table.add_row(
            _format_date(t.get("date")),
            t.get("batch_id", ""),
            t.get("batch_name", ""),
        )

    print_table(console, table)


def _download_all(client: PodojoClient, project: str, folder: Path) -> None:
    data = client.list_transcripts(project)
    interviews = data["interviews"]
    folder.mkdir(parents=True, exist_ok=True)

    missing = []
    for interview in interviews:
        text = client.download_transcript(project, interview["batch_id"])
        if not text.strip():
            missing.append(interview.get("batch_name") or interview["batch_id"])
            continue
        path = folder / _filename(interview)
        path.write_text(text, encoding="utf-8")
        console.print(f"Saved {path}", soft_wrap=True, markup=False)

    console.print(
        f"Downloaded {len(interviews) - len(missing)} transcripts to {folder}",
        soft_wrap=True,
        markup=False,
    )
    if missing:
        console.print(f"No transcript yet: {', '.join(missing)}", soft_wrap=True, markup=False)
    if data["total"] > len(interviews):
        console.print(f"Only the newest {len(interviews)} of {data['total']} interviews were downloaded.")


@app.command("download")
def download_transcript(
    project: str = typer.Argument(help="Project name"),
    batch_id: str = typer.Argument(None, help="Batch ID (leave out with --all)"),
    all_: bool = typer.Option(False, "--all", help="Download every transcript in the project"),
    output: Path = typer.Option(
        None, "-o", "--output", help="Output file path, or the folder for --all (default: current folder)"
    ),
):
    """Download a transcript, or all of a project's transcripts with --all."""
    if bool(batch_id) == all_:
        console.print("[red]Error:[/red] Pass either a batch ID or --all.")
        raise typer.Exit(1)

    client = PodojoClient()
    if all_:
        _download_all(client, project, output or Path("."))
        return

    text = client.download_transcript(project, batch_id)

    if output:
        output.write_text(text, encoding="utf-8")
        console.print(f"Saved to {output}")
    else:
        console.print(text)
