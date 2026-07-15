from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from . import prompt
from .llm_config import get_llm_model
from .llm_config import get_search_model
from .sub_agents.academic_newresearch.agent import create_academic_newresearch_agent
from .sub_agents.academic_webresearch.agent import create_academic_websearch_agent


def create_root_agent(
    llm_model: str | None = None,
    search_model: str | None = None,
) -> Agent:
    llm_model = llm_model or get_llm_model()
    search_model = search_model or get_search_model()

    return Agent(
        name="academic_coordinator",
        model=llm_model,
        description=(
            "Analyzes seminal papers provided by users, provides research advice, "
            "locates current papers relevant to the seminal paper, generates suggestions "
            "for new research directions, and accesses web resources to acquire knowledge."
        ),
        instruction=prompt.ACADEMIC_COORDINATOR_PROMPT,
        output_key="seminal_paper",
        tools=[
            AgentTool(agent=create_academic_websearch_agent(search_model)),
            AgentTool(agent=create_academic_newresearch_agent(llm_model)),
        ],
    )


root_agent = create_root_agent()
