from google.adk import Agent
from google.adk.tools import google_search

from . import prompt
from ..research_context import WebSearchInput

academic_websearch_agent =  Agent(
        model="gemini-2.5-flash",
        name="academic_websearch_agent",
        instruction=prompt.ACADEMIC_WEBSEARCH_PROMPT,
        input_schema=WebSearchInput,
        output_key="recent_research",
        tools=[google_search],
    )
