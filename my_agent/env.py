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


def is_telegram_enabled() -> bool:
    load_environment()
    configured = os.environ.get("ENABLE_TELEGRAM")
    if configured is None:
        return bool(os.environ.get("TELEGRAM_TOKEN"))

    normalized = configured.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(
        "ENABLE_TELEGRAM must be a boolean value: true/false, yes/no, on/off, or 1/0."
    )
