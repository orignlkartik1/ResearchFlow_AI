# ResearchFlow AI

ResearchFlow AI is a multi-agent academic research assistant built with Google ADK, FastAPI, and a Telegram bot interface. It helps users analyze seminal papers or research prompts, search for recent citing work, and synthesize future research directions.

Detailed requirements and design notes are maintained in [SRS.md](./SRS.md), [DESIGN.md](./DESIGN.md), [HLD.md](./HLD.md), and [LLD.md](./LLD.md).

## Current Capabilities

1. Accept research requests through `POST /chat`.
2. Expose `GET /health` for a basic service health check.
3. Analyze text-based research PDFs through `POST /api/analyze-pdf`.
4. Accept Telegram updates through `POST /telegram/webhook` when Telegram is enabled.
5. Run a Google ADK coordinator agent with two specialist sub-agents.
6. Search the web for recent academic work using the ADK Google Search tool
7. Generate future research directions from the seminal paper context and recent papers.
8. Preserve per-user conversation context in memory while the backend process is running.
9. Split long Telegram responses and send extremely large responses as text attachments.

## Project Structure

```text
ResearchFlow_AI/
+-- my_agent/
|   +-- __init__.py
|   +-- agent.py                          # Root academic coordinator agent
|   +-- prompt.py                         # Coordinator prompt
|   +-- env.py                            # .env loading and required env checks
|   +-- backend/
|   |   +-- __init__.py
|   |   +-- main.py                       # FastAPI app, /chat, Telegram webhook
|   |   +-- adk_runner.py                 # ADK Runner and in-memory sessions
|   |   +-- telegram.py                   # Telegram handlers and webhook helpers
|   |   +-- telegram_messages.py          # Long-message split/send helpers
|   |   +-- pdf/
|   |       +-- extractor.py              # In-memory PDF validation and extraction
|   +-- sub_agents/
|       +-- academic_webresearch/
|       |   +-- agent.py                  # Google Search-backed retrieval agent
|       |   +-- prompt.py                 # Retrieval prompt
|       +-- academic_newresearch/
|           +-- agent.py                  # Future research synthesis agent
|           +-- prompt.py                 # Synthesis prompt
+-- web/
|   +-- index.html                        # ResearchFlow-AI web interface
|   +-- style.css                         # Responsive UI styles
|   +-- app.js                            # Browser upload and results flow
+-- README.md
+-- SRS.md
+-- DESIGN.md
+-- HLD.md
+-- LLD.md
+-- ARCHITECTURE.md
+-- pyproject.toml
+-- uv.lock
```

## Architecture Summary

```text
Telegram user, API client, or PDF upload
        |
        v
FastAPI app: my_agent.backend.main
        |
        +-- /chat
        +-- /api/analyze-pdf
        +-- /health
        +-- /telegram/webhook
        |
        v
ADK runner: my_agent.backend.adk_runner
        |
        v
Coordinator agent: my_agent.agent
        |
        +-- academic_websearch_agent + google_search
        +-- academic_newresearch_agent
```

The FastAPI app initializes and starts Telegram during its lifespan only when Telegram is enabled. Telegram remains enabled by default when `TELEGRAM_TOKEN` is configured, preserving existing deployments; set `ENABLE_TELEGRAM=false` for a web-only deployment. Setting `ENABLE_TELEGRAM=true` without a token fails clearly at startup. When Telegram is enabled and `TELEGRAM_WEBHOOK_URL` is configured, startup registers the webhook. Telegram message handling calls the same ADK runner as `POST /chat`.

## Main Components

### Coordinator Agent

`my_agent/agent.py` exports `root_agent`, a Google ADK `Agent` named `academic_coordinator` using `gemini-2.5-flash`.

The coordinator owns the user-facing workflow and exposes two sub-agents through `AgentTool`:

- `academic_websearch_agent` for recent citing-paper discovery.
- `academic_newresearch_agent` for future research direction synthesis.

### Web Research Sub-Agent

`my_agent/sub_agents/academic_webresearch/agent.py` defines an agent that uses ADK's `google_search` tool. Its prompt asks it to identify papers from the current year and previous year that cite or extend the seminal work, group them by year, and include links where available.

### New Research Sub-Agent

`my_agent/sub_agents/academic_newresearch/agent.py` defines an agent that synthesizes at least 10 future research areas when enough paper context is available. It focuses on novelty, practical utility, unexpected directions, and emerging interest.

### FastAPI Backend

`my_agent/backend/main.py` exposes:

- `GET /health` for a basic health check.
- `POST /chat` for direct API usage.
- `POST /api/analyze-pdf` for PDF upload and research analysis.
- `POST /telegram/webhook` for Telegram updates.

The app validates Telegram webhook secrets when `TELEGRAM_WEBHOOK_SECRET` is set, schedules Telegram update processing as a background task, and manages the optional Telegram application's startup and shutdown lifecycle. PDF uploads are extracted by `my_agent/backend/pdf/extractor.py` and sent through the shared ADK runner.

### ADK Runner

`my_agent/backend/adk_runner.py` owns agent execution:

- Uses `Runner` from Google ADK.
- Uses `InMemorySessionService` for process-local conversation state.
- Creates one session per `user_id`.
- Extracts final text from ADK final response events.
- Converts execution failures into `RuntimeError` for callers.

### Telegram Integration

`my_agent/backend/telegram.py` uses `python-telegram-bot`.

- `/start` sends a short welcome message.
- Text messages show typing status and a processing message.
- User messages are sent to `ask_agent(user_id, message)`.
- Long responses are sent through `telegram_messages.py`.
- Long polling is disabled by default and only runs when `ENABLE_TELEGRAM_POLLING=1`.

## Requirements

The project uses `uv` and declares dependencies in `pyproject.toml`.

Current requirements include:

- Python `>=3.13`
- `fastapi`
- `google-adk==2.3.0`
- `pypdf` for in-memory, page-by-page PDF text extraction (BSD-3-Clause)
- `pydantic`
- `python-dotenv`
- `python-telegram-bot`
- `uvicorn`

`httpx` remains a declared dependency. Telegram uses `python-telegram-bot`.

## Setup

Install dependencies:

```bash
uv sync
```

Create `my_agent/.env` or provide equivalent process environment variables:

```text
GOOGLE_API_KEY=your_google_api_key

# Optional: set these to enable Telegram; omit them for web-only deployments.
# TELEGRAM_TOKEN=your_telegram_bot_token
# ENABLE_TELEGRAM=true

# Alternatively, explicitly disable Telegram even when a token is configured.
# ENABLE_TELEGRAM=false

# Optional: production webhook registration and verification
TELEGRAM_WEBHOOK_URL=https://your-domain.example/telegram/webhook
TELEGRAM_WEBHOOK_SECRET=your_random_secret

# Optional: local debugging only
ENABLE_TELEGRAM_POLLING=1
```

## Running

### FastAPI Web App

Start the FastAPI application, which serves both the web interface and API:

```bash
uv run uvicorn my_agent.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Open [http://localhost:8000/](http://localhost:8000/), choose or drop a PDF, and select **Analyze research**. The results view shows the returned analysis and lets you start another upload without refreshing. The UI sends the PDF as multipart form data to the same-origin `/api/analyze-pdf` endpoint; AI credentials remain server-side.

Text-based PDFs are supported; scanned/image-only PDFs are not, and OCR is unavailable. Uploads are processed in memory and are not permanently stored. Authentication is not implemented. Before operating as a public production service, add appropriate authentication and rate limiting.

For a Render web service, no separate frontend or deployment configuration is required. Use a start command that binds Uvicorn to the platform-provided port:

```bash
uv run uvicorn my_agent.backend.main:app --host 0.0.0.0 --port $PORT
```

Set `ENABLE_TELEGRAM=false` for web-only startup; no `TELEGRAM_TOKEN` is needed in that mode.

Test `/chat`:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user","message":"Analyze Attention Is All You Need and find recent citing papers."}'
```

Expected response shape:

```json
{
  "response": "Agent response text"
}
```

### Telegram Webhook Mode

Run the FastAPI app with `TELEGRAM_TOKEN` configured. If `TELEGRAM_WEBHOOK_URL` is set, startup registers the webhook automatically:

```bash
python -m uvicorn my_agent.backend.main:app --host 0.0.0.0 --port 8000
```

Telegram will send updates to:

```text
POST /telegram/webhook
```

When `TELEGRAM_WEBHOOK_SECRET` is configured, Telegram requests must include the matching `X-Telegram-Bot-Api-Secret-Token` header.

### Local Telegram Polling

Polling is intended only for temporary local debugging:

```bash
$env:ENABLE_TELEGRAM_POLLING="1"
python -m my_agent.backend.telegram
```

Without `ENABLE_TELEGRAM_POLLING=1`, the module raises an error telling you to use the FastAPI webhook path.

## API

### `POST /chat`

Request:

```json
{
  "user_id": "unique_user_identifier",
  "message": "research question, paper title, citation, abstract, or follow-up"
}
```

Success:

```json
{
  "response": "agent response text"
}
```

Agent execution failures return `503` with a `detail` field.

### `GET /health`

Returns `{"status": "ok"}` when the application is serving requests.

### `POST /api/analyze-pdf`

Upload a PDF as `multipart/form-data` using the `file` field. The backend extracts text page by page and sends it to the same `ask_agent()` research path used by `/chat`; uploaded files are not permanently stored.

```bash
curl -X POST \
  -F "file=@paper.pdf" \
  http://localhost:8000/api/analyze-pdf
```

Successful response:

```json
{
  "success": true,
  "filename": "paper.pdf",
  "page_count": 12,
  "result": {
    "response": "Research analysis..."
  }
}
```

The current limits are 15 MiB per upload, 100 pages, and 120,000 extracted text characters; at least 20 alphanumeric characters must be extractable. Files must have a `.pdf` filename and a valid PDF header/content; the provided MIME type is not trusted. Scanned/image-only PDFs without extractable text are rejected; OCR is not supported yet. Documents exceeding a limit receive an error rather than being silently truncated. PDF bytes and extracted text are processed in memory, and the per-request ADK session is deleted after analysis. AI credentials remain server-side.

### `POST /telegram/webhook`

Accepts a Telegram update JSON payload and returns:

```json
{
  "ok": true
}
```

Invalid JSON returns `400`. Invalid webhook secrets return `403` when webhook secret validation is enabled.
The route returns `503` when Telegram integration is disabled.

## Development Notes

- Agent behavior is controlled primarily through prompt files.
- The coordinator and both sub-agents currently use `gemini-2.5-flash`.
- Session state is process-local and is lost on restart.
- There is no persistent database yet.
- Scanned/image-only PDF OCR is not implemented.
- Web research quality depends on Google Search results returned through the ADK tool.

## Documentation

- [SRS.md](./SRS.md): requirements, constraints, acceptance criteria, and revision history.
- [DESIGN.md](./DESIGN.md): product, interaction, response, API, and configuration design.
- [HLD.md](./HLD.md): system context, layers, data flow, deployment, and security view.
- [LLD.md](./LLD.md): module-level functions, contracts, runtime behavior, and extension points.
- [ARCHITECTURE.md](./ARCHITECTURE.md): concise architecture reference.

## Future Enhancements

- Authentication and rate limiting before public production use.
- PDF follow-up chat.
- Persistent sessions with Redis, PostgreSQL, or another shared store.
- Scholarly database integrations.
- Citation graph visualization.
- Structured exports such as Markdown, JSON, BibTeX, or PDF.
- Tests for API, Telegram message splitting, webhook validation, and agent runner behavior.

## License

The project declares the MIT license in `pyproject.toml` and this README. The repository does not yet include a `LICENSE` file because it does not identify a copyright holder.
