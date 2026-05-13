from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.table import Table

from ..client import PodojoClient

app = typer.Typer(help="Manage projects")
console = Console()

CLI_TO_API_DOC_TYPE = {
    "brief": "research_brief",
    "agent": "agent_report",
    "final": "final_report",
}
UPLOADABLE_DOC_TYPES = {"brief", "final"}
MARKDOWN_SUFFIXES = {".md", ".markdown"}


@app.command("list")
def list_projects(
    skip: int = typer.Option(0, help="Number of projects to skip"),
    limit: int = typer.Option(50, help="Max projects to return"),
):
    """List all projects."""
    client = PodojoClient()
    projects = client.list_projects(skip=skip, limit=limit)

    table = Table(title="Projects")
    table.add_column("Name")
    table.add_column("Brief")

    for p in projects:
        table.add_row(p.get("name", ""), p.get("brief", ""))

    console.print(table)


@app.command("create")
def create_project(
    name: str = typer.Argument(help="Project name"),
    brief: str = typer.Option("", "--brief", "-b", help="Short project description"),
):
    """Create a new empty project."""
    client = PodojoClient()
    try:
        result = client.create_project(name, brief)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            console.print(f"[red]Project '{name}' already exists.[/red]")
            raise typer.Exit(code=1)
        console.print(f"[red]{e.response.status_code}: {e.response.text}[/red]")
        raise typer.Exit(code=1)

    console.print(f"Created project [bold]{result['name']}[/bold] (id={result['id']})")


@app.command("upload-doc")
def upload_doc(
    project_name: str = typer.Argument(help="Project name"),
    file: Path = typer.Argument(
        help="Markdown file to upload",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    doc_type: str = typer.Option(
        ..., "--type", "-t",
        help="Document type: 'brief' (research brief) or 'final' (final report)",
    ),
):
    """Upload a research brief or final report markdown file to a project."""
    if doc_type not in UPLOADABLE_DOC_TYPES:
        console.print(f"[red]Error:[/red] --type must be one of: {', '.join(sorted(UPLOADABLE_DOC_TYPES))}")
        raise typer.Exit(1)

    if file.suffix.lower() not in MARKDOWN_SUFFIXES:
        console.print(f"[red]Error:[/red] Expected a .md file, got {file.suffix or '(no extension)'}")
        raise typer.Exit(1)

    try:
        content = file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        console.print(f"[red]Error:[/red] File is not valid UTF-8 text: {file}")
        raise typer.Exit(1)

    api_type = CLI_TO_API_DOC_TYPE[doc_type]
    client = PodojoClient()
    try:
        client.upload_project_document(project_name, api_type, content)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Project '{project_name}' not found.[/red]")
            raise typer.Exit(code=1)
        console.print(f"[red]{e.response.status_code}: {e.response.text}[/red]")
        raise typer.Exit(code=1)

    console.print(f"Uploaded [bold]{doc_type}[/bold] for project [bold]{project_name}[/bold]")


@app.command("get-doc")
def get_doc(
    project_name: str = typer.Argument(help="Project name"),
    doc_type: str = typer.Option(
        ..., "--type", "-t",
        help="Document type: 'brief', 'agent', or 'final'",
    ),
    output: Path = typer.Option(None, "--output", "-o", help="Save to file instead of stdout"),
):
    """Download a project document (research brief, agent report, or final report)."""
    if doc_type not in CLI_TO_API_DOC_TYPE:
        console.print(f"[red]Error:[/red] --type must be one of: {', '.join(sorted(CLI_TO_API_DOC_TYPE))}")
        raise typer.Exit(1)

    api_type = CLI_TO_API_DOC_TYPE[doc_type]
    client = PodojoClient()
    try:
        result = client.get_project_document(project_name, api_type)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Document not found.[/red]")
            raise typer.Exit(code=1)
        console.print(f"[red]{e.response.status_code}: {e.response.text}[/red]")
        raise typer.Exit(code=1)

    content = result.get("content", "")
    if output:
        output.write_text(content, encoding="utf-8")
        console.print(f"Saved to [bold]{output}[/bold]")
    else:
        console.print(content)
