from my_agent.env import require_env

require_env("GOOGLE_API_KEY")

from google.adk import Agent
from google.adk.tools import google_search

from . import prompt

MODEL = "gemini-3.5-flash"


academic_websearch_agent = Agent(
    model=MODEL,
    name="academic_websearch_agent",
    instruction=prompt.ACADEMIC_WEBSEARCH_PROMPT,
    output_key="recent_citing_papers",
    tools=[google_search],
)
