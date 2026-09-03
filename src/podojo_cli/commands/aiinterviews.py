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

REQUIRED_FIELDS = ["interview_id", "title", "questions"]
REQUIRED_QUESTION_FIELDS = ["text"]

EXAMPLE_YAML = """\
# Podojo AI Interview Configuration
#
# One file = one study. This YAML is the source of truth: editing it edits the
# interview. The AI interviewer conducts a voice conversation built from the
# questions below. The participant app ends every interview with a fixed
# thank-you screen — no closing text to author.
#
# Required fields: interview_id, title, questions
# Optional fields: language (default en-US), project_name, overview,
#                  decision, screening_questions, welcome_message,
#                  rejection_message, live, collect_contact, max_responses
#
# Each question:
#   text            (required) the main question, asked verbatim-ish in order
#   section         (optional) researcher-facing grouping label
#   max_follow_ups  (optional, default 2) adaptive follow-up budget
#   probe_for       (optional) what a concrete answer must cover — drives follow-ups
#   image / image_file (optional) show participants an image alongside the
#                   question -- either:
#     image:      a URL to an externally-hosted image, or
#     image_file: a path to a local image (uploaded to Podojo storage on
#                 create/update; relative paths resolve against this YAML
#                 file's location)
#
# Each screening question (optional closed questions, answered on screen
# before the voice interview starts; answers are recorded with the session):
#   text            (required) multiple-choice question
#   multi_select    (optional, default false) participants can pick several
#                   options
#   screener        (optional, default false) the question screens: participants
#                   must pick an option with `qualifies: true`, otherwise they
#                   see the rejection_message and the interview never starts
#   show_if         (optional) show this question only if an earlier screening
#                   question was answered with one of the given options, e.g.
#                   `show_if: {question: 0, options: [1, 2]}` — 0-based indices
#                   into screening_questions and that question's options
#   options         (required, at least 2) each with `text`; `qualifies: true`
#                   marks the accepted answers of a screener question and is
#                   ignored on plain closed questions

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

# Optional: collect participant name, email and country on a dedicated
# incentive screen after the interview (default: true). Set false to skip it.
# collect_contact: false

# Optional: close the interview automatically once this many participants have
# completed a session (default: unlimited). The interview goes off live and new
# visitors see "not available"; participants already mid-conversation still
# finish, so the final count can slightly exceed this number. To collect more
# responses later, raise max_responses and set live: true again.
# max_responses: 20

# Optional: closed questions — shown on screen (no audio) before the
# conversation. Answers are captured alongside the session's recording; only
# questions marked `screener: true` can screen participants out.
screening_questions:
  - text: How often do you shop online?
    options:
      - text: Rarely or never
      - text: A few times a year
      - text: At least once a month
      - text: Weekly or more

  - text: Have you abandoned an online purchase at checkout in the past 3 months?
    screener: true
    options:
      - text: "Yes"
        qualifies: true
      - text: "No"
      - text: Not sure

  # Asked only when the previous question (index 1) was answered "Yes" (option 0)
  - text: What made you abandon the purchase?
    multi_select: true
    show_if:
      question: 1
      options: [0]
    options:
      - text: Unexpected costs
      - text: Forced account creation
      - text: Missing payment options
      - text: Delivery time

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
      Look at this checkout page. What's the first thing you look at
      before entering your details?
    max_follow_ups: 1
    image_file: ./screenshots/checkout-page.png
"""


def validate_ai_interview_data(data: dict) -> list[str]:
    """Validate AI interview YAML data, return list of error strings."""
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None:
            errors.append(f"Missing required field: '{field}'")

    max_responses = data.get("max_responses")
    if max_responses is not None and (
        isinstance(max_responses, bool) or not isinstance(max_responses, int) or max_responses < 1
    ):
        errors.append("'max_responses' must be a positive integer")

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
                screener = question.get("screener", False)
                if not isinstance(screener, bool):
                    errors.append(f"Screening question {i}: 'screener' must be true or false")
                    screener = False
                show_if = question.get("show_if")
                if show_if is not None:
                    if not isinstance(show_if, dict):
                        errors.append(
                            f"Screening question {i}: 'show_if' must be a mapping with "
                            "'question' and 'options'"
                        )
                    else:
                        ref = show_if.get("question")
                        if isinstance(ref, bool) or not isinstance(ref, int) or not 0 <= ref < i - 1:
                            errors.append(
                                f"Screening question {i}: 'show_if.question' must be the 0-based "
                                "index of an earlier screening question"
                            )
                            ref = None
                        ref_options = show_if.get("options")
                        if not isinstance(ref_options, list) or len(ref_options) == 0:
                            errors.append(
                                f"Screening question {i}: 'show_if.options' must list at least "
                                "one option index"
                            )
                        elif ref is not None:
                            trigger = screening_questions[ref]
                            trigger_options = (
                                trigger.get("options") if isinstance(trigger, dict) else None
                            )
                            limit = len(trigger_options) if isinstance(trigger_options, list) else 0
                            for index in ref_options:
                                if (
                                    isinstance(index, bool)
                                    or not isinstance(index, int)
                                    or not 0 <= index < limit
                                ):
                                    errors.append(
                                        f"Screening question {i}: 'show_if.options' index "
                                        f"{index} is out of range for screening question {ref + 1}"
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
                if screener and qualifying == 0:
                    errors.append(
                        f"Screening question {i}: needs at least one option with 'qualifies: true'"
                    )
                if not screener and 0 < qualifying < len(options):
                    errors.append(
                        f"Screening question {i}: has non-qualifying options but no "
                        "'screener: true' — set it, or drop the 'qualifies' flags"
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


def _resolve_image_files(data: dict, base_dir: Path, client: PodojoClient) -> None:
    """Upload any question `image_file` (local path) and replace it with the hosted URL."""
    questions = data.get("questions")
    if not isinstance(questions, list):
        return
    for i, question in enumerate(questions, 1):
        if not isinstance(question, dict) or "image_file" not in question:
            continue
        raw_path = question.pop("image_file")
        if not raw_path:
            continue
        image_path = Path(raw_path)
        if not image_path.is_absolute():
            image_path = (base_dir / image_path).resolve()
        if not image_path.exists():
            console.print(f"[red]Error:[/red] Question {i}: image file not found: {image_path}")
            raise typer.Exit(1)
        try:
            result = client.upload_ai_interview_image(image_path)
        except ValueError as ve:
            console.print(f"[red]Error:[/red] Question {i}: {ve}")
            raise typer.Exit(1)
        except httpx.HTTPStatusError as he:
            console.print(f"[red]Error:[/red] Question {i}: image upload failed: {_format_api_error(he)}")
            raise typer.Exit(1)
        question["image"] = result["url"]
        console.print(f"[dim]Uploaded image for question {i}: {result['url']}[/dim]")


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
    table.add_column("Responses", justify="right")
    table.add_column("Last Updated")

    for s in ai_interviews:
        live = "[green]Yes[/green]" if s.get("live") else "[dim]No[/dim]"
        count = s.get("response_count") or 0
        max_responses = s.get("max_responses")
        responses = f"{count} / {max_responses}" if max_responses else str(count)
        table.add_row(
            s.get("interview_id", ""),
            s.get("title", ""),
            s.get("language", ""),
            str(s.get("question_count", "")),
            live,
            responses,
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
    response_count = interview.pop("response_count", 0) or 0
    for key in ("id", "created_at", "created_by", "last_updated"):
        interview.pop(key, None)

    console.print(yaml.dump(interview, default_flow_style=False, sort_keys=False, allow_unicode=True))
    max_responses = interview.get("max_responses")
    if max_responses:
        console.print(f"Responses: {response_count} / {max_responses}")
    elif response_count:
        console.print(f"Responses: {response_count}")
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
    _resolve_image_files(data, from_file.parent, client)
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
    _resolve_image_files(data, from_file.parent, client)
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
