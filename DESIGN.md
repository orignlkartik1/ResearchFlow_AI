# Design

## Product Goal

ResearchFlow AI reduces the manual effort of early academic literature exploration. A user should be able to provide a paper title, citation, abstract, metadata, research prompt, or text-based PDF and receive a structured research response containing paper context, recent citing work, and potential future research directions.

## Design Document Map

- [SRS.md](./SRS.md) defines requirements, constraints, interfaces, and acceptance criteria.
- [HLD.md](./HLD.md) describes the high-level system design, layers, runtime flow, and deployment view.
- [LLD.md](./LLD.md) describes modules, functions, contracts, session handling, and error behavior.
- [ARCHITECTURE.md](./ARCHITECTURE.md) provides a concise architecture reference.

## Interaction Design

The primary interaction supports both conversational research and routed PDF analysis:

1. The user submits a research request through Telegram or `POST /chat`, or uploads a PDF through `POST /api/analyze-pdf`.
2. For a PDF, the backend extracts page-labeled text and classifies a bounded excerpt for document type, confidence, and available metadata.
3. A confident seminal classification selects the existing coordinator and its web-research and future-research sub-agents.
4. General or uncertain classifications select a separate general-paper analysis agent.
5. The system returns workflow and classification metadata alongside the research response.
6. Conversational users can continue through `/chat` or Telegram in their existing in-memory session.

Telegram is optimized for lightweight, ongoing chat. The HTTP API is optimized for integration, testing, and non-Telegram clients.

## Agent Design

The agent graph uses a coordinator pattern:

- `academic_coordinator` owns the user-facing workflow and final response.
- `academic_websearch_agent` owns retrieval using the ADK `google_search` tool.
- `academic_newresearch_agent` owns synthesis of gaps and future directions.
- `academic_generalresearch_agent` analyzes general papers without assuming they are seminal.

The coordinator exposes sub-agents as ADK `AgentTool` tools. This keeps retrieval and synthesis responsibilities separate while allowing the root agent to compose the final response.

The PDF classifier returns validated structured data and a confidence score. Confidence below `0.70`, malformed output, insufficient classifier text, model failure, or timeout selects general analysis; classifier failure is explicitly returned as a general fallback with zero confidence. "Seminal" is an inference, not an objective determination.

## Response Design

Responses should be structured and explicit about missing information. The system should prefer:

- Clear section headings for paper context, recent papers, and future directions.
- Grouping recent papers by publication year.
- Counts of distinct papers found per year.
- Title, authors, year, source, and link when available.
- Short rationales for future research suggestions.
- Direct statements when metadata, citations, or evidence are unavailable.

For Telegram, responses must also respect chat delivery constraints. Long responses are split into multiple messages. Extremely large responses can be delivered as a text attachment.

## API Design

The direct chat API intentionally keeps a minimal contract:

```json
{
  "user_id": "string",
  "message": "string"
}
```

`user_id` is also used as the ADK session identifier. This keeps context management simple for the current single-process implementation.

The Telegram webhook endpoint accepts raw Telegram update JSON and delegates processing to the Telegram application in a FastAPI background task. Optional webhook secret validation is controlled by environment configuration.

`POST /api/analyze-pdf` accepts one PDF in the multipart `file` field. It extracts page-labeled text in memory, enforces size/page/text limits, classifies a bounded excerpt, then routes the full text to the selected workflow. The existing `success`, `filename`, `page_count`, and `result.response` fields are preserved; `document` and `workflow` are additive. Temporary classifier and workflow sessions are deleted; the uploaded PDF is not permanently stored.

## Telegram Runtime Design

Webhook mode is the intended runtime design:

- FastAPI starts and stops the Telegram application through its lifespan hook.
- `TELEGRAM_WEBHOOK_URL`, when set, is registered at startup.
- `TELEGRAM_WEBHOOK_SECRET`, when set, is checked against Telegram's secret-token header.
- Incoming updates are processed through `process_telegram_update`.

Long polling remains available only for local debugging. It is guarded by `ENABLE_TELEGRAM_POLLING=1` so production deployments do not accidentally start polling.

## Configuration Design

Runtime configuration is environment-based. `my_agent/.env` is loaded through `python-dotenv` for local development, while deployed environments should provide values through the process environment or a secret manager.

Required:

- `GOOGLE_API_KEY`

`TELEGRAM_TOKEN` is required only when Telegram integration is enabled.

Optional:

- `TELEGRAM_WEBHOOK_URL`
- `TELEGRAM_WEBHOOK_SECRET`
- `ENABLE_TELEGRAM_POLLING`

The current code uses fixed `gemini-2.5-flash` model declarations in the coordinator and sub-agent modules.

## Current Tradeoffs

- In-memory sessions are simple but not durable.
- The session ID is the same as `user_id`, which gives one active conversation context per user per process.
- Webhook mode is better suited to deployment than polling.
- Search depends on general Google Search results through ADK rather than direct scholarly database APIs.
- OCR is not supported for scanned/image-only PDFs.

## Future Design Direction

- Add persistent sessions and user-level history.
- Add OCR for scanned PDF/document uploads.
- Add scholarly database integrations.
- Add structured result export.
- Add citation graph exploration.
- Add a web dashboard for saved research projects.
