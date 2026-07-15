from google.adk import Agent
from google.adk.tools import google_search

from my_agent.llm_config import get_search_model

from . import prompt


def create_academic_websearch_agent(model: str | None = None) -> Agent:
    return Agent(
        model=model or get_search_model(),
        name="academic_websearch_agent",
        instruction=prompt.ACADEMIC_WEBSEARCH_PROMPT,
        output_key="recent_citing_papers",
        tools=[google_search],
    )


academic_websearch_agent = create_academic_websearch_agent()
