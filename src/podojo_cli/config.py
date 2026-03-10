import os
from pathlib import Path

import tomllib


CONFIG_PATH = Path.home() / ".podojo.toml"


def load_config() -> dict:
    config = {}
    if CONFIG_PATH.exists():
        config = tomllib.loads(CONFIG_PATH.read_text())
    config.setdefault("base_url", os.getenv("PODOJO_BASE_URL", "http://localhost:8000"))
    config.setdefault("api_key", os.getenv("PODOJO_API_KEY", ""))
    return config
