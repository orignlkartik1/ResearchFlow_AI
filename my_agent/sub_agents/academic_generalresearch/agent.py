from google.adk import Agent
from google.adk.tools.agent_tool import AgentTool

from . import prompt
from ..academic_newresearch.agent import academic_newresearch_agent
from ..academic_webresearch.agent import academic_websearch_agent

academic_generalresearch_agent = Agent(
    model="gemini-2.5-flash",
    name="academic_generalresearch_agent",
    description=(
        "Analyzes a general academic paper, discovers related recent research, "
        "and synthesizes future research directions."
    ),
    instruction=prompt.ACADEMIC_GENERALRESEARCH_PROMPT,
    tools=[
        AgentTool(agent=academic_websearch_agent),
        AgentTool(agent=academic_newresearch_agent),
    ],
)
