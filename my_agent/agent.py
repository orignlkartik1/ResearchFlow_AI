from .env import require_env

require_env("GOOGLE_API_KEY")

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from . import prompt
from .sub_agents.academic_newresearch import academic_newresearch_agent
from .sub_agents.academic_webresearch import academic_websearch_agent

MODEL = "gemini-3.5-flash"


root_agent = Agent(
    name="academic_coordinator",
    model=MODEL,
    description=(
        "Analyzes seminal papers provided by users, provides research advice, "
        "locates current papers relevant to the seminal paper, generates suggestions "
        "for new research directions, and accesses web resources to acquire knowledge."
    ),
    instruction=prompt.ACADEMIC_COORDINATOR_PROMPT,
    output_key="seminal_paper",
    tools=[
        AgentTool(agent=academic_websearch_agent),
        AgentTool(agent=academic_newresearch_agent),
    ],
)
