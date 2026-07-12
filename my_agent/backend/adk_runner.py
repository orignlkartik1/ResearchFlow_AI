from my_agent.env import require_env

require_env("GOOGLE_API_KEY")

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from my_agent.agent import root_agent

APP_NAME = "ResearchFlowAI"

session_service = InMemorySessionService()

runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
)

_created_sessions = set()


async def ask_agent(user_id: str, message: str) -> str:
    session_id = user_id

    # Create the session only once
    if session_id not in _created_sessions:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        _created_sessions.add(session_id)

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
