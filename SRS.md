# Software Requirements Specification

## ResearchFlow AI

**Document Version:** 4.3
**Date:** 2026-09-29
**Project:** ResearchFlow AI - Academic Research Assistant  
**Author:** orignlkartik1

## 1. Introduction

### 1.1 Purpose

ResearchFlow AI is a multi-agent assistant for academic literature exploration. It analyzes a seminal paper or research prompt, discovers recent citing or related papers, and proposes future research directions through a direct HTTP API and a Telegram bot interface.

### 1.2 Scope

The current system includes:

- Google ADK coordinator and sub-agent orchestration.
- FastAPI backend with `/health`, `/chat`, `/api/analyze-pdf`, and `/telegram/webhook`.
- In-memory PDF validation and page-by-page text extraction for text-based PDFs.
- Telegram bot integration using `python-telegram-bot`.
- Webhook-first Telegram runtime with optional local polling.
- In-memory conversation sessions.
- Environment-based configuration for credentials and webhook options.
- Long Telegram response splitting and optional text attachment delivery.

### 1.3 Definitions

| Term | Definition |
|------|------------|
| ADK | Google Agent Development Kit |
| AgentTool | ADK wrapper that allows one agent to call another agent |
| Coordinator | Root agent that manages the complete user-facing workflow |
| Seminal paper | Foundational academic work used as the research starting point |
| Session | Conversation context associated with a user ID |
| Webhook | HTTP endpoint used by Telegram to deliver bot updates |

## 2. Overall Description

### 2.1 Product Perspective

ResearchFlow AI is a Python service composed of:

1. A Google ADK agent graph.
2. A FastAPI HTTP application.
3. A Telegram bot application managed by FastAPI lifecycle hooks.
4. External Google model/search services and Telegram Bot API.

### 2.2 Product Functions

- Accept research requests through HTTP or Telegram.
- Extract useful context from a paper title, citation, abstract, summary, or metadata.
- Search for recent papers that cite or extend the seminal work.
- Group recent papers by year and include source links where available.
- Generate at least 10 future research areas when enough input evidence exists.
- Preserve context for follow-up questions while the process is running.
- Protect Telegram webhook requests with an optional shared secret.
- Deliver long Telegram responses without exceeding Telegram message limits.
- Send extracted PDF research context through the existing `ask_agent()` path.

### 2.3 User Classes

- Researchers exploring literature trends.
- Students preparing thesis or dissertation topics.
- Academics evaluating citation influence.
- API consumers integrating the research workflow into another application.
- Telegram users who prefer a chat interface.

### 2.4 Operating Environment

- Python `>=3.13`
- `uv` for dependency management
- FastAPI with Uvicorn
- Google ADK `2.3.0`
- `python-telegram-bot` `22.8+`
- Internet access for model, search, and Telegram APIs

### 2.5 Constraints

- Credentials must be provided through environment variables or `my_agent/.env`.
- `TELEGRAM_TOKEN` is required only when Telegram integration is enabled.
- In-memory sessions do not survive process restarts.
- PDF uploads are limited to 15 MiB, 100 pages, and 120,000 extracted text characters.
- OCR for scanned/image-only PDFs is not implemented.
- Web research depends on the ADK Google Search tool and available public search results.

## 3. Functional Requirements

### 3.1 Paper Analysis

- **F1.1** The system shall accept paper titles, citations, abstracts, summaries, or paper metadata through user messages.
- **F1.2** The coordinator shall extract title, authors, publication year, abstract, summary, keywords, innovations, and references when available.
- **F1.3** The coordinator shall clearly state when required metadata cannot be determined from the provided input.
- **F1.4** PDF uploads shall be analyzed according to the PDF Analysis API requirements in F7.

### 3.2 Web Research

- **F2.1** The web research sub-agent shall use the ADK Google Search tool.
- **F2.2** The sub-agent shall search for recent citing or related papers from the current year and previous year.
- **F2.3** The sub-agent shall target at least 10 distinct papers per year when available.
- **F2.4** Results shall include title, authors, year, source, and link when available.
- **F2.5** Results shall be deduplicated and grouped by year.
- **F2.6** The sub-agent shall document search limitations when the target count cannot be met.

### 3.3 Future Research Synthesis

- **F3.1** The future research sub-agent shall analyze the seminal paper and recent paper collection.
- **F3.2** The sub-agent shall generate at least 10 distinct future research areas when input evidence is sufficient.
- **F3.3** Each area shall include a concise title and rationale.
- **F3.4** Suggestions shall balance practical utility, unexpectedness, and emerging popularity.
- **F3.5** Relevant authors may be listed when the source material supports that mapping.

### 3.4 API Backend

- **F4.1** The backend shall expose `POST /chat`.
- **F4.2** The request body shall include `user_id` and `message`.
- **F4.3** The backend shall create an ADK session for a new user ID.
- **F4.4** The backend shall preserve context across requests for the same user ID while the process is running.
- **F4.5** The backend shall return JSON containing a `response` field.
- **F4.6** Runtime agent failures shall return `503` with a useful message.

### 3.5 Telegram Interface

- **F5.1** The bot shall respond to `/start`.
- **F5.2** The bot shall process text messages through the same ADK runner used by `/chat`.
- **F5.3** The bot shall send Telegram typing status while work is in progress.
- **F5.4** The bot shall show a processing message while the agent runs.
- **F5.5** The bot shall split long responses to respect Telegram message limits.
- **F5.6** Very large responses may be delivered as UTF-8 text attachments.
- **F5.7** Webhook mode shall support optional secret token validation.
- **F5.8** Long polling shall be available only when explicitly enabled for local debugging.

### 3.6 Telegram Webhook

- **F6.1** The backend shall expose `POST /telegram/webhook`.
- **F6.2** The webhook shall accept Telegram update JSON.
- **F6.3** The webhook shall reject invalid JSON with `400`.
- **F6.4** The webhook shall reject invalid secret tokens with `403` when `TELEGRAM_WEBHOOK_SECRET` is configured.
- **F6.5** The webhook shall schedule update processing in a background task and return `{"ok": true}`.
- **F6.6** FastAPI startup shall initialize and start the Telegram application when Telegram integration is enabled.
- **F6.7** FastAPI shutdown shall stop and shut down Telegram when it was started.
- **F6.8** FastAPI startup shall register the Telegram webhook when Telegram is enabled and `TELEGRAM_WEBHOOK_URL` is configured.

### 3.7 PDF Analysis API

- **F7.1** The backend shall expose `POST /api/analyze-pdf` accepting a multipart `file` upload.
- **F7.2** The endpoint shall validate the filename, PDF signature, PDF structure, and non-empty upload.
- **F7.3** The endpoint shall extract text per page and preserve page boundaries in the research input.
- **F7.4** The endpoint shall reject uploads over 15 MiB, documents over 100 pages, or extracted text over 120,000 characters without truncation.
- **F7.5** The endpoint shall reject image-only or otherwise text-empty PDFs with a clear `NO_EXTRACTABLE_TEXT` error; OCR is out of scope.
- **F7.6** The endpoint shall submit extracted text to the existing `ask_agent()` path and return its response with filename and page count.
- **F7.7** The endpoint shall not permanently store uploaded PDFs and shall delete its temporary ADK session after analysis.
- **F7.8** PDF processing and research failures shall return structured JSON errors without exposing credentials or internal tracebacks.

## 4. Non-Functional Requirements

### 4.1 Performance

- **NF1.1** Simple API validation and session lookup should complete in under 2 seconds.
- **NF1.2** Agent response time depends on model and search latency; long-running research requests may exceed normal HTTP chat latency.
- **NF1.3** Telegram users shall receive immediate processing feedback.

### 4.2 Reliability

- **NF2.1** The backend shall handle malformed JSON and invalid webhook secrets.
- **NF2.2** Telegram send/edit/delete errors shall be logged without crashing the process.
- **NF2.3** Agent execution failures shall be logged and surfaced to callers with actionable messages.
- **NF2.4** Long response chunk failures shall not prevent the bot from attempting later chunks.

### 4.3 Security

- **NF3.1** Credentials shall not be committed to source control.
- **NF3.2** `.env` files shall be treated as local secrets.
- **NF3.3** Telegram webhook requests shall be protected with `TELEGRAM_WEBHOOK_SECRET` in deployed environments.
- **NF3.4** Error messages shall not include API keys, tokens, or secret values.
- **NF3.5** User input shall be treated as untrusted content.

### 4.4 Maintainability

- **NF4.1** Code shall follow clear Python module boundaries.
- **NF4.2** Agent prompts shall remain in prompt modules.
- **NF4.3** Backend route handlers shall delegate agent execution to `adk_runner.py`.
- **NF4.4** Telegram message delivery helpers shall remain separate from Telegram update handlers.
- **NF4.5** Documentation shall be updated with behavior-changing code changes.

## 5. Architecture

```text
Telegram user or API client
        |
        v
FastAPI app: my_agent.backend.main
        |
        v
ADK runner: my_agent.backend.adk_runner
        |
        v
Coordinator agent: my_agent.agent
        |
        +--> Web research sub-agent + Google Search
        |
        +--> Future research sub-agent
        |
        v
Response returned to API client or Telegram user
```

Design detail is maintained in:

- [DESIGN.md](./DESIGN.md): product, interaction, agent, response, API, and runtime design.
- [HLD.md](./HLD.md): high-level system design, system context, layers, deployment view, and major decisions.
- [LLD.md](./LLD.md): module-level design, concrete functions, API contracts, session logic, and error handling.
- [ARCHITECTURE.md](./ARCHITECTURE.md): concise architecture reference and data flow.

## 6. Data Requirements

### 6.1 Input Data

- `user_id`
- User message text
- Paper title, DOI, abstract, citation, summary, or metadata
- Telegram update JSON for webhook requests
- Optional conversation context from an existing in-memory session

### 6.2 Output Data

- Paper summary and extracted metadata
- Recent citing or related papers
- Future research directions
- Telegram chat messages or text attachments
- Error details for recoverable failures

### 6.3 Storage

- Runtime sessions: in-memory ADK session service
- Configuration: process environment and `my_agent/.env`
- Logs: application logger output
- Temporary files: text attachments for extremely large Telegram responses
- PDF uploads and extracted text: process memory only; temporary per-request ADK sessions are deleted after analysis
- Persistent storage: not currently implemented

## 7. Interface Requirements

### 7.1 Chat API

`POST /chat`

```json
{
  "user_id": "string",
  "message": "string"
}
```

Success response:

```json
{
  "response": "string"
}
```

### 7.2 Telegram Webhook

`POST /telegram/webhook`

- Accepts Telegram update JSON.
- Validates `X-Telegram-Bot-Api-Secret-Token` when a secret is configured.
- Schedules update processing in a background task.
- Returns `{"ok": true}`.

### 7.3 PDF Analysis

`POST /api/analyze-pdf` accepts multipart form data with a `file` field. Successful responses include `success`, `filename`, `page_count`, and `result.response`. Errors include a stable error `code` and safe user-facing `message`.

## 8. Acceptance Criteria

- [ ] `/chat` accepts valid requests and returns a response.
- [ ] `/health` returns `{"status":"ok"}`.
- [ ] `/api/analyze-pdf` extracts text PDFs and preserves page boundaries in the agent input.
- [ ] `/api/analyze-pdf` rejects empty, non-PDF, malformed, image-only, and oversized documents.
- [ ] PDF analysis uses `ask_agent()` and removes its temporary ADK session.
- [ ] Sessions are reused for repeated `user_id` values.
- [ ] `/telegram/webhook` rejects invalid secrets when a secret is configured.
- [ ] `/telegram/webhook` rejects invalid JSON.
- [ ] FastAPI startup initializes the Telegram application.
- [ ] FastAPI shutdown stops the Telegram application.
- [ ] The Telegram bot handles `/start`.
- [ ] The Telegram bot handles text messages through `ask_agent`.
- [ ] The Telegram bot handles long responses without exceeding message limits.
- [ ] Missing credentials fail with actionable messages.
- [ ] README, SRS, HLD, LLD, architecture, design, security, contribution, code of conduct, and changelog documents are present.
- [ ] No real secrets are included in documentation or examples.

## 9. Future Enhancements

- Persistent session storage with PostgreSQL, MongoDB, or Redis.
- OCR for scanned PDFs.
- Citation graph visualization.
- Web dashboard for saved research projects.
- Export to Markdown, PDF, JSON, and BibTeX.
- Authentication and per-user rate limiting for public deployments.
- Structured observability with metrics and tracing.
- Tests for API, Telegram, message splitting, and agent runner behavior.

## 10. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-09 | orignlkartik1 | Initial SRS |
| 2.0 | 2026-07-12 | orignlkartik1 | Added backend, FastAPI, and session details |
| 3.0 | 2026-07-18 | orignlkartik1 | Expanded multi-turn and future enhancement requirements |
| 4.0 | 2026-08-08 | orignlkartik1 | Aligned requirements with webhook mode, model fallback, and documentation set |
| 4.1 | 2026-08-08 | orignlkartik1 | Added HLD and LLD references for complete design traceability |
| 4.2 | 2026-09-07 | orignlkartik1 | Aligned requirements with current Telegram webhook implementation, ADK runner, and documentation updates |
| 4.3 | 2026-09-29 | orignlkartik1 | Added bounded in-memory PDF analysis through the shared research path |
