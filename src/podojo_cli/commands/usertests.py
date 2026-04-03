from pathlib import Path

import httpx
import typer
import yaml
from rich.console import Console
from rich.table import Table

from ..client import PodojoClient

app = typer.Typer(help="Manage unmoderated user tests")
console = Console()

REQUIRED_FIELDS = ["usertest_id", "client", "title", "logo", "prototype_url", "steps"]
VALID_STEP_TYPES = {"screen", "prototype"}
VALID_STEP_VARIANTS = {"question", "task"}
REQUIRED_STEP_FIELDS = ["type", "title"]

EXAMPLE_YAML = """\
# Podojo Unmoderated User Test Configuration
#
# Required fields: usertest_id, client, title, logo, prototype_url, steps
# Optional fields: welcome_text, privacy_text, promo_code, promo_code_info, project_name

usertest_id: checkout-usability-v1
client: Acme Corp
title: Checkout Flow Usability Test
logo: https://example.com/logo.png
prototype_url: https://figma.com/proto/abc123

# Optional: welcome message shown to participants (supports markdown)
welcome_text: |
  ## Welcome to our study!

  We're testing a new checkout flow. There are no right or wrong
  answers -- we want to understand your experience.

  This session takes about 10 minutes.

# Optional: privacy notice
privacy_text: |
  Your responses are anonymous and will only be used to improve
  our product. You can stop at any time.

# Optional: reward for participants
promo_code: THANKS10
promo_code_info: "Use this code for 10% off your next purchase"

# Optional: link user test to a project
project_name: checkout-redesign-q1

# Optional: set user test live (default: false)
# live: true

# Steps define what participants see and do
# Each step requires: type ("screen" or "prototype") and title
# Screen steps should have a variant: "question" (open-ended) or "task" (action-based)
# Optional per step: text (markdown), image (URL)
steps:
  - type: screen
    variant: question
    title: First Impressions
    text: |
      Look at this homepage screenshot.
      What stands out to you first?
    image: https://example.com/screenshots/homepage.png

  - type: prototype
    title: Complete a Purchase
    text: |
      Using the prototype below, try to buy a pair of running shoes.
      Think aloud as you go through each step.

  - type: screen
    variant: task
    title: Find the Return Policy
    text: |
      Without using search, try to find the return policy page.
      Describe where you would click.

  - type: screen
    variant: question
    title: Overall Experience
    text: |
      On a scale of 1-5, how easy was the checkout process?
      What would you improve?
"""


def validate_usertest_data(data: dict) -> list[str]:
    """Validate user test YAML data, return list of error strings."""
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None:
            errors.append(f"Missing required field: '{field}'")

    steps = data.get("steps")
    if steps is not None:
        if not isinstance(steps, list):
            errors.append("'steps' must be a list")
        elif len(steps) == 0:
            errors.append("'steps' must contain at least one step")
        else:
            for i, step in enumerate(steps, 1):
                if not isinstance(step, dict):
                    errors.append(f"Step {i}: must be a mapping with 'type' and 'title'")
                    continue
                for field in REQUIRED_STEP_FIELDS:
                    if field not in step:
                        errors.append(f"Step {i}: missing required field '{field}'")
                step_type = step.get("type")
                if step_type not in VALID_STEP_TYPES:
                    errors.append(
                        f"Step {i}: 'type' must be 'screen' or 'prototype', got '{step_type}'"
                    )
                variant = step.get("variant")
                if step_type == "screen" and variant is not None and variant not in VALID_STEP_VARIANTS:
                    errors.append(
                        f"Step {i}: 'variant' must be 'question' or 'task', got '{variant}'"
                    )
    return errors


def _load_yaml(path: Path) -> dict:
    """Load and parse YAML file."""
    if not path.exists():
        console.print(f"[red]Error:[/red] File not found: {path}")
        raise typer.Exit(1)
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        console.print(f"[red]Error:[/red] Invalid YAML syntax:\n{e}")
        raise typer.Exit(1)
    if not isinstance(data, dict):
        console.print("[red]Error:[/red] YAML file must contain a mapping (key-value pairs)")
        raise typer.Exit(1)
    return data


def _format_api_error(e: httpx.HTTPStatusError) -> str:
    """Format API error into actionable message."""
    try:
        detail = e.response.json().get("detail", "")
        if isinstance(detail, list):
            messages = []
            for err in detail:
                loc = " -> ".join(str(x) for x in err.get("loc", []))
                messages.append(f"  {loc}: {err.get('msg', '')}")
            return "Validation errors:\n" + "\n".join(messages)
        return str(detail)
    except Exception:
        return e.response.text


@app.command("list")
def list_usertests(
    skip: int = typer.Option(0, help="Number of user tests to skip"),
    limit: int = typer.Option(50, help="Max user tests to return"),
):
    """List all user tests."""
    client = PodojoClient()
    try:
        result = client.list_usertests(skip=skip, limit=limit)
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error:[/red] {_format_api_error(e)}")
        raise typer.Exit(1)

    usertests = result.get("usertests", [])
    if not usertests:
        console.print("No user tests found.")
        return

    table = Table(title="User Tests")
    table.add_column("User Test ID")
    table.add_column("Title")
    table.add_column("Client")
    table.add_column("Steps", justify="right")
    table.add_column("Live")
    table.add_column("Last Updated")

    for s in usertests:
        live = "[green]Yes[/green]" if s.get("live") else "[dim]No[/dim]"
        table.add_row(
            s.get("usertest_id", ""),
            s.get("title", ""),
            s.get("client", ""),
            str(s.get("step_count", "")),
            live,
            s.get("last_updated", ""),
        )

    console.print(table)


@app.command("get")
def get_usertest(
    usertest_id: str = typer.Argument(help="User test ID to retrieve"),
):
    """Get a user test and output as YAML."""
    client = PodojoClient()
    try:
        usertest = client.get_usertest(usertest_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error:[/red] User test '{usertest_id}' not found")
        else:
            console.print(f"[red]Error:[/red] {_format_api_error(e)}")
        raise typer.Exit(1)

    # Remove server-managed fields for a clean editable output
    for key in ("id", "created_at", "created_by", "last_updated"):
        usertest.pop(key, None)

    console.print(yaml.dump(usertest, default_flow_style=False, sort_keys=False, allow_unicode=True))


@app.command("create")
def create_usertest(
    from_file: Path = typer.Option(..., "--from-file", "-f", help="YAML file with user test config"),
):
    """Create a new user test from a YAML file."""
    data = _load_yaml(from_file)

    errors = validate_usertest_data(data)
    if errors:
        console.print("[red]Validation errors:[/red]")
        for err in errors:
            console.print(f"  {err}")
        raise typer.Exit(1)

    if "project_name" not in data:
        data["project_name"] = data["usertest_id"]

    client = PodojoClient()
    try:
        result = client.create_usertest(data)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            console.print(f"[red]Error:[/red] User test '{data.get('usertest_id')}' already exists")
        else:
            console.print(f"[red]Error:[/red] {_format_api_error(e)}")
        raise typer.Exit(1)

    console.print(f"[green]Created user test:[/green] {result.get('usertest_id', '')}")


@app.command("update")
def update_usertest(
    usertest_id: str = typer.Argument(help="User test ID to update"),
    from_file: Path = typer.Option(..., "--from-file", "-f", help="YAML file with fields to update"),
):
    """Update a user test from a YAML file (partial updates OK)."""
    data = _load_yaml(from_file)

    client = PodojoClient()
    try:
        result = client.update_usertest(usertest_id, data)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error:[/red] User test '{usertest_id}' not found")
        else:
            console.print(f"[red]Error:[/red] {_format_api_error(e)}")
        raise typer.Exit(1)

    console.print(f"[green]Updated user test:[/green] {result.get('usertest_id', usertest_id)}")


@app.command("delete")
def delete_usertest(
    usertest_id: str = typer.Argument(help="User test ID to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete a user test."""
    if not yes:
        typer.confirm(f"Delete user test '{usertest_id}'?", abort=True)

    client = PodojoClient()
    try:
        client.delete_usertest(usertest_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error:[/red] User test '{usertest_id}' not found")
        else:
            console.print(f"[red]Error:[/red] {_format_api_error(e)}")
        raise typer.Exit(1)

    console.print(f"[green]Deleted user test:[/green] {usertest_id}")


@app.command("validate")
def validate(
    file: Path = typer.Argument(help="YAML file to validate"),
):
    """Validate a user test YAML file without creating it."""
    data = _load_yaml(file)

    errors = validate_usertest_data(data)
    if errors:
        console.print("[red]Validation errors:[/red]")
        for err in errors:
            console.print(f"  {err}")
        raise typer.Exit(1)

    console.print("[green]Valid user test config.[/green]")


@app.command("example")
def example():
    """Print an example user test YAML template."""
    print(EXAMPLE_YAML)
