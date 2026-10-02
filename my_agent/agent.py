from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from . import prompt
from .sub_agents.academic_newresearch.agent import academic_newresearch_agent
from .sub_agents.academic_webresearch.agent import academic_websearch_agent


root_agent = Agent(
    name="academic_coordinator",
    model='gemini-2.5-flash',
    description=(
        "Analyzes uploaded academic papers, discovers recent related research, "
        "and synthesizes evidence-grounded future research directions."
    ),
    instruction=prompt.ACADEMIC_COORDINATOR_PROMPT,
    tools=[
        AgentTool(agent=academic_newresearch_agent),
        AgentTool(agent=academic_websearch_agent),
    ],
)
