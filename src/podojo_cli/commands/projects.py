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
