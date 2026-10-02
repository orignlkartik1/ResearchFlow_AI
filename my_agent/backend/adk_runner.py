import logging

from google.adk.agents import Agent
<<<<<<< HEAD
from google.adk.events import Event
=======
>>>>>>> 2c45288313cf742abf248695f11136fbf9fae068
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


<<<<<<< HEAD
def _final_response_text(event: Event) -> str:
    if not event.is_final_response() or event.content is None:
        return ""

    text_parts = []
    for part in event.content.parts or []:
        text = getattr(part, "text", None)
        if isinstance(text, str):
            text_parts.append(text)
    return "".join(text_parts)


=======
>>>>>>> 2c45288313cf742abf248695f11136fbf9fae068
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
        response_text = _final_response_text(event)
        if response_text:
            answer = response_text

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
