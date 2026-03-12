import os
from pathlib import Path

import tomllib


CONFIG_PATH = Path.home() / ".podojo.toml"
DEFAULT_BASE_URL = "https://podojo-fastapi-mcp.onrender.com"


def load_config() -> dict:
    config = {}
    if CONFIG_PATH.exists():
        config = tomllib.loads(CONFIG_PATH.read_text())
    config.setdefault("base_url", os.getenv("PODOJO_BASE_URL", DEFAULT_BASE_URL))
    config.setdefault("api_key", os.getenv("PODOJO_API_KEY", ""))
    return config


def save_gdrive_credentials(path: str):
    config = {}
    if CONFIG_PATH.exists():
        config = tomllib.loads(CONFIG_PATH.read_text())
    config["gdrive_credentials"] = path
    lines = "\n".join(f'{k} = "{v}"' for k, v in config.items())
    CONFIG_PATH.write_text(lines + "\n")


def save_config(api_key: str):
    config = {}
    if CONFIG_PATH.exists():
        config = tomllib.loads(CONFIG_PATH.read_text())
    config["api_key"] = api_key
    config.setdefault("base_url", DEFAULT_BASE_URL)
    lines = "\n".join(f'{k} = "{v}"' for k, v in config.items())
    CONFIG_PATH.write_text(lines + "\n")


def clear_api_key():
    if not CONFIG_PATH.exists():
        return
    config = tomllib.loads(CONFIG_PATH.read_text())
    config.pop("api_key", None)
    if config:
        lines = "\n".join(f'{k} = "{v}"' for k, v in config.items())
        CONFIG_PATH.write_text(lines + "\n")
    else:
        CONFIG_PATH.unlink()
