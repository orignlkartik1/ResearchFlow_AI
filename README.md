# ResearchFlow AI

ResearchFlow AI is a multi-agent academic research assistant built around Google ADK agents with a FastAPI backend and Telegram bot interface. It helps researchers analyze seminal academic papers, find recent citing papers, identify research trends, and discover promising future research areas.

**For detailed project specifications and requirements, see the [SRS Document](./SRS.md).**

## Project Overview

The project currently focuses on an integrated research workflow:

1. Collect or analyze a seminal paper
2. Extract its core context, references, keywords, and innovations
3. Search for recent citing papers (current year and previous year)
4. Synthesize gaps, trends, and promising future research areas
5. Deliver results through Telegram bot or direct API access

## Project Structure

```text
ResearchFlow_AI/
+-- my_agent/
|   +-- __init__.py
|   +-- agent.py                          # Coordinator agent definition
|   +-- prompt.py                         # Coordinator prompt
|   +-- env.py                            # Environment variable handling
|   +-- backend/
|   |   +-- main.py                       # FastAPI application
|   |   +-- adk_runner.py                 # ADK agent runner & session management
|   |   +-- telegram.py                   # Telegram bot handler
|   +-- sub_agents/
|       +-- academic_webresearch/
|       |   +-- agent.py                  # Web search sub-agent
|       |   +-- prompt.py                 # Web search prompt
|       +-- academic_newresearch/
|           +-- agent.py                  # Future research sub-agent
|           +-- prompt.py                 # Future research prompt
+-- SRS.md                                # Detailed specifications
+-- README.md                             # This file
+-- pyproject.toml                        # Project metadata and dependencies
+-- uv.lock                               # Dependency lock file
```

## Main Components

### Academic Coordinator Agent

`my_agent/agent.py` defines the root `academic_coordinator` agent using Google ADK.

The coordinator is responsible for managing the complete research workflow. It uses `gemini-2.5-flash` as the LLM and orchestrates sub-agents through the `AgentTool` wrapper. The coordinator:

- Analyzes the seminal paper from user input
- Invokes the web research sub-agent to find citing papers
- Invokes the new research sub-agent to generate future directions
- Compiles and presents findings to the user
- Maintains conversation context for multi-turn interactions

The exported `root_agent` points to this coordinator:

```python
root_agent = Agent(
    name="academic_coordinator",
    model=MODEL,
    description="Analyzes seminal papers...",
    instruction=prompt.ACADEMIC_COORDINATOR_PROMPT,
    tools=[
        AgentTool(agent=academic_websearch_agent),
        AgentTool(agent=academic_newresearch_agent),
    ],
)
```

### Coordinator Prompt

`my_agent/prompt.py` contains `ACADEMIC_COORDINATOR_PROMPT`.

This prompt defines the end-to-end interaction flow:

- Greet the user and ask for a seminal paper
- Extract paper metadata: title, authors, abstract, summary, keywords, innovations, and references
- Invoke the academic web search tool to find recent citing papers
- Invoke the future research synthesis tool based on findings
- Present results clearly to the user
- Support follow-up questions and context-aware responses

### Academic Web Research Sub-Agent

`my_agent/sub_agents/academic_webresearch/` contains the `academic_websearch_agent`.

This agent uses the Google ADK `google_search` tool to find recent papers that cite the provided seminal paper. Its prompt:

- Searches for papers from the current year and previous year
- Targets at least 10 distinct citing papers per year (20 minimum total)
- Uses iterative search strategies with multiple query variations
- Filters results for relevance and removes duplicates
- Groups results by publication year

### Academic New Research Sub-Agent

`my_agent/sub_agents/academic_newresearch/` contains the `academic_newresearch_agent`.

This agent takes the seminal paper context and the recent citing papers, then synthesizes:

- At least 10 future research areas
- Each with title, rationale, and novelty assessment
- Diversity across utility, unexpectedness, and emerging popularity
- Optional identification of relevant authors from the input papers

### FastAPI Backend

`my_agent/backend/main.py` contains the FastAPI application with a `/chat` endpoint.

- Accepts POST requests with `user_id` and `message`
- Routes requests to the ADK runner for agent processing
- Returns JSON response with agent findings
- Handles concurrent user requests asynchronously
- Manages session creation and context preservation

### ADK Runner

`my_agent/backend/adk_runner.py` manages agent execution and session state.

- Creates and maintains in-memory sessions per user
- Uses Google ADK's `Runner` and `InMemorySessionService`
- Implements `ask_agent(user_id, message)` function for backend integration
- Extracts final response text from agent events
- Preserves conversation context across multiple turns

### Telegram Bot Entry Point

`my_agent/backend/telegram.py` contains the Telegram bot using python-telegram-bot.

- Registers `/start` command with greeting
- Handles text messages and forwards them to the FastAPI backend via HTTP
- Uses async `httpx.AsyncClient` for non-blocking requests
- Displays agent responses back to the user
- Implements proper async/await patterns for polling
- Supports multi-turn conversations with context persistence

## Requirements

The project metadata is defined in `pyproject.toml`.

Current declared requirements:

- Python `>=3.14`
- `aiogram>=3.29.0` (alternative bot framework option)
- `fastapi>=0.139.0`
- `google-adk==2.3.0`
- `httpx>=0.28.1` (async HTTP client)
- `python-dotenv>=1.2.2`
- `python-telegram-bot>=22.8`
- `uvicorn>=0.51.0`

The source code imports Google ADK modules such as:

- `google.adk.agents`
- `google.adk.tools`
- `google.adk.runners`
- `google.adk.sessions`
- `google.genai.types`

Make sure the Google ADK package required by your environment is installed.

## Setup

This project includes a `uv.lock` file, so `uv` is the intended package manager.

```bash
uv sync
```

If you are not using `uv`, create a virtual environment and install the dependencies from `pyproject.toml` with your preferred Python package manager.

### Environment Variables

You need to configure the following environment variables. Create a `.env` file in the `my_agent/` directory:

```text
# Required for Google ADK agents
GOOGLE_API_KEY=your_google_adk_api_key

# Required for Telegram bot
TELEGRAM_TOKEN=your_telegram_bot_token

# Optional backend configuration
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
```

#### Advanced LLM Configuration (Optional)

For advanced model fallback and custom provider configuration:

```text
LLM_MODEL=gemini-2.5-flash
LLM_MODEL_FALLBACKS=openai/gpt-4.1,anthropic/claude-sonnet-4-5,groq/llama-3.3-70b-versatile
SEARCH_MODEL=gemini-2.5-flash
SEARCH_MODEL_FALLBACKS=gemini-3.5-flash-lite
```

Google ADK, Gemini, and LiteLLM providers require provider-specific credentials depending on the models you configure. Add only the keys for the providers you use:

- Google: `GOOGLE_API_KEY`
- OpenAI: `OPENAI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- Groq: `GROQ_API_KEY`

The agent validates every configured model at startup. During a run, ResearchFlow AI automatically retries with the next configured model when the active provider returns transient demand errors (rate limits, quota exceeded, etc.).

## Running

### Run FastAPI Backend

```bash
python -m uvicorn my_agent.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend will start on `http://127.0.0.1:8000/` with the `/chat` endpoint available.

To test the backend:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "message": "Analyze the paper on Transformers"}'
```

### Run Telegram Bot

```bash
python -m my_agent.backend.telegram
```

The bot will connect to Telegram and start polling for messages. It will forward messages to the backend at `http://127.0.0.1:8000/chat`.

**Make sure the FastAPI backend is running before starting the Telegram bot.**

### Run With Google ADK CLI (Alternative)

The root agent is exposed as `root_agent` in `my_agent/agent.py`, which is the common structure expected by ADK tooling.

Depending on your installed ADK CLI and configuration, run the agent from the project root:

```bash
adk run --agent my_agent.agent:root_agent
```

## Workflow

The intended ResearchFlow AI workflow is:

1. User sends a message to Telegram bot (e.g., paper title or query)
2. Telegram bot forwards the message to FastAPI backend via HTTP POST to `/chat`
3. Backend creates a session for the user (if new) and calls the ADK runner
4. Coordinator agent analyzes the seminal paper for context
5. Coordinator calls `academic_websearch_agent` via AgentTool
6. Web research agent searches for recent citing papers using Google Search tool
7. Coordinator calls `academic_newresearch_agent` via AgentTool
8. New research agent generates future research directions
9. Coordinator compiles findings and returns response to backend
10. Backend returns JSON response to Telegram bot
11. Telegram bot displays the research findings to the user
12. User can ask follow-up questions, and the session maintains context

## API Documentation

### POST /chat

Processes user research queries through the ADK agent system.

**Endpoint:** `POST /chat`

**Request Body:**
```json
{
  "user_id": "unique_user_identifier",
  "message": "User's research query or follow-up question"
}
```

**Response (Success - 200):**
```json
{
  "response": "Agent's research findings and analysis"
}
```

**Response (Error - 400/500):**
```json
{
  "detail": "Error message describing the issue"
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "Analyze the Attention is All You Need paper and find recent citing papers"
  }'
```

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
   - Ensure no credentials are exposed in code or logs

4. **Agent Development**
   - Modify prompts in `prompt.py` files for agent behavior changes
   - Add new sub-agents in `my_agent/sub_agents/` following existing patterns
   - Test agent workflows end-to-end before submitting
   - Validate multi-turn conversation support

5. **Backend Development**
   - Keep FastAPI routes simple and focused
   - Use async/await patterns consistently
   - Test concurrent requests
   - Document API endpoints
   - Ensure session management works correctly

6. **Telegram Bot Enhancement**
   - Use async handlers and non-blocking HTTP calls
   - Handle error cases gracefully
   - Test with actual Telegram Bot API before submitting
   - Support multi-turn conversations with context

7. **Documentation**
   - Update README.md if adding user-facing features
   - Update SRS.md if changing requirements or adding significant features
   - Include clear commit messages describing your changes
   - Document any new environment variables or configuration

8. **Pull Request Process**
   - Link related issues in your PR description
   - Provide clear explanation of what your PR does and why
   - Ensure all changes are tested
   - Be responsive to feedback and review comments
   - Verify that multi-turn conversations work correctly

9. **Areas for Contribution**
   - **Backend Enhancements**: Database persistence, caching, monitoring, logging
   - **AI Agents Stack**: Advanced reasoning patterns (ReAct, Chain-of-Thought), memory systems
   - **Paper Analysis**: Enhanced metadata extraction, document parsing, figure/table analysis
   - **Testing**: Unit and integration tests for agents and backend, conversation testing
   - **Documentation**: Improve code comments and user guides, architecture diagrams
   - **Bot Features**: File uploads, inline search, conversation history, command enhancements
   - **Performance**: Optimization and scaling, concurrent request handling
   - **Security**: Input validation, credential protection, API security

## Future Enhancements

ResearchFlow AI is actively evolving. Key planned improvements include:

- **Full Telegram Integration**: Seamless message routing between Telegram and research workflows
- **Advanced AI Agents**: ReAct pattern, Chain-of-Thought reasoning, agent memory systems
- **Database Backend**: Replace in-memory sessions with PostgreSQL/MongoDB for persistence
- **Citation Network Visualization**: Interactive graph exploration and trend analysis
- **Web Dashboard**: User-friendly interface for research exploration and result visualization
- **Enhanced Paper Analysis**: Table/figure extraction, methodology parsing, code repository discovery
- **Collaborative Features**: Shared research projects, team annotations, export capabilities
- **Model Diversification**: Support for multiple LLM providers with automatic fallback

See the [SRS Document](./SRS.md) for detailed future enhancement plans.

## Notes

- The web research sub-agent is responsible for retrieval using Google Search.
- The new research sub-agent is responsible for synthesis and future direction forecasting.
- The coordinator owns the user-facing workflow and output formatting.
- FastAPI backend (`backend/main.py`) is the central hub for session and agent management.
- Telegram bot (`backend/telegram.py`) is the primary user interface, connecting via HTTP to the backend.
- Sessions are stored in-memory and do not persist across server restarts (future: database backend).
- The package name in `pyproject.toml` is currently `researchflow-ai`, matching the repository name.
- Multi-turn conversations are supported and maintain context across multiple user messages.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

For issues, questions, or suggestions, please open an issue on the GitHub repository.

For more information about Google ADK and Telegram Bot API, refer to:
- [Google ADK Documentation](https://ai.google.dev/)
- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [python-telegram-bot Documentation](https://python-telegram-bot.readthedocs.io/)
