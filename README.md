# ResearchFlow AI

ResearchFlow AI is a multi-agent academic research assistant built around Google ADK agents. It helps a user analyze a seminal academic paper, find recent papers that cite or extend it, and generate future research directions from that evidence.

The project currently focuses on an academic workflow:

1. collect or analyze a seminal paper
2. extract its core context, references, keywords, and innovations
3. search for recent citing papers
4. synthesize gaps, trends, and promising future research areas

## Project Structure

```text
ReasearchFlow_AI/
+-- my_agent/
|   +-- agent.py
|   +-- prompt.py
|   +-- bot.py
|   +-- sub_agents/
|       +-- academic_webresearch/
|       |   +-- agent.py
|       |   +-- prompt.py
|       +-- academic_newresearch/
|           +-- agent.py
|           +-- prompt.py
+-- pyproject.toml
+-- uv.lock
+-- README.md
```

## Main Components

### Academic Coordinator

`my_agent/agent.py` defines the root `academic_coordinator` agent.

The coordinator is responsible for managing the complete research workflow. It analyzes the seminal paper, calls the web research sub-agent to find recent citing papers, then calls the new research sub-agent to produce future research directions.

The exported `root_agent` points to this coordinator:

```python
root_agent = academic_coordinator
```

### Coordinator Prompt

`my_agent/prompt.py` contains `ACADEMIC_COORDINATOR_PROMPT`.

This prompt defines the end-to-end interaction flow:

- ask the user for a seminal paper
- extract paper metadata, abstract, summary, keywords, innovations, and references
- invoke the academic web search tool
- invoke the future research synthesis tool
- present findings and suggestions clearly to the user

### Academic Web Research Sub-Agent

`my_agent/sub_agents/academic_webresearch/` contains the `academic_websearch_agent`.

This agent uses the Google ADK `google_search` tool to find recent papers that cite the provided seminal paper. Its prompt asks it to search for papers from the current year and previous year, verify relevance, group results by year, and return titles, authors, sources, years, and links.

### Academic New Research Sub-Agent

`my_agent/sub_agents/academic_newresearch/` contains the `academic_newresearch_agent`.

This agent takes the seminal paper context and the recent citing papers, then synthesizes at least 10 future research areas. Each suggestion includes a title and a short rationale explaining novelty, underexplored gaps, and future potential.

### Telegram Bot Entry Point

`my_agent/bot.py` contains a basic Aiogram Telegram bot skeleton. It currently registers a `/start` command and starts polling with the `BOT_TOKEN` environment variable.

This bot is separate from the ADK coordinator flow in its current form. It can be extended later to call the academic coordinator agent from Telegram messages.

## Requirements

The project metadata is defined in `pyproject.toml`.

Current declared requirements:

- Python `>=3.14`
- `aiogram>=3.29.0`

The source code also imports Google ADK modules such as:

- `google.adk`
- `google.adk.agents`
- `google.adk.tools`

Make sure the Google ADK package required by your environment is installed, even though it is not currently listed in `pyproject.toml`.

## Setup

This project includes a `uv.lock` file, so `uv` is the intended package manager.

```bash
uv sync
```

If you are not using `uv`, create a virtual environment and install the dependencies from `pyproject.toml` with your preferred Python package manager.

Environment variables you may need:

```text
BOT_TOKEN=your_telegram_bot_token
```

Google ADK and Gemini usage may also require provider-specific credentials depending on your local ADK configuration.

## Running

### Run The Telegram Bot

```bash
python -m my_agent.bot
```

The bot will start polling Telegram using `BOT_TOKEN`.

### Run With Google ADK

The root agent is exposed as `root_agent` in `my_agent/agent.py`, which is the common structure expected by ADK tooling.

Depending on your installed ADK CLI and configuration, run or inspect the agent from the project root using the ADK command appropriate for your environment.

## Workflow

The intended ResearchFlow AI workflow is:

1. User provides a seminal academic paper, ideally as a PDF or identifiable paper metadata.
2. The coordinator extracts the paper's title, authors, abstract, summary, keywords, innovations, and references.
3. The coordinator calls `academic_websearch_agent`.
4. The web research agent searches for recent papers citing the seminal paper and returns grouped results.
5. The coordinator calls `academic_newresearch_agent`.
6. The new research agent generates future research areas based on the seminal paper and recent citing papers.
7. The coordinator presents the recent papers and future research directions to the user.

## Notes

- The web research sub-agent is responsible for retrieval.
- The new research sub-agent is responsible for synthesis and forecasting.
- The coordinator owns the user-facing workflow and output formatting.
- `bot.py` is currently a minimal Telegram bot and is not yet wired into the ADK agent workflow.
- The package name in `pyproject.toml` is currently `reasearchflow-ai`, matching the repository spelling.
