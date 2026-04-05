import os
from pathlib import Path

import keyring
import tomllib

KEYRING_SERVICE = "podojo-cli"
KEYRING_USERNAME = "api_key"
CONFIG_PATH = Path.home() / ".podojo.toml"
DEFAULT_BASE_URL = "https://podojo-fastapi-mcp.onrender.com"


def load_config() -> dict:
    config = {}
    if CONFIG_PATH.exists():
        config = tomllib.loads(CONFIG_PATH.read_text())
    config.setdefault("base_url", os.getenv("PODOJO_BASE_URL", DEFAULT_BASE_URL))
    api_key = (
        os.getenv("PODOJO_API_KEY")
        or keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        or ""
    )
    config.setdefault("api_key", api_key)
    return config


def save_config(api_key: str):
    keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, api_key)


def clear_api_key():
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
    except keyring.errors.PasswordDeleteError:
        pass
    if not CONFIG_PATH.exists():
        return
    config = tomllib.loads(CONFIG_PATH.read_text())
    config.pop("api_key", None)
    if config:
        lines = "\n".join(f'{k} = "{v}"' for k, v in config.items())
        CONFIG_PATH.write_text(lines + "\n")
    else:
        CONFIG_PATH.unlink()
