# Architecture

ResearchFlow AI is organized around a FastAPI backend that serves the browser interface and API, an optional Telegram application, a PDF understanding/router layer, and specialized Google ADK research workflows.

For fuller design detail, use [HLD.md](./HLD.md) for the system-level view and [LLD.md](./LLD.md) for module-level behavior.

## Runtime View

```text
Browser, API client, PDF upload, or Telegram (when enabled)
        |
        v
my_agent.backend.main
        |
        +-- /chat
        +-- /health
        +-- /api/analyze-pdf
        +-- /telegram/webhook (optional)
        |
        +-- PDF -> extractor -> document classifier -> workflow router
                                      |                    |
                                      v                    v
                         academic_coordinator    academic_generalresearch_agent
                                      |
                           academic_websearch_agent
                           academic_newresearch_agent
```

`POST /api/analyze-pdf` validates an in-memory upload, extracts page-labeled text once, classifies a bounded excerpt, and routes the document. Confident seminal papers use the existing `ask_agent()` coordinator path; general or uncertain papers use the general-paper agent through the same ADK runner/session services. Short-lived classifier and workflow sessions are deleted. `/chat` and Telegram continue using the existing `ask_agent()` entry point.

## Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| FastAPI app | `my_agent/backend/main.py` | Exposes `/health`, `/chat`, `/api/analyze-pdf`, and `/telegram/webhook`; manages optional Telegram lifecycle |
| PDF extractor | `my_agent/backend/pdf/extractor.py` | Validates and extracts PDF text per page with upload, page, and text limits |
| Document classifier | `my_agent/backend/pdf/document_classifier.py` | Validates model-produced type, confidence, and available metadata; uses bounded input, timeout, and a general-workflow fallback |
| Workflow router | `my_agent/backend/research/router.py` | Routes confident seminal papers to the existing coordinator and general/uncertain papers to the general analysis agent |
| ADK runner | `my_agent/backend/adk_runner.py` | Creates in-memory sessions, runs root or specialized agents through shared execution services, extracts final response text, and deletes short-lived sessions |
| Telegram bot | `my_agent/backend/telegram.py` | Handles `/start`, text messages, webhook updates, webhook setup, and optional debug polling |
| Telegram messages | `my_agent/backend/telegram_messages.py` | Splits long responses and handles Telegram send/edit/delete failures |
| Coordinator agent | `my_agent/agent.py` | Defines the root ADK agent and wires sub-agents as tools |
| Environment loader | `my_agent/env.py` | Loads `my_agent/.env` and validates required values |
| Web research sub-agent | `my_agent/sub_agents/academic_webresearch` | Searches for recent citing or related papers using ADK Google Search |
| Future research sub-agent | `my_agent/sub_agents/academic_newresearch` | Synthesizes research gaps and future directions |
| General research agent | `my_agent/sub_agents/academic_generalresearch` | Analyzes a general paper and distinguishes document evidence from suggestions |

## Data Flow

1. The user sends a request through `/chat`, uploads a PDF in the browser or API, or sends a Telegram message.
2. FastAPI validates the request body or Telegram webhook secret.
3. `adk_runner.ask_agent` creates or reuses an in-memory session for `user_id`.
4. The coordinator agent processes the request.
5. The coordinator invokes sub-agents through ADK `AgentTool`.
6. The final ADK response is returned as JSON or sent back through Telegram.
7. A PDF upload is validated and extracted once; the classifier receives a bounded excerpt of page-labeled text.
8. A valid classification selects the workflow. Seminal confidence below `0.70` is treated as uncertain and routed to general analysis.
9. Invalid output, insufficient classification text, classifier timeout, or model failure produces a general-workflow fallback with confidence `0`; the API reports that fallback.
10. The selected workflow receives the full extracted text once. Temporary classifier and workflow sessions are deleted.

Classification is a model-assisted inference, not an objective claim about scholarly impact. The classifier considers contribution and novelty alongside publication context and references when present; age, self-description, or reference count alone are not sufficient signals.

## Session Model

Sessions are stored in `InMemorySessionService`. The current `session_id` is the same as `user_id`, which gives each user one active conversation context per backend process.

This is simple and useful for local development, but it has deployment limits:

- Sessions are lost on restart.
- Multiple backend replicas do not share session state.
- There is no retention policy or user-level history management.

Persistent session storage should be introduced before multi-instance production deployment.

## Telegram Modes

Webhook mode is the intended Telegram runtime mode. `main.py` initializes the Telegram app during FastAPI lifespan only when Telegram is enabled, and optionally registers a webhook when `TELEGRAM_WEBHOOK_URL` is configured. Telegram remains enabled by default when `TELEGRAM_TOKEN` is configured; `ENABLE_TELEGRAM=false` selects web-only mode. Setting `ENABLE_TELEGRAM=true` requires a valid `TELEGRAM_TOKEN`.

Webhook requests can be protected with `TELEGRAM_WEBHOOK_SECRET`. When configured, FastAPI validates Telegram's `X-Telegram-Bot-Api-Secret-Token` header before accepting updates.

Polling mode is guarded by `ENABLE_TELEGRAM_POLLING=1` and should be used only for local debugging.
