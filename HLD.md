# High-Level Design

## ResearchFlow AI

## 1. Purpose

This High-Level Design describes the major system components, responsibilities, integrations, and runtime flows for the current ResearchFlow AI implementation, including confidence-based PDF understanding and workflow selection. It complements [SRS.md](./SRS.md), [DESIGN.md](./DESIGN.md), and [LLD.md](./LLD.md).

## 2. System Context

ResearchFlow AI accepts academic research requests through a standalone browser interface, direct HTTP API, text-based PDF upload, or a Telegram bot. Uploaded PDFs are classified and routed to either the existing Google ADK seminal-paper coordinator and its sub-agents or a new general-paper analysis agent.

```text
User / API Client / PDF Upload / Telegram
        |
        v
ResearchFlow AI FastAPI Backend
        |
        +--> Google ADK / Gemini
        +--> ADK Google Search tool
        +--> Telegram Bot API
```

## 3. High-Level Architecture

```text
+-------------------------+
| Interface Layer         |
| - HTTP API clients      |
| - Telegram users        |
+-----------+-------------+
            |
            v
+-------------------------+
| API and Lifecycle Layer |
| - FastAPI app           |
| - /chat                 |
| - /api/analyze-pdf      |
| - /telegram/webhook     |
| - Telegram app startup  |
+-----------+-------------+
            |
            v
+-------------------------+
| Orchestration Layer     |
| - ADK Runner            |
| - In-memory sessions    |
| - PDF session cleanup   |
+-----------+-------------+
            |
            v
+-------------------------+
| Agent Layer             |
| - Coordinator agent     |
| - Web research agent    |
| - Future research agent |
+-----------+-------------+
            |
            v
+-------------------------+
| External Services       |
| - Google ADK / Gemini   |
| - Google Search         |
| - Telegram Bot API      |
+-------------------------+
```

PDF research workflows route after document understanding:

```text
PDF
 |
 v
Document Understanding
 |
+----------------------+----------------------+
|                                             |
v                                             v
Seminal (confident)                    General or uncertain
|                                             |
v                                             v
Existing academic coordinator          General paper analysis
|                                             |
+----------------------+----------------------+
                       |
                       v
                 Research insights
```

## 4. Major Components

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| Interface | HTTP clients | Call `/chat` with a user ID and message |
| Interface | PDF upload clients | Send PDFs to `/api/analyze-pdf` |
| Interface | Telegram users | Send `/start` and text messages to the bot |
| API | FastAPI app | Validates API/PDF requests, validates webhook secrets, manages optional Telegram lifecycle |
| PDF | PDF extractor | Validates PDF files and extracts bounded, page-labeled text in memory |
| Understanding | Document classifier | Classifies a bounded text excerpt; validates confidence and available metadata and falls back safely |
| Research | Workflow router | Routes confident seminal papers to the existing coordinator and general/uncertain papers to general analysis |
| Telegram | Telegram application | Parses updates, handles commands/messages, sends responses |
| Orchestration | ADK runner | Creates sessions, executes the root agent, extracts final response text |
| Agent | Coordinator | Owns the user-facing research workflow and invokes sub-agents |
| Agent | Web research | Uses ADK Google Search to find recent citing or related papers |
| Agent | Future research | Synthesizes gaps and future research suggestions |
| Agent | General paper analysis | Analyzes methods, data, results, limits, gaps, and directions without assuming a seminal paper |
| Config | Environment loader | Loads `my_agent/.env` and validates required values |

## 5. Core Data Flows

### 5.1 Direct Chat API

1. API client sends `POST /chat` with `user_id` and `message`.
2. FastAPI validates the request body.
3. The route calls `ask_agent(user_id, message)`.
4. The ADK runner creates or reuses an in-memory session.
5. The coordinator agent processes the request and invokes sub-agents as needed.
6. The ADK runner extracts the final response text.
7. FastAPI returns `{"response": "..."}`.

### 5.2 Telegram Webhook

1. Telegram sends an update to `POST /telegram/webhook`.
2. FastAPI validates `X-Telegram-Bot-Api-Secret-Token` when `TELEGRAM_WEBHOOK_SECRET` is configured.
3. FastAPI parses the JSON update and schedules background processing.
4. `process_telegram_update` converts JSON into a Telegram `Update`.
5. The Telegram application dispatches the update to command or text handlers.
6. The text handler sends typing status and a processing message.
7. The handler calls `ask_agent` directly.
8. The bot deletes or edits the processing message and sends the response, splitting long output when needed.

### 5.3 PDF Analysis API

1. A client uploads a `.pdf` file to `POST /api/analyze-pdf`.
2. The backend enforces upload size, PDF content, page count, and extracted-text limits.
3. pypdf extracts text page by page once; scanned/image-only documents without usable text are rejected.
4. The classifier receives a bounded excerpt from the beginning and end of the extracted text and returns validated type, confidence, and metadata.
5. Confident seminal documents use the existing `ask_agent()` coordinator path; general or uncertain documents use the general-paper analysis agent through shared ADK runner/session services.
6. Model errors, timeouts, or malformed classification output select general analysis with confidence `0` and an explicit fallback status.
7. Temporary classifier and research sessions are deleted after analysis.
8. The API preserves existing success fields and adds document classification metadata and the selected workflow; the PDF is not permanently stored.

Classification is a model-assisted estimate, not an objective judgment of scholarly influence. Publication age, self-description, or reference count alone do not qualify a paper as seminal.

## 6. Deployment View

The current target deployment is a single FastAPI application process served by Uvicorn.

```text
Uvicorn process
    |
    +-- FastAPI app
    +-- Optional Telegram application lifecycle
    +-- Telegram webhook processing
    +-- In-memory ADK sessions
    +-- Agent execution
```

For production scaling, session persistence and shared state should be added before running multiple backend replicas.

## 7. Security Design

- Credentials are loaded from environment variables or `my_agent/.env`.
- `TELEGRAM_TOKEN` is required for Telegram integration.
- Telegram webhooks can be protected with `TELEGRAM_WEBHOOK_SECRET`.
- Webhook secret comparison uses `hmac.compare_digest`.
- User messages are treated as untrusted input.
- API keys and tokens must not be logged or committed.

See [SECURITY.md](./SECURITY.md) for operational security guidance.

## 8. Key Design Decisions

- Use FastAPI as the single runtime entry point for direct API and Telegram webhook traffic.
- Use the `python-telegram-bot` application lifecycle inside FastAPI instead of a separate polling process.
- Keep long polling as an explicitly enabled local debugging mode.
- Use a coordinator/sub-agent model to separate workflow control, retrieval, and synthesis.
- Use `InMemorySessionService` for early-stage session management.
- Use fixed `gemini-2.5-flash` agent model declarations in the current codebase.

## 9. Known Limitations

- Sessions are not durable.
- Multiple backend replicas would not share conversation context.
- OCR is not available for scanned/image-only PDFs.
- PDF uploads are limited to 15 MiB, 100 pages, and 120,000 extracted text characters.
- There is no authentication or rate limiting for `/chat`.
- Search quality depends on the ADK Google Search tool and public web results.
