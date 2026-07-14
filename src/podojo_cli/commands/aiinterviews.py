from pathlib import Path

import httpx
import typer
import yaml
from rich.console import Console
from rich.table import Table

from ..client import PodojoClient
from ..config import load_config

app = typer.Typer(help="Manage AI voice interviews")
console = Console()

REQUIRED_FIELDS = ["interview_id", "title", "questions", "closing_message"]
REQUIRED_QUESTION_FIELDS = ["text"]

EXAMPLE_YAML = """\
# Podojo AI Interview Configuration
#
# One file = one study. This YAML is the source of truth: editing it edits the
# interview. The AI interviewer conducts a voice conversation built from the
# questions below.
#
# Required fields: interview_id, title, questions, closing_message
# Optional fields: language (default en-US), project_name, overview,
#                  decision, screening_questions, welcome_message,
#                  rejection_message, live, collect_contact
#
# Each question:
#   text            (required) the main question, asked verbatim-ish in order
#   section         (optional) researcher-facing grouping label
#   max_follow_ups  (optional, default 2) adaptive follow-up budget
#   probe_for       (optional) what a concrete answer must cover — drives follow-ups
#
# Each screening question (optional participant screener, answered on screen
# before the voice interview starts):
#   text            (required) multiple-choice question
#   multi_select    (optional, default false) participants can pick several
#                   options; one qualifying pick passes the question
#   options         (required, at least 2) each with `text` and an optional
#                   `qualifies: true` — participants must pick a qualifying
#                   option on every question, otherwise they see the
#                   rejection_message and the interview never starts

interview_id: checkout-experience-v1
title: Checkout Experience Research
language: en-US

# Optional: link interview to a project
project_name: checkout-redesign-q1

# Optional: research context that grounds the interviewer's follow-ups
overview: |
  We're redesigning the checkout flow of our online store. This study targets
  recent customers to understand how they decide what to buy, what slows them
  down during checkout, and what would make them complete a purchase.

  Key questions:
  - How do customers move from browsing to buying?
  - What friction shows up during checkout (payment, shipping, account creation)?
  - What would make customers abandon a purchase at the last step?

# Optional: the decision this research informs
decision: >
  Redesign the checkout flow to reduce cart abandonment.

# Optional: intro paragraph on the welcome page, below the study title
welcome_message: >
  Thanks for joining! We'd like to have a short, friendly conversation about
  your experience. There are no right or wrong answers — just talk naturally.

# Optional: set interview live (default: false)
# live: true

# Optional: collect participant name/email on a dedicated screen after the
# interview (default: false)
# collect_contact: true

# Optional: participant screener — shown on screen (no audio) before the
# conversation. Answers are captured alongside the session's recording.
screening_questions:
  - text: How often do you shop online?
    options:
      - text: Rarely or never
      - text: A few times a year
      - text: At least once a month
        qualifies: true
      - text: Weekly or more
        qualifies: true

  - text: Have you abandoned an online purchase at checkout in the past 3 months?
    options:
      - text: "Yes"
        qualifies: true
      - text: "No"
      - text: Not sure

  - text: Which devices do you use to shop online?
    multi_select: true
    options:
      - text: Phone
        qualifies: true
      - text: Laptop or desktop
        qualifies: true
      - text: I don't shop online

# Optional: shown to participants whose screener answers don't qualify
rejection_message: >
  Thank you for your time, you did not meet the research criteria for this
  study!

questions:
  - section: Shopping Habits
    text: >
      Think about the last time you bought something online. Walk me through
      how you went from finding the product to completing the purchase.
    max_follow_ups: 3
    probe_for: >
      Specific steps taken (search, comparison, reviews), devices used, and
      anything that slowed them down or almost made them give up.

  - section: Checkout Friction
    text: >
      Think about a time you abandoned an online purchase at checkout.
      What made you stop?
    max_follow_ups: 3
    probe_for: >
      Unexpected costs, forced account creation, missing payment options,
      delivery times. Ask what would have changed their mind.

  - section: Checkout Friction
    text: >
      When you reach a checkout page, what's the first thing you look at
      before entering your details?
    max_follow_ups: 1

closing_message: >
  Thank you for sharing your experience! Your feedback is incredibly valuable
  and will help us improve the shopping experience.
"""


def validate_ai_interview_data(data: dict) -> list[str]:
    """Validate AI interview YAML data, return list of error strings."""
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None:
            errors.append(f"Missing required field: '{field}'")

    questions = data.get("questions")
    if questions is not None:
        if not isinstance(questions, list):
            errors.append("'questions' must be a list")
        elif len(questions) == 0:
            errors.append("'questions' must contain at least one question")
        else:
            for i, question in enumerate(questions, 1):
                if not isinstance(question, dict):
                    errors.append(f"Question {i}: must be a mapping with 'text'")
                    continue
                for field in REQUIRED_QUESTION_FIELDS:
                    if field not in question:
                        errors.append(f"Question {i}: missing required field '{field}'")
                max_follow_ups = question.get("max_follow_ups")
                if max_follow_ups is not None and (
                    isinstance(max_follow_ups, bool)
                    or not isinstance(max_follow_ups, int)
                    or max_follow_ups < 0
                ):
                    errors.append(
                        f"Question {i}: 'max_follow_ups' must be an integer >= 0, got '{max_follow_ups}'"
                    )

    screening_questions = data.get("screening_questions")
    if screening_questions is not None:
        if not isinstance(screening_questions, list):
            errors.append("'screening_questions' must be a list")
        else:
            for i, question in enumerate(screening_questions, 1):
                if not isinstance(question, dict) or "text" not in question:
                    errors.append(f"Screening question {i}: must be a mapping with 'text'")
                    continue
                multi_select = question.get("multi_select", False)
                if not isinstance(multi_select, bool):
                    errors.append(
                        f"Screening question {i}: 'multi_select' must be true or false"
                    )
                options = question.get("options")
                if not isinstance(options, list) or len(options) < 2:
                    errors.append(f"Screening question {i}: 'options' must list at least 2 options")
                    continue
                qualifying = 0
                for j, option in enumerate(options, 1):
                    if not isinstance(option, dict) or "text" not in option:
                        errors.append(
                            f"Screening question {i}, option {j}: must be a mapping with 'text'"
                        )
                        continue
                    qualifies = option.get("qualifies", False)
                    if not isinstance(qualifies, bool):
                        errors.append(
                            f"Screening question {i}, option {j}: 'qualifies' must be true or false"
                        )
                    elif qualifies:
                        qualifying += 1
                if qualifying == 0:
                    errors.append(
                        f"Screening question {i}: needs at least one option with 'qualifies: true'"
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


def _ai_interviews_url() -> str:
    return load_config()["ai_interviews_url"].rstrip("/")


@app.command("list")
def list_ai_interviews(
    skip: int = typer.Option(0, help="Number of AI interviews to skip"),
    limit: int = typer.Option(50, help="Max AI interviews to return"),
):
    """List all AI interviews."""
    client = PodojoClient()
    try:
        result = client.list_ai_interviews(skip=skip, limit=limit)
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error:[/red] {_format_api_error(e)}")
        raise typer.Exit(1)

    ai_interviews = result.get("ai_interviews", [])
    if not ai_interviews:
        console.print("No AI interviews found.")
        return

    table = Table(title="AI Interviews")
    table.add_column("Interview ID")
    table.add_column("Title")
    table.add_column("Language")
    table.add_column("Questions", justify="right")
    table.add_column("Live")
    table.add_column("Last Updated")

    for s in ai_interviews:
        live = "[green]Yes[/green]" if s.get("live") else "[dim]No[/dim]"
        table.add_row(
            s.get("interview_id", ""),
            s.get("title", ""),
            s.get("language", ""),
            str(s.get("question_count", "")),
            live,
            s.get("last_updated", ""),
        )

    console.print(table)


@app.command("get")
def get_ai_interview(
    interview_id: str = typer.Argument(help="AI interview ID to retrieve"),
):
    """Get an AI interview and output as YAML."""
    client = PodojoClient()
    try:
        interview = client.get_ai_interview(interview_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error:[/red] AI interview '{interview_id}' not found")
        else:
            console.print(f"[red]Error:[/red] {_format_api_error(e)}")
        raise typer.Exit(1)

    # Remove server-managed fields for a clean editable output
    group = interview.pop("group", "")
    for key in ("id", "created_at", "created_by", "last_updated"):
        interview.pop(key, None)

    console.print(yaml.dump(interview, default_flow_style=False, sort_keys=False, allow_unicode=True))
    if group:
        base = _ai_interviews_url()
        console.print(f"Preview: {base}/preview/{group}/{interview_id}")
        console.print(f"Live:    {base}/{group}/{interview_id}")


@app.command("create")
def create_ai_interview(
    from_file: Path = typer.Option(..., "--from-file", "-f", help="YAML file with AI interview config"),
):
    """Create a new AI interview from a YAML file."""
    data = _load_yaml(from_file)

    errors = validate_ai_interview_data(data)
    if errors:
        console.print("[red]Validation errors:[/red]")
        for err in errors:
            console.print(f"  {err}")
        raise typer.Exit(1)

    client = PodojoClient()
    try:
        result = client.create_ai_interview(data)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            console.print(f"[red]Error:[/red] AI interview '{data.get('interview_id')}' already exists")
        else:
            console.print(f"[red]Error:[/red] {_format_api_error(e)}")
        raise typer.Exit(1)

    interview_id = result.get("interview_id", "")
    group = result.get("group", "")
    console.print(f"[green]Created AI interview:[/green] {interview_id}")
    if group:
        base = _ai_interviews_url()
        console.print(f"  Preview: {base}/preview/{group}/{interview_id}")
        console.print(f"  Live:    {base}/{group}/{interview_id}")


@app.command("update")
def update_ai_interview(
    interview_id: str = typer.Argument(help="AI interview ID to update"),
    from_file: Path = typer.Option(..., "--from-file", "-f", help="YAML file with fields to update"),
):
    """Update an AI interview from a YAML file (partial updates OK)."""
    data = _load_yaml(from_file)

    client = PodojoClient()
    try:
        result = client.update_ai_interview(interview_id, data)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error:[/red] AI interview '{interview_id}' not found")
        else:
            console.print(f"[red]Error:[/red] {_format_api_error(e)}")
        raise typer.Exit(1)

    console.print(f"[green]Updated AI interview:[/green] {result.get('interview_id', interview_id)}")


@app.command("delete")
def delete_ai_interview(
    interview_id: str = typer.Argument(help="AI interview ID to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete an AI interview."""
    if not yes:
        typer.confirm(f"Delete AI interview '{interview_id}'?", abort=True)

    client = PodojoClient()
    try:
        client.delete_ai_interview(interview_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error:[/red] AI interview '{interview_id}' not found")
        else:
            console.print(f"[red]Error:[/red] {_format_api_error(e)}")
        raise typer.Exit(1)

    console.print(f"[green]Deleted AI interview:[/green] {interview_id}")


@app.command("validate")
def validate(
    file: Path = typer.Argument(help="YAML file to validate"),
):
    """Validate an AI interview YAML file without creating it."""
    data = _load_yaml(file)

    errors = validate_ai_interview_data(data)
    if errors:
        console.print("[red]Validation errors:[/red]")
        for err in errors:
            console.print(f"  {err}")
        raise typer.Exit(1)

    console.print("[green]Valid AI interview config.[/green]")


@app.command("example")
def example():
    """Print an example AI interview YAML template."""
    print(EXAMPLE_YAML)
