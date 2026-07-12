import os
from pathlib import Path

from dotenv import load_dotenv


ENV_PATH = Path(__file__).resolve().parent / ".env"
_loaded = False


def load_environment() -> None:
    global _loaded
    if not _loaded:
        load_dotenv(ENV_PATH, override=False)
        _loaded = True


def require_env(name: str) -> str:
    load_environment()
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Expected it in {ENV_PATH} or in the process environment."
        )
    return value
