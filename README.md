# ResearchFlow AI

ResearchFlow AI is a multi-agent academic research assistant built around Google ADK agents. It helps a user analyze a seminal academic paper, find recent papers that cite or extend it, and generate insights about future research directions.

**For detailed project specifications and requirements, see the [SRS Document](./SRS.md).**

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
+-- SRS.md
+-- pyproject.toml
+-- uv.lock
+-- README.md
```

## Main Components

### Academic Coordinator

`my_agent/agent.py` defines the root `academic_coordinator` agent.

The coordinator is responsible for managing the complete research workflow. It analyzes the seminal paper, calls the web research sub-agent to find recent citing papers, then calls the new research sub-agent to synthesize insights.

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

This agent uses the Google ADK `google_search` tool to find recent papers that cite the provided seminal paper. Its prompt asks it to search for papers from the current year and previous year, verify results, and group them logically.

### Academic New Research Sub-Agent

`my_agent/sub_agents/academic_newresearch/` contains the `academic_newresearch_agent`.

This agent takes the seminal paper context and the recent citing papers, then synthesizes at least 10 future research areas. Each suggestion includes a title and a short rationale explaining novel directions and research gaps.

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
LLM_MODEL=gemini-3.5-flash
LLM_MODEL_FALLBACKS=openai/gpt-4.1,anthropic/claude-sonnet-4-5,groq/llama-3.3-70b-versatile
SEARCH_MODEL=gemini-3.5-flash
SEARCH_MODEL_FALLBACKS=gemini-3.5-flash-lite
```

Google ADK, Gemini, and LiteLLM providers require provider-specific credentials depending on the models you configure. Add only the keys for the providers you use, such as `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY`, or `DEEPSEEK_API_KEY`.

The agent validates every configured model at startup. During a run, ResearchFlow AI automatically retries with the next configured model when the active provider returns transient demand errors such as quota exhaustion, rate limits, overload, timeouts, 429, or 503 responses. The web-search sub-agent must still use Gemini models because ADK's built-in `google_search` tool only supports Gemini-backed agents.

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

## Contributing

We welcome contributions! Here are some tips for getting started:

### Contribution Tips

1. **Before You Start**
   - Check existing issues and pull requests to avoid duplicates
   - Read the [SRS Document](./SRS.md) to understand project scope and requirements
   - Ensure you have Python 3.14+ and `uv` installed

2. **Development Workflow**
   - Fork the repository and create a feature branch: `git checkout -b feature/your-feature-name`
   - Set up your environment: `uv sync`
   - Make your changes following PEP 8 standards
   - Test your code thoroughly before submitting

3. **Code Quality**
   - Include docstrings for all functions and classes
   - Keep functions focused and modular
   - Add comments for complex logic
   - Follow the existing code style and architecture

4. **Agent Development**
   - Modify prompts in `prompt.py` files for agent behavior changes
   - Add new sub-agents in `my_agent/sub_agents/` following existing patterns
   - Test agent workflows end-to-end before submitting

5. **Documentation**
   - Update README.md if adding user-facing features
   - Update SRS.md if changing requirements or adding significant features
   - Include clear commit messages describing your changes

6. **Pull Request Process**
   - Link related issues in your PR description
   - Provide clear explanation of what your PR does and why
   - Ensure all changes are tested
   - Be responsive to feedback and review comments

7. **Areas for Contribution**
   - **Telegram Bot Integration**: Connect bot to academic coordinator workflow
   - **AI Agents Stack**: Implement advanced reasoning patterns (ReAct, Chain-of-Thought)
   - **Paper Analysis**: Enhance metadata extraction and document parsing
   - **Testing**: Add unit and integration tests
   - **Documentation**: Improve code comments and user guides

## Future Enhancements

ResearchFlow AI is actively evolving. Key planned improvements include:

- **Telegram Bot Full Integration**: Seamless message routing to research workflows
- **Advanced AI Agents Stack**: ReAct pattern, Chain-of-Thought, agent memory, specialized sub-agents
- **Citation Network Visualization**: Interactive graph exploration
- **Web Dashboard**: User-friendly interface for research exploration
- **Database Backend**: PostgreSQL/MongoDB for scalable paper storage

See the [SRS Document](./SRS.md) for detailed future enhancement plans.

## Notes

- The web research sub-agent is responsible for retrieval.
- The new research sub-agent is responsible for synthesis and forecasting.
- The coordinator owns the user-facing workflow and output formatting.
- `bot.py` is currently a minimal Telegram bot and is not yet wired into the ADK agent workflow.
- The package name in `pyproject.toml` is currently `reasearchflow-ai`, matching the repository spelling.

