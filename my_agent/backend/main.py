import hmac
import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import PurePosixPath
from typing import Annotated

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Header,
    HTTPException,
    Request,
    UploadFile,
)
from pydantic import BaseModel
from starlette.responses import JSONResponse

from my_agent.backend.adk_runner import ask_agent, discard_agent_session
from my_agent.backend.pdf.extractor import (
    MAX_PDF_UPLOAD_BYTES,
    ExtractedDocument,
    InvalidPDFError,
    NoExtractableTextError,
    PDFExtractionError,
    PDFTooLargeError,
    extract_pdf,
)
from my_agent.backend.telegram import (
    get_telegram_application,
    process_telegram_update,
    set_telegram_webhook,
)
from my_agent.env import is_telegram_enabled, load_environment

load_environment()
TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
TELEGRAM_WEBHOOK_URL = os.environ.get("TELEGRAM_WEBHOOK_URL")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    telegram_app = None
    try:
        if is_telegram_enabled():
            telegram_app = get_telegram_application()
            await telegram_app.initialize()
            await telegram_app.start()

            if TELEGRAM_WEBHOOK_URL:
                await set_telegram_webhook(
                    TELEGRAM_WEBHOOK_URL,
                    secret_token=TELEGRAM_WEBHOOK_SECRET,
                )
        else:
            logger.info("Telegram integration is disabled; starting in web-only mode")

        yield
    finally:
        if telegram_app is not None:
            await telegram_app.stop()
            await telegram_app.shutdown()


app = FastAPI(lifespan=lifespan)


class ChatRequest(BaseModel):
    user_id: str
    message: str


def _pdf_error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
            },
        },
    )


def _build_pdf_analysis_message(document: ExtractedDocument) -> str:
    return (
        "The user has provided the following research paper as source material. "
        "Analyze it now using the ResearchFlow-AI research workflow; do not ask "
        "the user to provide the paper again. Page labels identify the original "
        "PDF page boundaries.\n\n"
        f"{document.research_text()}"
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        response = await ask_agent(
            req.user_id,
            req.message,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "response": response
    }


@app.post("/api/analyze-pdf")
async def analyze_pdf(file: Annotated[UploadFile | None, File()] = None):
    if file is None:
        return _pdf_error(400, "FILE_REQUIRED", "Upload a PDF file in the 'file' field.")

    try:
        filename = (file.filename or "").replace("\\", "/").rsplit("/", maxsplit=1)[-1]
        if not filename:
            return _pdf_error(400, "INVALID_FILE", "The uploaded file must have a .pdf filename.")
        if PurePosixPath(filename).suffix.lower() != ".pdf":
            return _pdf_error(400, "INVALID_FILE", "The uploaded file must be a PDF.")

        file_bytes = await file.read(MAX_PDF_UPLOAD_BYTES + 1)
        if not file_bytes:
            return _pdf_error(400, "EMPTY_FILE", "The uploaded PDF is empty.")
        if len(file_bytes) > MAX_PDF_UPLOAD_BYTES:
            return _pdf_error(413, "FILE_TOO_LARGE", "The PDF exceeds the 15 MiB upload limit.")

        document = extract_pdf(file_bytes, filename)
    except InvalidPDFError as exc:
        return _pdf_error(400, "INVALID_PDF", str(exc))
    except NoExtractableTextError as exc:
        return _pdf_error(422, "NO_EXTRACTABLE_TEXT", str(exc))
    except PDFTooLargeError as exc:
        return _pdf_error(413, "DOCUMENT_TOO_LARGE", str(exc))
    except PDFExtractionError as exc:
        logger.error("PDF text extraction failed (%s)", type(exc).__name__)
        return _pdf_error(500, "PDF_EXTRACTION_FAILED", "The PDF text could not be extracted.")
    except Exception as exc:
        logger.error("Unexpected failure while processing uploaded PDF (%s)", type(exc).__name__)
        return _pdf_error(500, "PDF_PROCESSING_FAILED", "The uploaded PDF could not be processed.")
    finally:
        await file.close()

    research_user_id = f"pdf-upload-{uuid.uuid4().hex}"
    research_failed = False
    try:
        response = await ask_agent(
            research_user_id,
            _build_pdf_analysis_message(document),
        )
    except Exception as exc:
        logger.error("ResearchFlow analysis failed for uploaded PDF (%s)", type(exc).__name__)
        research_failed = True

    try:
        await discard_agent_session(research_user_id)
    except Exception as exc:
        logger.error("Failed to clear temporary PDF analysis session (%s)", type(exc).__name__)
        return _pdf_error(
            500,
            "SESSION_CLEANUP_FAILED",
            "The analysis session could not be safely cleared.",
        )

    if research_failed:
        return _pdf_error(
            502,
            "RESEARCH_PROCESSING_FAILED",
            "ResearchFlow-AI could not complete the analysis. Please try again.",
        )

    return {
        "success": True,
        "filename": document.filename,
        "page_count": document.page_count,
        "result": {
            "response": response,
        },
    }


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
):
    if not is_telegram_enabled():
        raise HTTPException(status_code=503, detail="Telegram integration is disabled")

    if TELEGRAM_WEBHOOK_SECRET and not hmac.compare_digest(
        x_telegram_bot_api_secret_token or "",
        TELEGRAM_WEBHOOK_SECRET,
    ):
        raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret")

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Telegram update payload") from exc

    background_tasks.add_task(process_telegram_update, payload)

    return {
        "ok": True
    }
