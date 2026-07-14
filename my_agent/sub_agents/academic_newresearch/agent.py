from my_agent.env import require_env

require_env("GOOGLE_API_KEY")

from google.adk import Agent

from . import prompt

MODEL = "gemini-3.5-flash"

academic_newresearch_agent = Agent(
    model=MODEL,
    name="academic_newresearch_agent",
    instruction=prompt.ACADEMIC_NEWRESEARCH_PROMPT,
)
