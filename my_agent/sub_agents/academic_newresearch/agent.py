from google.adk import Agent

from my_agent.llm_config import get_llm_model

from . import prompt


def create_academic_newresearch_agent(model: str | None = None) -> Agent:
    return Agent(
        model=model or get_llm_model(),
        name="academic_newresearch_agent",
        instruction=prompt.ACADEMIC_NEWRESEARCH_PROMPT,
    )


academic_newresearch_agent = create_academic_newresearch_agent()
