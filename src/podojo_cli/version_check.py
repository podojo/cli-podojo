import json
import threading
from datetime import datetime, timedelta, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import httpx
from rich.console import Console

PACKAGE_NAME = "podojo-cli"
PYPI_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
CACHE_PATH = Path.home() / ".cache" / "podojo-cli" / "version.json"
CACHE_TTL = timedelta(hours=24)


def _current_version() -> str | None:
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return None


def _read_cache() -> dict | None:
    try:
        return json.loads(CACHE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _write_cache(data: dict) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(data))
    except OSError:
        pass


def _fetch_latest() -> None:
    try:
        resp = httpx.get(PYPI_URL, timeout=2.0)
        resp.raise_for_status()
        latest = resp.json()["info"]["version"]
        _write_cache(
            {"latest": latest, "checked_at": datetime.now(timezone.utc).isoformat()}
        )
    except (httpx.HTTPError, KeyError, ValueError):
        pass


def _is_newer(latest: str, current: str) -> bool:
    def parts(v: str) -> tuple[int, ...]:
        return tuple(int(x) for x in v.split(".") if x.isdigit())

    try:
        return parts(latest) > parts(current)
    except ValueError:
        return False


def check_for_update() -> None:
    current = _current_version()
    if current is None:
        return

    cache = _read_cache() or {}
    latest = cache.get("latest")
    checked_at_raw = cache.get("checked_at")

    needs_refresh = True
    if checked_at_raw:
        try:
            checked_at = datetime.fromisoformat(checked_at_raw)
            needs_refresh = datetime.now(timezone.utc) - checked_at > CACHE_TTL
        except ValueError:
            pass

    if latest and _is_newer(latest, current):
        Console(stderr=True).print(
            f"[yellow]Upgrade available: {current} → {latest}. "
            f"Run [bold]uv tool upgrade {PACKAGE_NAME}[/bold][/yellow]"
        )

    if needs_refresh:
        threading.Thread(target=_fetch_latest, daemon=True).start()
