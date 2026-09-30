from google.adk import Agent

from . import prompt

academic_generalresearch_agent = Agent(
    model="gemini-2.5-flash",
    name="academic_generalresearch_agent",
    description="Analyzes a general academic paper without assuming it is seminal.",
    instruction=prompt.ACADEMIC_GENERALRESEARCH_PROMPT,
)
