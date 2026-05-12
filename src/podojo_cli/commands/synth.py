"""Synthetic usertest commands.

These commands provide thin primitives for driving a Playwright-controlled
browser. They're designed to be called in a loop by Claude Code (or another
agent) acting as a synthetic participant: each action prints the resulting
page state, including a screenshot path that the agent can read.
"""
from __future__ import annotations

import httpx
import typer
from rich.console import Console
from rich.markup import escape

from ..client import PodojoClient
from ..synth import session as synth_session

app = typer.Typer(help="Drive a synthetic usertest via a headless browser")
console = Console()


def _looks_like_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def _resolve_target(target: str) -> tuple[str, dict | None]:
    """Resolve target to (preview_url, usertest_dict).

    For a raw URL, usertest_dict is None (no API call). For a usertest_id, we
    fetch the full config so the caller can show a brief to the agent.
    """
    if _looks_like_url(target):
        return target, None
    client = PodojoClient()
    try:
        usertest = client.get_usertest(target)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error:[/red] User test '{target}' not found")
        else:
            console.print(f"[red]Error:[/red] {e.response.text}")
        raise typer.Exit(1)
    group = usertest.get("group")
    if not group:
        console.print(f"[red]Error:[/red] usertest '{target}' has no 'group'")
        raise typer.Exit(1)
    url = f"https://usertests.podojo.com/preview/{group}/{target}"
    return url, usertest


def _print_brief(usertest: dict) -> None:
    """Print a structured summary of the usertest so the agent can plan ahead."""
    title = usertest.get("title") or usertest.get("usertest_id") or "(untitled)"
    steps = usertest.get("steps") or []
    console.print(f"\n[bold]Usertest:[/bold] {escape(str(title))} ({len(steps)} steps)")

    welcome = (usertest.get("welcome_text") or "").strip()
    if welcome:
        console.print("\n[bold]Welcome text:[/bold]")
        for line in welcome.splitlines():
            console.print(f"  {escape(line)}")

    if steps:
        labels = [_step_label(s) for s in steps]
        width = max((len(l) for l in labels), default=0)
        console.print("\n[bold]Steps:[/bold]")
        for i, (step, label) in enumerate(zip(steps, labels), 1):
            step_title = step.get("title") if isinstance(step, dict) else ""
            console.print(
                f"  {i}. {label.ljust(width)}  — {escape(str(step_title or ''))}"
            )
    console.print()


def _step_label(step: object) -> str:
    if not isinstance(step, dict):
        return "?"
    step_type = step.get("type") or "?"
    if step_type == "screen":
        variant = step.get("variant")
        return f"screen/{variant}" if variant else "screen"
    return str(step_type)


def _print_state(state: dict) -> None:
    if "error" in state:
        console.print(f"[red]Driver error:[/red] {escape(str(state['error']))}")
        if "trace" in state:
            console.print(f"[dim]{escape(str(state['trace']))}[/dim]")
        return

    console.print(f"[bold]idx:[/bold]        {state.get('idx')}")
    if state.get("note"):
        console.print(f"[bold]note:[/bold]       {escape(str(state['note']))}")
    console.print(f"[bold]url:[/bold]        {escape(str(state.get('url', '')))}")
    console.print(f"[bold]title:[/bold]      {escape(str(state.get('title', '')))}")
    console.print(f"[bold]screenshot:[/bold] {escape(str(state.get('screenshot', '')))}")

    buttons = state.get("buttons") or []
    if buttons:
        console.print("\n[bold]buttons:[/bold]")
        for b in buttons:
            console.print(f"  - {escape(str(b))}")

    links = state.get("links") or []
    if links:
        console.print("\n[bold]links:[/bold]")
        for link in links:
            console.print(
                f"  - {escape(repr(link.get('text')))} -> "
                f"{escape(str(link.get('href')))}"
            )

    inputs = state.get("inputs") or []
    if inputs:
        console.print("\n[bold]inputs:[/bold]")
        for i in inputs:
            console.print(
                f"  - type={escape(str(i.get('type')))} "
                f"name={escape(str(i.get('name')))} "
                f"placeholder={escape(repr(i.get('placeholder')))} "
                f"value={escape(repr(i.get('value')))}"
            )

    iframes = state.get("iframes") or []
    if iframes:
        console.print("\n[bold]iframes:[/bold]")
        for f in iframes:
            console.print(
                f"  - {escape(repr(f.get('name')))} {escape(str(f.get('url')))}"
            )

    text = (state.get("text") or "").strip()
    if text:
        console.print("\n[bold]body text (truncated):[/bold]")
        console.print(escape(text[:2000]))


def _send(cmd: dict) -> None:
    try:
        state = synth_session.send_command(cmd)
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except TimeoutError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    _print_state(state)


@app.command("start")
def start(
    target: str = typer.Argument(help="usertest_id or preview URL"),
    headed: bool = typer.Option(False, "--headed", help="show the browser window"),
):
    """Start a synth session against a usertest preview URL."""
    url, usertest = _resolve_target(target)
    if usertest is not None:
        _print_brief(usertest)
    console.print(f"[dim]Loading {url}[/dim]")
    try:
        pid = synth_session.start_driver(url, headed=headed)
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    try:
        state = synth_session.wait_for_initial_state()
    except (RuntimeError, TimeoutError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    console.print(f"[green]Driver started[/green] (pid {pid})")
    _print_state(state)


@app.command("state")
def state():
    """Print the current page state without performing any action."""
    if not synth_session.driver_running():
        console.print("[red]Error:[/red] No synth session is running.")
        raise typer.Exit(1)
    s = synth_session.read_state()
    if s is None:
        console.print("[yellow]No state yet.[/yellow]")
        raise typer.Exit(1)
    _print_state(s)


@app.command("click")
def click(
    text: str = typer.Argument(help="visible text of the element to click"),
    exact: bool = typer.Option(False, "--exact", help="require exact text match"),
):
    """Click an element by its visible text."""
    _send({"op": "click_text", "text": text, "exact": exact})


@app.command("click-role")
def click_role(
    role: str = typer.Argument(help="ARIA role (e.g. button, link, textbox)"),
    name: str = typer.Argument(help="accessible name"),
    exact: bool = typer.Option(False, "--exact", help="require exact name match"),
):
    """Click an element by ARIA role + accessible name."""
    _send({"op": "click_role", "role": role, "name": name, "exact": exact})


@app.command("click-css")
def click_css(
    selector: str = typer.Argument(help="CSS selector"),
):
    """Click an element by CSS selector."""
    _send({"op": "click_selector", "selector": selector})


@app.command("click-xy")
def click_xy(
    x: int = typer.Argument(help="x coordinate"),
    y: int = typer.Argument(help="y coordinate"),
):
    """Click at viewport coordinates (use when nothing else works)."""
    _send({"op": "click_xy", "x": x, "y": y})


@app.command("frame-click-xy")
def frame_click_xy(
    x: int = typer.Argument(help="x coordinate inside the prototype iframe"),
    y: int = typer.Argument(help="y coordinate inside the prototype iframe"),
):
    """Click coordinates inside the first non-main iframe (e.g. Figma prototype)."""
    _send({"op": "frame_click_xy", "x": x, "y": y})


@app.command("fill")
def fill(
    selector: str = typer.Argument(help="CSS selector of the input"),
    value: str = typer.Argument(help="value to fill in"),
):
    """Fill an input/textarea by CSS selector."""
    _send({"op": "fill", "selector": selector, "value": value})


@app.command("fill-role")
def fill_role(
    role: str = typer.Argument(help="ARIA role (e.g. textbox)"),
    name: str = typer.Argument(help="accessible name"),
    value: str = typer.Argument(help="value to fill in"),
):
    """Fill an input by ARIA role + accessible name."""
    _send({"op": "fill_role", "role": role, "name": name, "value": value})


@app.command("type")
def type_text(
    text: str = typer.Argument(help="text to type at the current focus"),
):
    """Type text at the current keyboard focus."""
    _send({"op": "type", "text": text})


@app.command("press")
def press(
    key: str = typer.Argument(help="key name (e.g. Enter, Tab, Escape)"),
):
    """Press a keyboard key."""
    _send({"op": "press", "key": key})


@app.command("wait")
def wait(
    seconds: float = typer.Argument(2.0, help="seconds to wait"),
):
    """Pause for N seconds, then take a fresh screenshot."""
    _send({"op": "wait", "seconds": seconds})


@app.command("screenshot")
def screenshot():
    """Take a fresh screenshot of the current page."""
    _send({"op": "screenshot"})


@app.command("reload")
def reload():
    """Reload the current page."""
    _send({"op": "reload"})


@app.command("goto")
def goto(
    url: str = typer.Argument(help="URL to navigate to"),
):
    """Navigate the browser to a URL."""
    _send({"op": "goto", "url": url})


@app.command("advance")
def advance(
    times: int = typer.Argument(1, help="how many step buttons to click"),
):
    """Auto-click 'Done with Step' / 'Continue' N times to fast-forward."""
    _send({"op": "advance", "times": times})


@app.command("stop")
def stop():
    """Stop the running synth session and tear down the browser."""
    if not synth_session.driver_running():
        console.print("[dim]No synth session is running.[/dim]")
        return
    synth_session.stop_driver()
    console.print("[green]Stopped synth session.[/green]")
