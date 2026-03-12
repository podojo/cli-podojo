from pathlib import Path

import typer
from rich.console import Console

from ..config import load_config, save_gdrive_credentials
from ..gdrive.upload import upload_md_as_doc

app = typer.Typer(help="Upload documents to Google Drive")
console = Console()


@app.command("setup")
def setup(credentials_file: Path = typer.Argument(help="Path to Google service account JSON key file")):
    """Save the path to your Google service account credentials."""
    if not credentials_file.exists():
        console.print(f"[red]Error:[/red] File not found: {credentials_file}")
        raise typer.Exit(1)
    save_gdrive_credentials(str(credentials_file.resolve()))
    console.print(f"[green]Credentials saved:[/green] {credentials_file.resolve()}")


@app.command("upload")
def upload(
    file: Path = typer.Argument(help="Markdown file to upload"),
    title: str = typer.Option(None, "--title", "-t", help="Document title (defaults to filename)"),
    folder_id: str = typer.Option(None, "--folder-id", "-f", help="Google Drive folder ID"),
):
    """Upload a markdown file to Google Drive as a Google Doc."""
    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

    config = load_config()
    credentials_path = config.get("gdrive_credentials")
    if not credentials_path:
        console.print("[red]Error:[/red] No credentials configured. Run: podojo gdrive setup <path-to-key.json>")
        raise typer.Exit(1)

    console.print(f"Uploading [bold]{file}[/bold]…", end=" ")
    _, url = upload_md_as_doc(str(file), credentials_path, title=title, folder_id=folder_id)
    console.print("[green]done[/green]")
    console.print(url)
