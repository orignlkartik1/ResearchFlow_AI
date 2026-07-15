import logging

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from my_agent.agent import create_root_agent
from my_agent.llm_config import (
    get_available_llm_models,
    get_available_search_models,
    is_retryable_llm_error,
    validate_model_environment,
)

APP_NAME = "ResearchFlowAI"
logger = logging.getLogger(__name__)

session_service = InMemorySessionService()

_created_sessions = set()


def _create_runner(llm_model: str, search_model: str) -> Runner:
    return Runner(
        app_name=APP_NAME,
        agent=create_root_agent(
            llm_model=llm_model,
            search_model=search_model,
        ),
        session_service=session_service,
    )


async def _ensure_session(user_id: str, session_id: str) -> None:
    # Create the session only once
    if session_id not in _created_sessions:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        _created_sessions.add(session_id)


async def _run_once(
    user_id: str,
    session_id: str,
    message: str,
    llm_model: str,
    search_model: str,
) -> str:
    runner = _create_runner(llm_model, search_model)
    content = types.Content(
        role="user",
        parts=[types.Part(text=message)],
    )
    answer = ""

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content:
            answer = "".join(
                part.text
                for part in event.content.parts
                if getattr(part, "text", None)
            )

    return answer


def _model_attempts() -> list[tuple[str, str]]:
    attempts = []
    for llm_model in get_available_llm_models():
        for search_model in get_available_search_models():
            attempt = (llm_model, search_model)
            if attempt not in attempts:
                attempts.append(attempt)
    return attempts


async def ask_agent(user_id: str, message: str) -> str:
    validate_model_environment()

    session_id = user_id
    await _ensure_session(user_id, session_id)

    attempts = _model_attempts()
    retryable_errors = []

    for index, (llm_model, search_model) in enumerate(attempts, start=1):
        try:
            logger.info(
                "Running ResearchFlow AI with llm_model=%s search_model=%s",
                llm_model,
                search_model,
            )
            return await _run_once(
                user_id=user_id,
                session_id=session_id,
                message=message,
                llm_model=llm_model,
                search_model=search_model,
            )
        except Exception as exc:
            if not is_retryable_llm_error(exc):
                raise RuntimeError(f"Agent run failed: {exc}") from exc

            retryable_errors.append(f"{llm_model}/{search_model}: {exc}")
            if index == len(attempts):
                break

            next_llm_model, next_search_model = attempts[index]
            logger.warning(
                "Model attempt failed; retrying with llm_model=%s search_model=%s",
                next_llm_model,
                next_search_model,
                exc_info=True,
            )

    raise RuntimeError(
        "All configured model attempts failed due to transient provider errors. "
        "Attempts: "
        + " | ".join(retryable_errors)
    )
