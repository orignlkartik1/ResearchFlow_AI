# Low-Level Design

## ResearchFlow AI

## 1. Purpose

This Low-Level Design describes the concrete modules, functions, data contracts, and runtime logic used by the current ResearchFlow AI implementation. It should be read with [SRS.md](./SRS.md), [DESIGN.md](./DESIGN.md), and [HLD.md](./HLD.md).

## 2. Module Design

| Module | Primary Items | Responsibility |
|--------|---------------|----------------|
| `my_agent/env.py` | `ENV_PATH`, `load_environment`, `require_env`, `is_telegram_enabled` | Loads `my_agent/.env`, validates required values, and resolves Telegram activation |
| `my_agent/agent.py` | `root_agent` | Defines the root ADK coordinator and wires sub-agents through `AgentTool` |
| `my_agent/prompt.py` | `ACADEMIC_COORDINATOR_PROMPT` | Defines the coordinator workflow and output expectations |
| `my_agent/backend/main.py` | `app`, `lifespan`, `ChatRequest`, `health`, `chat`, `analyze_pdf`, `telegram_webhook` | Defines FastAPI lifecycle and HTTP routes |
| `my_agent/backend/adk_runner.py` | `APP_NAME`, `session_service`, `_ensure_session`, `_run_once`, `ask_agent`, `discard_agent_session` | Runs ADK agents and manages process-local sessions |
| `my_agent/backend/pdf/extractor.py` | `extract_pdf`, `ExtractedDocument`, `ExtractedPage` | Validates in-memory PDF bytes, extracts page text, and enforces document limits |
| `my_agent/backend/telegram.py` | `start`, `chat`, `get_telegram_application`, `create_telegram_application`, `process_telegram_update`, `set_telegram_webhook`, `delete_telegram_webhook` | Lazily creates the Telegram application and handles commands, messages, webhooks, and debug polling |
| `my_agent/backend/telegram_messages.py` | `split_telegram_message`, `send_long_message`, `reply_long_text`, `safe_delete_message`, `safe_edit_text` | Handles Telegram message limits and send/edit/delete failures |
| `my_agent/sub_agents/academic_webresearch/agent.py` | `academic_websearch_agent` | Defines the retrieval sub-agent using `google_search` |
| `my_agent/sub_agents/academic_webresearch/prompt.py` | `ACADEMIC_WEBSEARCH_PROMPT` | Defines recent citing-paper search behavior |
| `my_agent/sub_agents/academic_newresearch/agent.py` | `academic_newresearch_agent` | Defines the future research synthesis sub-agent |
| `my_agent/sub_agents/academic_newresearch/prompt.py` | `ACADEMIC_NEWRESEARCH_PROMPT` | Defines future research output behavior |

## 3. API Contracts

### 3.1 `POST /chat`

Request model:

```python
class ChatRequest(BaseModel):
    user_id: str
    message: str
```

Success response:

```json
{
  "response": "agent response text"
}
```

Error behavior:

- Runtime agent failures are converted to `HTTPException(status_code=503)`.
- FastAPI/Pydantic validation handles invalid request bodies.

### 3.2 `POST /telegram/webhook`

Inputs:

- Telegram update JSON body.
- Optional `X-Telegram-Bot-Api-Secret-Token` header.

Behavior:

- Rejects invalid webhook secrets with `403` when `TELEGRAM_WEBHOOK_SECRET` is configured.
- Rejects invalid JSON with `400`.
- Adds `process_telegram_update(payload)` as a FastAPI background task.
- Returns `{"ok": true}` once the update is accepted for processing.
- Returns `503` when Telegram integration is disabled.

### 3.3 `GET /health`

Returns `{"status": "ok"}` without exposing configuration or credentials.

### 3.4 `POST /api/analyze-pdf`

Input: multipart form field `file` containing a `.pdf` file with a valid PDF header.

Processing flow:

1. Read at most 15 MiB plus one byte from the upload.
2. Validate PDF content and extract each page's text in memory.
3. Reject documents over 100 pages or 120,000 extracted text characters.
4. Reject documents with fewer than 20 extractable alphanumeric characters; scanned/image-only PDFs are not OCR-processed.
5. Send page-labeled text to `ask_agent()` with a fresh, per-request user ID.
6. Close the upload and return the analysis response and page count.

Success includes `success`, `filename`, `page_count`, and `result.response`. Failures return a JSON `error` object with a stable code; model failures return `502` without provider details.

## 4. FastAPI Lifecycle

`main.py` defines an async lifespan context manager. It starts Telegram only when `is_telegram_enabled()` returns true:

```text
lifespan
    +-- enabled: create application, initialize, start, optionally register webhook
    +-- disabled: log web-only mode
    +-- yield
    +-- if enabled: stop and shut down Telegram
```

`ENABLE_TELEGRAM` explicitly enables or disables Telegram (`true`/`false`, `yes`/`no`, `on`/`off`, or `1`/`0`). When unset, Telegram is enabled if `TELEGRAM_TOKEN` is configured, preserving existing deployments. Enabling Telegram without a token raises the actionable `require_env` error during startup. `TELEGRAM_WEBHOOK_URL` controls automatic webhook registration. `TELEGRAM_WEBHOOK_SECRET` is passed to Telegram during webhook setup and is also used for request validation.

## 5. Agent Construction

`agent.py` defines `root_agent` directly:

```text
academic_coordinator
    |
    +-- AgentTool(academic_newresearch_agent)
    +-- AgentTool(academic_websearch_agent)
```

The coordinator and both sub-agents currently use `gemini-2.5-flash`.

`academic_websearch_agent` includes the ADK `google_search` tool. `academic_newresearch_agent` does not declare external tools; it synthesizes from provided context.

## 6. Session Handling

`adk_runner.py` uses:

- `APP_NAME = "ResearchFlowAI"`
- `InMemorySessionService`
- `_created_sessions: set`

Session flow:

```text
ask_agent(user_id, message)
    |
    +-- session_id = user_id
    +-- _ensure_session(user_id, session_id)
    +-- _run_once(user_id, session_id, message, llm_model=None)
    +-- return final response text
```

`_ensure_session` creates an ADK session only when the session ID is not already present in `_created_sessions`.

Current limitation: session tracking is process-local and is lost on restart.

## 7. ADK Runner Behavior

`_run_once`:

1. Creates a `Runner` with `app_name`, `root_agent`, and `session_service`.
2. Wraps the user message in `google.genai.types.Content`.
3. Iterates over `runner.run_async(...)`.
4. Captures text from final response events.
5. Returns the final answer string.

`ask_agent` catches any exception from the run, logs it, and raises `RuntimeError("Agent execution failed: ...")`.

## 8. Telegram Handler Behavior

### `/start`

`start(update, context)`:

- Ignores updates without a message.
- Replies with a short ResearchFlow AI welcome message.

### Text Messages

`chat(update, context)`:

1. Ignores malformed updates without a message, user, or chat.
2. Ignores messages with no text.
3. Uses Telegram `typing` chat action.
4. Sends a processing message.
5. Calls `ask_agent(user_id, message)`.
6. Deletes the processing message and sends the response.
7. Edits the processing message with an error if agent execution fails.

### Polling Guard

When `telegram.py` is executed directly, polling starts only if:

```text
ENABLE_TELEGRAM_POLLING=1
```

Otherwise, it raises a `RuntimeError` instructing operators to use the FastAPI webhook path.

## 9. Telegram Message Handling

Important constants:

- `TELEGRAM_MESSAGE_LIMIT = 4000`
- `ATTACHMENT_THRESHOLD = 100000000`

Long response behavior:

1. If response length is within the limit, send one message.
2. If response exceeds the limit, split by paragraph, then newline, then space.
3. If response exceeds the attachment threshold, create a temporary UTF-8 text file and send it as a document.
4. Continue sending remaining chunks even if one chunk fails.
5. Log Telegram API failures without crashing the process.

## 10. Environment Loading

`my_agent/env.py` loads:

```text
my_agent/.env
```

`load_environment()` is idempotent and uses `override=False`, so process environment variables take precedence over `.env` values.

`require_env(name)` raises `RuntimeError` when a required variable is missing. `telegram.py` requires `TELEGRAM_TOKEN` only when creating the Telegram application, not when the FastAPI app or Telegram module is imported.

## 11. PDF Upload Handling

`POST /api/analyze-pdf` keeps upload bytes in memory, checks the filename extension and PDF signature, and uses pypdf to open and extract text. Per-page records are retained, including pages with no text, and page labels are included in the research prompt. The original upload is closed after processing and is not permanently stored.

The upload cap is 15 MiB, the page cap is 100, and the extracted-text cap is 120,000 characters. Text is rejected at the cap rather than truncated. Image-only PDFs return `NO_EXTRACTABLE_TEXT`; OCR is not implemented. AI credentials are never returned in the API response.

## 12. Error Handling

| Area | Error | Handling |
|------|-------|----------|
| Missing required env | `RuntimeError` | Startup/import failure with actionable message |
| Invalid `/chat` body | Pydantic validation error | FastAPI validation response |
| Agent execution failure | Exception from ADK runner | Logged and returned as `503` from `/chat` |
| Invalid webhook secret | Secret mismatch | `HTTPException(403)` |
| Invalid webhook JSON | JSON parsing failure | `HTTPException(400)` |
| Invalid PDF | Invalid signature or malformed file | JSON `400` error |
| No extractable PDF text | Image-only or nearly empty extracted text | JSON `422` error |
| PDF size limit exceeded | Upload, page, or text cap | JSON `413` error |
| PDF research failure | `ask_agent` failure | Generic JSON `502` error |
| Telegram send/edit/delete failure | Telegram API or unexpected exception | Logged; bot continues |
| Direct polling without opt-in | Missing `ENABLE_TELEGRAM_POLLING=1` | `RuntimeError` |

## 13. Extension Points

- Add new sub-agents under `my_agent/sub_agents/` and expose them through `AgentTool`.
- Replace `InMemorySessionService` with persistent session storage.
- Add OCR for scanned PDFs before the coordinator prompt is invoked.
- Add authentication and rate limiting to FastAPI routes.
- Add tests for `/chat`, webhook secret validation, long-message splitting, and ADK runner error behavior.
