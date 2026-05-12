"""Session management for the synthetic usertest driver.

A "session" is a single running driver subprocess with state in
~/.podojo/synth/. v1 supports one session at a time.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

SESSION_DIR = Path.home() / ".podojo" / "synth"
PID_FILE = SESSION_DIR / "driver.pid"
CMD_FILE = SESSION_DIR / "cmd.json"
STATE_FILE = SESSION_DIR / "state.json"
START_TIMEOUT_S = 60.0
COMMAND_TIMEOUT_S = 30.0


def ensure_session_dir() -> Path:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return SESSION_DIR


def read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def driver_running() -> bool:
    pid = read_pid()
    return pid is not None and is_alive(pid)


def start_driver(url: str, headed: bool = False) -> int:
    """Start the driver subprocess. Returns its PID. Raises if already running."""
    if driver_running():
        raise RuntimeError(
            "A synth session is already running. Run 'podojo synth stop' first."
        )
    ensure_session_dir()
    CMD_FILE.unlink(missing_ok=True)
    STATE_FILE.unlink(missing_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "podojo_cli.synth.driver",
        "--url",
        url,
        "--session-dir",
        str(SESSION_DIR),
    ]
    if headed:
        cmd.append("--headed")

    log_path = SESSION_DIR / "driver.log"
    log = log_path.open("ab")
    proc = subprocess.Popen(
        cmd,
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    PID_FILE.write_text(str(proc.pid))
    return proc.pid


def stop_driver() -> bool:
    """Stop a running driver. Returns True if a process was signaled."""
    pid = read_pid()
    if pid is None:
        return False
    send_command({"op": "quit"}, expect_state=False)
    time.sleep(0.5)
    if is_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        time.sleep(0.5)
    if is_alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    PID_FILE.unlink(missing_ok=True)
    CMD_FILE.unlink(missing_ok=True)
    return True


def read_state() -> dict | None:
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def wait_for_state(min_idx: int, timeout_s: float) -> dict:
    """Wait until state.json has idx > min_idx (or an error). Returns the state."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        state = read_state()
        if state is not None:
            if "error" in state and state.get("idx", -1) >= min_idx:
                return state
            if state.get("idx", -1) > min_idx:
                return state
        time.sleep(0.2)
    raise TimeoutError(f"timed out after {timeout_s:.0f}s waiting for driver")


def send_command(cmd: dict, expect_state: bool = True) -> dict:
    """Write a command and (optionally) wait for the resulting state."""
    if not driver_running():
        raise RuntimeError(
            "No synth session is running. Start one with 'podojo synth start ...'."
        )
    prev = read_state() or {}
    prev_idx = prev.get("idx", -1)
    CMD_FILE.write_text(json.dumps(cmd))
    if not expect_state:
        return {}
    return wait_for_state(prev_idx, COMMAND_TIMEOUT_S)


def wait_for_initial_state() -> dict:
    """After starting the driver, wait for the first state dump."""
    deadline = time.monotonic() + START_TIMEOUT_S
    while time.monotonic() < deadline:
        state = read_state()
        if state is not None:
            return state
        if not driver_running():
            log = (SESSION_DIR / "driver.log").read_text() if (SESSION_DIR / "driver.log").exists() else ""
            raise RuntimeError(f"driver exited before producing state.\n{log}")
        time.sleep(0.3)
    raise TimeoutError("driver did not produce initial state in time")
