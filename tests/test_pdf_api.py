import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

import pymupdf
from fastapi.testclient import TestClient

from my_agent.backend import adk_runner
from my_agent.backend import main
from my_agent.backend.pdf.extractor import extract_pdf


def make_pdf(page_texts: list[str]) -> bytes:
    document = pymupdf.open()
    for text in page_texts:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    contents = document.tobytes()
    document.close()
    return contents


class PDFAPITests(unittest.TestCase):
    def request(self, method: str, path: str, **kwargs):
        with patch.dict(os.environ, {"ENABLE_TELEGRAM": "false"}):
            with TestClient(main.app) as client:
                return getattr(client, method)(path, **kwargs)

    def upload_pdf(self, contents: bytes, filename: str = "paper.pdf"):
        return self.request(
            "post",
            "/api/analyze-pdf",
            files={"file": (filename, contents, "application/pdf")},
        )

    def test_extracts_text_and_preserves_page_boundaries(self):
        extracted = extract_pdf(make_pdf(["First page research text.", "Second page research text."]), "paper.pdf")

        self.assertEqual(extracted.page_count, 2)
        self.assertEqual([page.page_number for page in extracted.pages], [1, 2])
        self.assertIn("[Page 1]\nFirst page research text.", extracted.research_text())
        self.assertIn("[Page 2]\nSecond page research text.", extracted.research_text())

    def test_valid_pdf_uses_shared_research_path(self):
        agent = AsyncMock(return_value="Research result")
        cleanup = AsyncMock()
        with (
            patch.object(main, "ask_agent", agent),
            patch.object(main, "discard_agent_session", cleanup),
        ):
            response = self.upload_pdf(make_pdf(["A substantial research paper with meaningful text."]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "success": True,
                "filename": "paper.pdf",
                "page_count": 1,
                "result": {"response": "Research result"},
            },
        )
        user_id, message = agent.await_args.args
        self.assertTrue(user_id.startswith("pdf-upload-"))
        cleanup.assert_awaited_once_with(user_id)
        self.assertIn("[Page 1]", message)
        self.assertIn("A substantial research paper", message)

    def test_missing_and_empty_uploads_are_rejected(self):
        missing = self.request("post", "/api/analyze-pdf")
        empty = self.upload_pdf(b"")

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(missing.json()["error"]["code"], "FILE_REQUIRED")
        self.assertEqual(empty.status_code, 400)
        self.assertEqual(empty.json()["error"]["code"], "EMPTY_FILE")

    def test_non_pdf_and_malformed_pdf_are_rejected(self):
        non_pdf = self.upload_pdf(b"not a pdf", filename="paper.pdf")
        wrong_extension = self.upload_pdf(make_pdf(["Valid PDF research text"]), filename="paper.txt")
        malformed = self.upload_pdf(b"%PDF-1.7\nthis is not a valid document", filename="bad.pdf")

        self.assertEqual(non_pdf.status_code, 400)
        self.assertEqual(non_pdf.json()["error"]["code"], "INVALID_PDF")
        self.assertEqual(wrong_extension.status_code, 400)
        self.assertEqual(wrong_extension.json()["error"]["code"], "INVALID_FILE")
        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(malformed.json()["error"]["code"], "INVALID_PDF")

    def test_image_only_pdf_returns_no_extractable_text(self):
        document = pymupdf.open()
        page = document.new_page()
        image = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 16, 16), 0)
        image.clear_with(255)
        page.insert_image(page.rect, pixmap=image)
        contents = document.tobytes()
        document.close()

        response = self.upload_pdf(contents)

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "NO_EXTRACTABLE_TEXT")
        self.assertIn("Scanned/image-only PDFs", response.json()["error"]["message"])

    def test_document_over_text_limit_is_rejected_without_truncation(self):
        with patch("my_agent.backend.pdf.extractor.MAX_PDF_TEXT_CHARACTERS", 10):
            response = self.upload_pdf(make_pdf(["A substantial research paper with meaningful text."]))

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"]["code"], "DOCUMENT_TOO_LARGE")

    def test_document_over_page_limit_is_rejected(self):
        with patch("my_agent.backend.pdf.extractor.MAX_PDF_PAGES", 1):
            response = self.upload_pdf(make_pdf(["First page research text.", "Second page research text."]))

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"]["code"], "DOCUMENT_TOO_LARGE")

    def test_upload_over_byte_limit_is_rejected(self):
        with (
            patch("my_agent.backend.main.MAX_PDF_UPLOAD_BYTES", 10),
            patch("my_agent.backend.pdf.extractor.MAX_PDF_UPLOAD_BYTES", 10),
        ):
            response = self.upload_pdf(b"%PDF-1.7\n" + b"x" * 20)

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"]["code"], "FILE_TOO_LARGE")

    def test_unexpected_extraction_failure_returns_safe_error(self):
        with patch(
            "my_agent.backend.main.extract_pdf",
            side_effect=RuntimeError("sensitive internal detail"),
        ):
            response = self.upload_pdf(make_pdf(["A substantial research paper with meaningful text."]))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "PDF_PROCESSING_FAILED")
        self.assertNotIn("sensitive internal detail", response.text)

    def test_research_failure_is_returned_without_internal_details(self):
        agent = AsyncMock(side_effect=RuntimeError("internal provider detail"))
        with patch.object(main, "ask_agent", agent):
            response = self.upload_pdf(make_pdf(["A substantial research paper with meaningful text."]))

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error"]["code"], "RESEARCH_PROCESSING_FAILED")
        self.assertNotIn("internal provider detail", response.text)

    def test_temporary_agent_session_is_deleted(self):
        user_id = "pdf-upload-test-session"
        adk_runner._created_sessions.add(user_id)
        delete_session = AsyncMock()
        try:
            with patch.object(adk_runner.session_service, "delete_session", delete_session):
                asyncio.run(adk_runner.discard_agent_session(user_id))
        finally:
            adk_runner._created_sessions.discard(user_id)

        delete_session.assert_awaited_once_with(
            app_name=adk_runner.APP_NAME,
            user_id=user_id,
            session_id=user_id,
        )
        self.assertNotIn(user_id, adk_runner._created_sessions)

    def test_existing_health_chat_and_web_only_startup(self):
        agent = AsyncMock(return_value="Existing chat result")
        with patch.object(main, "ask_agent", agent):
            with patch.dict(os.environ, {"ENABLE_TELEGRAM": "false"}, clear=True):
                with TestClient(main.app) as client:
                    health = client.get("/health")
                    chat = client.post(
                        "/chat",
                        json={"user_id": "existing-user", "message": "existing request"},
                    )

        self.assertEqual(health.json(), {"status": "ok"})
        self.assertEqual(chat.status_code, 200)
        self.assertEqual(chat.json(), {"response": "Existing chat result"})
        self.assertEqual(agent.await_args.args, ("existing-user", "existing request"))


if __name__ == "__main__":
    unittest.main()
