import logging

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from my_agent.agent import root_agent

APP_NAME = "ResearchFlowAI"
logger = logging.getLogger(__name__)

session_service = InMemorySessionService()

_created_sessions = set()


class AgentSessionCleanupError(RuntimeError):
    """Raised when a short-lived ADK session cannot be deleted."""


def _create_runner(
    llm_model: str | None = None,
    search_model: str | None = None,
    agent: Agent = root_agent,
) -> Runner:
    return Runner(
        app_name=APP_NAME,
        agent=agent,
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
    agent: Agent = root_agent,
) -> str:
    runner = _create_runner(llm_model=llm_model, agent=agent)
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
                for part in event.content.part
                if getattr(part, "text", None)
            )

    return answer

async def ask_agent(user_id: str, message: str) -> str:
    session_id = user_id
    await _ensure_session(user_id, session_id)

    try:
        # Use the default model configured on the root_agent unless specified
        return await _run_once(user_id=user_id, session_id=session_id, message=message, llm_model=None)
    except Exception as exc:
        logger.exception("ask_agent failed for user %s", user_id)
        raise RuntimeError(f"Agent execution failed: {exc}") from exc


async def run_specialized_agent(user_id: str, message: str, agent: Agent) -> str:
    """Run a task-specific ADK agent with the shared session and runner services."""
    session_id = user_id
    await _ensure_session(user_id, session_id)

    try:
        return await _run_once(
            user_id=user_id,
            session_id=session_id,
            message=message,
            llm_model=None,
            agent=agent,
        )
    except Exception as exc:
        logger.exception("Specialized agent execution failed for user %s", user_id)
        raise RuntimeError(f"Agent execution failed: {exc}") from exc


async def discard_agent_session(user_id: str) -> None:
    """Remove a short-lived agent session after an API operation."""
    session_id = user_id
    if session_id not in _created_sessions:
        return

    try:
        await session_service.delete_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
    except Exception as exc:
        logger.exception("Failed to clear temporary agent session for user %s", user_id)
        raise AgentSessionCleanupError("Agent session cleanup failed") from exc
    _created_sessions.discard(session_id)
