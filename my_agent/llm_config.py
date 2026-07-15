import logging
import os

from google.adk.models import LLMRegistry
from google.adk.utils.model_name_utils import is_gemini_model

from .env import load_environment


DEFAULT_LLM_MODEL = "gemini-2.5-flash"
DEFAULT_SEARCH_MODEL = "gemini-2.5-flash"
logger = logging.getLogger(__name__)
RETRYABLE_ERROR_MARKERS = (
    "429",
    "500",
    "502",
    "503",
    "504",
    "capacity",
    "deadline",
    "demand",
    "exhausted",
    "overload",
    "quota",
    "rate limit",
    "rate_limit",
    "resource_exhausted",
    "service unavailable",
    "temporarily unavailable",
    "timeout",
    "timed out",
    "try again",
    "unavailable",
)

PROVIDER_ENV_VARS = {
    "anthropic": ("ANTHROPIC_API_KEY",),
    "azure": ("AZURE_API_KEY", "AZURE_API_BASE"),
    "azure_ai": ("AZURE_API_KEY", "AZURE_API_BASE"),
    "cohere": ("COHERE_API_KEY",),
    "deepseek": ("DEEPSEEK_API_KEY",),
    "fireworks_ai": ("FIREWORKS_API_KEY",),
    "gemini": ("GOOGLE_API_KEY",),
    "google": ("GOOGLE_API_KEY",),
    "groq": ("GROQ_API_KEY",),
    "mistral": ("MISTRAL_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
    "together_ai": ("TOGETHERAI_API_KEY",),
}


def get_llm_model() -> str:
    load_environment()
    return os.environ.get("LLM_MODEL", DEFAULT_LLM_MODEL).strip()


def get_search_model() -> str:
    load_environment()
    return os.environ.get("SEARCH_MODEL", DEFAULT_SEARCH_MODEL).strip()


def get_llm_models() -> list[str]:
    """Return the ordered primary and fallback reasoning models."""
    load_environment()
    return _model_list("LLM_MODEL", "LLM_MODEL_FALLBACKS", DEFAULT_LLM_MODEL)


def get_search_models() -> list[str]:
    """Return the ordered primary and fallback Gemini search models."""
    load_environment()
    return _model_list("SEARCH_MODEL", "SEARCH_MODEL_FALLBACKS", DEFAULT_SEARCH_MODEL)


def get_available_llm_models() -> list[str]:
    return _models_with_credentials(get_llm_models(), "LLM_MODEL/LLM_MODEL_FALLBACKS")


def get_available_search_models() -> list[str]:
    return _models_with_credentials(
        get_search_models(),
        "SEARCH_MODEL/SEARCH_MODEL_FALLBACKS",
    )


def is_retryable_llm_error(exc: Exception) -> bool:
    """Detect transient provider errors that are worth retrying on another model."""
    text = " ".join(
        str(value).lower()
        for value in (
            exc.__class__.__name__,
            getattr(exc, "message", ""),
            getattr(exc, "status_code", ""),
            getattr(exc, "code", ""),
            exc,
        )
    )
    return any(marker in text for marker in RETRYABLE_ERROR_MARKERS)


def _model_list(primary_env: str, fallback_env: str, default: str) -> list[str]:
    primary = os.environ.get(primary_env, default)
    fallbacks = os.environ.get(fallback_env, "")
    models = []
    for value in (primary, fallbacks):
        for model in value.split(","):
            model = model.strip()
            if model and model not in models:
                models.append(model)
    return models or [default]


def _provider_from_model(model: str) -> str:
    if ":" in model:
        return model.split(":", 1)[0].lower()
    if "/" in model:
        return model.split("/", 1)[0].lower()
    if model.startswith("claude-"):
        return "anthropic"
    if model.startswith(("gpt-", "o1-", "o3-")):
        return "openai"
    if is_gemini_model(model):
        return "gemini"
    return ""


def _missing_env_vars(names: tuple[str, ...]) -> list[str]:
    return [name for name in names if not os.environ.get(name)]


def _validate_supported_model(model_name: str, label: str) -> None:
    try:
        LLMRegistry.resolve(model_name)
    except Exception as exc:
        raise RuntimeError(
            f"{label}={model_name!r} is not supported by the installed ADK. "
            "Use a Gemini model such as 'gemini-3.5-flash', a native ADK model "
            "such as 'gpt-4.1', or a LiteLLM provider model such as "
            "'openai/gpt-4.1', 'anthropic/claude-sonnet-4-5', or "
            "'groq/llama-3.3-70b-versatile'."
        ) from exc


def _validate_credentials(model_name: str, label: str) -> None:
    provider = _provider_from_model(model_name)
    required = PROVIDER_ENV_VARS.get(provider, ())
    missing = _missing_env_vars(required)
    if missing:
        raise RuntimeError(
            "Missing provider credentials: "
            + "; ".join(f"{label} requires {name}" for name in missing)
        )


def _models_with_credentials(models: list[str], label: str) -> list[str]:
    available = []
    for model_name in models:
        provider = _provider_from_model(model_name)
        required = PROVIDER_ENV_VARS.get(provider, ())
        missing = _missing_env_vars(required)
        if missing:
            logger.warning(
                "Skipping %s model %s because credentials are missing: %s",
                label,
                model_name,
                ", ".join(missing),
            )
            continue
        available.append(model_name)
    return available


def validate_model_environment() -> None:
    """Validate configured model names and credentials before an agent run."""
    load_environment()
    for model_name in get_llm_models():
        _validate_supported_model(model_name, "LLM_MODEL/LLM_MODEL_FALLBACKS")

    for model_name in get_search_models():
        _validate_supported_model(model_name, "SEARCH_MODEL/SEARCH_MODEL_FALLBACKS")
        if not is_gemini_model(model_name):
            raise RuntimeError(
                f"SEARCH_MODEL fallback {model_name!r} is not valid for google_search. "
                "ADK's built-in google_search tool only works with Gemini models. "
                "Keep SEARCH_MODEL and SEARCH_MODEL_FALLBACKS set to Gemini models."
            )

    if not get_available_llm_models():
        _validate_credentials(get_llm_model(), "LLM_MODEL")

    if not get_available_search_models():
        _validate_credentials(get_search_model(), "SEARCH_MODEL")
