import httpx
import typer
from rich.console import Console
from rich.table import Table

from ..client import PodojoClient

app = typer.Typer(help="Manage projects")
console = Console()


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
