from pathlib import Path

import typer
from rich.console import Console

from ..gdrive.list import list_files
from ..gdrive.upload import CREDENTIALS_FILENAME, upload_md_as_doc

app = typer.Typer(help="Upload documents to Google Drive")
console = Console()


@app.command("upload")
def upload(
    file: Path = typer.Argument(help="Markdown file to upload"),
    folder_id: str = typer.Option(..., "--folder-id", "-f", help="Google Drive folder ID"),
    title: str = typer.Option(None, "--title", "-t", help="Document title (defaults to filename)"),
):
    """Upload a markdown file to Google Drive as a Google Doc."""
    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

    if not Path(CREDENTIALS_FILENAME).exists():
        console.print(f"[red]Error:[/red] {CREDENTIALS_FILENAME} not found in current directory")
        raise typer.Exit(1)

    console.print(f"Uploading [bold]{file}[/bold]…", end=" ")
    _, url = upload_md_as_doc(str(file), folder_id=folder_id, title=title)
    console.print("[green]done[/green]")
    console.print(url)


@app.command("list")
def list_cmd(
    folder_id: str = typer.Option(..., "--folder-id", "-f", help="Google Drive folder ID"),
):
    """List files in a Google Drive folder."""
    if not Path(CREDENTIALS_FILENAME).exists():
        console.print(f"[red]Error:[/red] {CREDENTIALS_FILENAME} not found in current directory")
        raise typer.Exit(1)

    files = list_files(folder_id=folder_id)

    if not files:
        console.print("No files found.")
        return

    for f in files:
        link = f.get("webViewLink", "")
        console.print(f"[bold]{f['name']}[/bold]  {link}")
