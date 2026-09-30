import asyncio
import os
import unittest
from io import BytesIO
from unittest.mock import AsyncMock, patch

from pypdf import PdfWriter
from fastapi.testclient import TestClient

from my_agent.backend import adk_runner
from my_agent.backend import main
from my_agent.backend.pdf.extractor import extract_pdf


def make_pdf(page_texts: list[str], image_only_pages: set[int] | None = None) -> bytes:
    image_only_pages = image_only_pages or set()
    page_count = len(page_texts)
    font_object_id = 3 + page_count * 2
    image_object_id = font_object_id + 1
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            f"<< /Type /Pages /Kids [{' '.join(f'{3 + index * 2} 0 R' for index in range(page_count))}] "
            f"/Count {page_count} >>"
        ).encode(),
    ]
    page_objects = []
    content_objects = []

    for index, text in enumerate(page_texts):
        page_object_id = 3 + index * 2
        content_object_id = page_object_id + 1
        resources = f"/Font << /F1 {font_object_id} 0 R >>"
        if index in image_only_pages:
            resources += f" /XObject << /Im0 {image_object_id} 0 R >>"
        page_objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << {resources} >> /Contents {content_object_id} 0 R >>"
            ).encode()
        )
        if index in image_only_pages:
            content = b"q 16 0 0 16 72 72 cm /Im0 Do Q"
        elif text:
            escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            content = (
                f"BT /F1 12 Tf 72 720 Td ({escaped_text}) Tj ET".encode("ascii")
            )
        else:
            content = b""
        content_objects.append(
            f"<< /Length {len(content)} >>\nstream\n".encode()
            + content
            + b"\nendstream"
        )

    objects.extend(
        item
        for pair in zip(page_objects, content_objects)
        for item in pair
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    if image_only_pages:
        image_data = b"FF0000>"
        objects.append(
            (
                f"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 "
                f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /ASCIIHexDecode "
                f"/Length {len(image_data)} >>\nstream\n"
            ).encode()
            + image_data
            + b"\nendstream"
        )

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_id, content in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{object_id} 0 obj\n".encode() + content + b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode()
    )
    return bytes(output)


def make_encrypted_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("password")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


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
        extracted = extract_pdf(
            make_pdf(["First page research text.", "", "Third page research text."]),
            "paper.pdf",
        )

        self.assertEqual(extracted.page_count, 3)
        self.assertEqual([page.page_number for page in extracted.pages], [1, 2, 3])
        self.assertEqual(extracted.pages[1].text, "")
        self.assertIn("[Page 1]\nFirst page research text.", extracted.research_text())
        self.assertIn("[Page 2]", extracted.research_text())
        self.assertIn("[Page 3]\nThird page research text.", extracted.research_text())

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

    def test_encrypted_pdf_is_rejected(self):
        response = self.upload_pdf(make_encrypted_pdf())

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_PDF")
        self.assertIn("Password-protected PDFs", response.json()["error"]["message"])

    def test_empty_pdf_returns_no_extractable_text(self):
        response = self.upload_pdf(make_pdf([""]))

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "NO_EXTRACTABLE_TEXT")

    def test_image_only_pdf_returns_no_extractable_text(self):
        response = self.upload_pdf(make_pdf([""], image_only_pages={0}))

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "NO_EXTRACTABLE_TEXT")
        self.assertIn("Scanned/image-only PDFs", response.json()["error"]["message"])

    def test_document_under_minimum_text_requirement_is_rejected(self):
        response = self.upload_pdf(make_pdf(["Only 19 chars here"]))

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "NO_EXTRACTABLE_TEXT")

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
