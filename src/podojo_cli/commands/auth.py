import httpx
import typer
from rich.console import Console

from ..config import DEFAULT_BASE_URL, clear_api_key, load_config, save_config

app = typer.Typer(help="Authenticate with Podojo")
console = Console()


def _verify_key(api_key: str) -> bool:
    config = load_config()
    base_url = config["base_url"].rstrip("/") + "/api/v1"
    try:
        r = httpx.get(
            f"{base_url}/projects",
            params={"limit": 1},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        return r.status_code == 200
    except httpx.RequestError:
        return False


@app.command("login")
def login(
    api_key: str = typer.Option(
        None, "--key", "-k", help="Your Podojo API key (prompted if omitted)"
    ),
):
    """Save your API key and verify it works."""
    if not api_key:
        api_key = typer.prompt("API Key", hide_input=True)
    console.print("Verifying key…", end=" ")
    if not _verify_key(api_key):
        console.print("[red]failed[/red]")
        console.print("[red]Error:[/red] Invalid API key or could not reach the server.")
        raise typer.Exit(1)
    save_config(api_key)
    console.print("[green]done[/green]")
    console.print("[green]Logged in successfully.[/green]")


@app.command("logout")
def logout():
    """Remove the saved API key."""
    clear_api_key()
    console.print("Logged out.")
