import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from my_agent.backend import main
from my_agent.backend.adk_runner import run_specialized_agent
from my_agent.backend.pdf.document_classifier import (
    DocumentClassification,
    classify_document,
)
from my_agent.backend.pdf.extractor import ExtractedDocument, ExtractedPage
from my_agent.backend.research import router
from my_agent.sub_agents.academic_generalresearch.agent import (
    academic_generalresearch_agent,
)


def classification_output(**overrides):
    value = {
        "document_type": "seminal",
        "confidence": 0.91,
        "title": "A Foundational Research Paper",
        "authors": ["A. Researcher"],
        "publication_year": 2018,
    }
    value.update(overrides)
    return json.dumps(value)


def sample_document():
    return ExtractedDocument(
        filename="paper.pdf",
        page_count=2,
        pages=(
            ExtractedPage(1, "A substantial research paper with meaningful text."),
            ExtractedPage(2, "Page two contains additional research findings."),
        ),
    )


class DocumentClassifierTests(unittest.IsolatedAsyncioTestCase):
    async def classify_with_output(self, output):
        with (
            patch(
                "my_agent.backend.pdf.document_classifier.run_specialized_agent",
                new=AsyncMock(return_value=output),
            ) as run_agent,
            patch(
                "my_agent.backend.pdf.document_classifier.discard_agent_session",
                new=AsyncMock(),
            ) as discard_session,
        ):
            result = await classify_document("Research paper text with enough characters.")
        return result, run_agent, discard_session

    async def test_classifies_seminal_document_and_metadata(self):
        result, run_agent, discard_session = await self.classify_with_output(
            classification_output()
        )

        self.assertEqual(result.document_type, "seminal")
        self.assertEqual(result.confidence, 0.91)
        self.assertEqual(result.title, "A Foundational Research Paper")
        self.assertEqual(result.authors, ["A. Researcher"])
        self.assertEqual(result.publication_year, 2018)
        self.assertFalse(result.classification_uncertain)
        self.assertIn("Document text", run_agent.await_args.args[1])
        self.assertIn("Research paper text", run_agent.await_args.args[1])
        discard_session.assert_awaited_once()

    async def test_classifies_general_document(self):
        result, _, _ = await self.classify_with_output(
            classification_output(document_type="general", confidence=0.88)
        )

        self.assertEqual(result.document_type, "general")
        self.assertEqual(result.confidence, 0.88)
        self.assertFalse(result.classification_uncertain)

    async def test_low_confidence_seminal_candidate_uses_uncertain_general_fallback(self):
        result, _, _ = await self.classify_with_output(
            classification_output(confidence=0.55)
        )

        self.assertEqual(result.document_type, "general")
        self.assertEqual(result.confidence, 0.55)
        self.assertTrue(result.classification_uncertain)
        self.assertEqual(result.classification_status, "classified")

    async def test_low_confidence_general_classification_is_marked_uncertain(self):
        result, _, _ = await self.classify_with_output(
            classification_output(document_type="general", confidence=0.55)
        )

        self.assertEqual(result.document_type, "general")
        self.assertEqual(result.confidence, 0.55)
        self.assertTrue(result.classification_uncertain)

    async def test_missing_title_authors_and_year_are_allowed(self):
        result, _, _ = await self.classify_with_output(
            json.dumps({"document_type": "general", "confidence": 0.82})
        )

        self.assertIsNone(result.title)
        self.assertEqual(result.authors, [])
        self.assertIsNone(result.publication_year)

    async def test_malformed_and_invalid_classifier_outputs_fall_back_safely(self):
        for output in ("not JSON", '{"document_type":"unknown","confidence":0.9}'):
            with self.subTest(output=output):
                result, _, _ = await self.classify_with_output(output)
                self.assertEqual(result.document_type, "general")
                self.assertEqual(result.confidence, 0.0)
                self.assertTrue(result.classification_uncertain)
                self.assertEqual(result.classification_status, "fallback")

    async def test_invalid_confidence_and_missing_required_fields_fall_back(self):
        for output in (
            classification_output(confidence=1.2),
            '{"document_type":"general"}',
        ):
            with self.subTest(output=output):
                result, _, _ = await self.classify_with_output(output)
                self.assertEqual(result.document_type, "general")
                self.assertEqual(result.confidence, 0.0)
                self.assertEqual(result.classification_status, "fallback")

    async def test_insufficient_text_uses_fallback_without_model_call(self):
        with patch(
            "my_agent.backend.pdf.document_classifier.run_specialized_agent",
            new=AsyncMock(),
        ) as run_agent:
            result = await classify_document("short")

        self.assertEqual(result.document_type, "general")
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.classification_status, "fallback")
        run_agent.assert_not_awaited()

    async def test_model_failure_and_timeout_use_fallback(self):
        for failure in (
            RuntimeError("model unavailable"),
            TimeoutError("model timed out"),
        ):
            with self.subTest(failure=type(failure).__name__):
                with (
                    patch(
                        "my_agent.backend.pdf.document_classifier.run_specialized_agent",
                        new=AsyncMock(side_effect=failure),
                    ),
                    patch(
                        "my_agent.backend.pdf.document_classifier.discard_agent_session",
                        new=AsyncMock(),
                    ),
                ):
                    result = await classify_document(
                        "Research paper text with enough characters."
                    )
                self.assertEqual(result.classification_status, "fallback")
                self.assertEqual(result.confidence, 0.0)

    async def test_classification_only_sends_bounded_excerpt(self):
        text = "A" * 25_000
        with (
            patch(
                "my_agent.backend.pdf.document_classifier.run_specialized_agent",
                new=AsyncMock(return_value=classification_output()),
            ) as run_agent,
            patch(
                "my_agent.backend.pdf.document_classifier.discard_agent_session",
                new=AsyncMock(),
            ),
        ):
            await classify_document(text)

        self.assertLess(len(run_agent.await_args.args[1]), 22_000)
        self.assertIn("[Middle of document omitted for classification.]", run_agent.await_args.args[1])


class WorkflowRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_seminal_document_uses_existing_coordinator(self):
        classification = DocumentClassification(
            document_type="seminal",
            confidence=0.91,
            title="Foundational Paper",
        )
        with (
            patch.object(router, "classify_document", new=AsyncMock(return_value=classification)),
            patch.object(router, "ask_agent", new=AsyncMock(return_value="Seminal analysis")) as ask_agent,
            patch.object(router, "run_specialized_agent", new=AsyncMock()) as general_agent,
            patch.object(router, "discard_agent_session", new=AsyncMock()) as cleanup,
        ):
            result = await router.process_document(sample_document())

        self.assertEqual(result.workflow, "seminal")
        self.assertEqual(result.document.document_type, "seminal")
        self.assertEqual(result.response, "Seminal analysis")
        self.assertIn("classified as a seminal/foundational paper", ask_agent.await_args.args[1])
        self.assertIn("[Page 1]", ask_agent.await_args.args[1])
        general_agent.assert_not_awaited()
        cleanup.assert_awaited_once()

    async def test_general_document_uses_general_analysis_agent(self):
        classification = DocumentClassification(
            document_type="general",
            confidence=0.86,
            title="Recent Paper",
        )
        with (
            patch.object(router, "classify_document", new=AsyncMock(return_value=classification)),
            patch.object(router, "ask_agent", new=AsyncMock()) as seminal_agent,
            patch.object(
                router,
                "run_specialized_agent",
                new=AsyncMock(return_value="Paper analysis"),
            ) as general_agent,
            patch.object(router, "discard_agent_session", new=AsyncMock()) as cleanup,
        ):
            result = await router.process_document(sample_document())

        self.assertEqual(result.workflow, "general")
        self.assertEqual(result.response, "Paper analysis")
        self.assertIs(general_agent.await_args.args[2], academic_generalresearch_agent)
        self.assertIn("general research paper", general_agent.await_args.args[1])
        self.assertIn("Do not ask for a seminal paper", general_agent.await_args.args[1])
        seminal_agent.assert_not_awaited()
        cleanup.assert_awaited_once()

    async def test_uncertain_seminal_candidate_routes_to_general(self):
        classification = DocumentClassification(
            document_type="seminal",
            confidence=0.51,
        )
        with (
            patch.object(router, "classify_document", new=AsyncMock(return_value=classification)),
            patch.object(router, "ask_agent", new=AsyncMock()) as seminal_agent,
            patch.object(
                router,
                "run_specialized_agent",
                new=AsyncMock(return_value="Fallback analysis"),
            ),
            patch.object(router, "discard_agent_session", new=AsyncMock()),
        ):
            result = await router.process_document(sample_document())

        self.assertEqual(result.workflow, "general")
        self.assertEqual(result.document.document_type, "general")
        self.assertTrue(result.document.classification_uncertain)
        seminal_agent.assert_not_awaited()

    async def test_workflow_failure_propagates_and_session_is_cleared(self):
        classification = DocumentClassification(
            document_type="general",
            confidence=0.85,
        )
        with (
            patch.object(router, "classify_document", new=AsyncMock(return_value=classification)),
            patch.object(
                router,
                "run_specialized_agent",
                new=AsyncMock(side_effect=RuntimeError("model detail")),
            ),
            patch.object(router, "discard_agent_session", new=AsyncMock()) as cleanup,
        ):
            with self.assertRaisesRegex(RuntimeError, "model detail"):
                await router.process_document(sample_document())

        cleanup.assert_awaited_once()


class SharedRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_specialized_agent_uses_shared_runner_session_services(self):
        agent = academic_generalresearch_agent
        with (
            patch(
                "my_agent.backend.adk_runner._ensure_session",
                new=AsyncMock(),
            ) as ensure_session,
            patch(
                "my_agent.backend.adk_runner._run_once",
                new=AsyncMock(return_value="specialized result"),
            ) as run_once,
        ):
            result = await run_specialized_agent("short-lived-user", "message", agent)

        self.assertEqual(result, "specialized result")
        ensure_session.assert_awaited_once_with("short-lived-user", "short-lived-user")
        self.assertIs(run_once.await_args.kwargs["agent"], agent)


class ApplicationIntegrationTests(unittest.TestCase):
    def test_general_pdf_response_includes_backward_compatible_fields(self):
        workflow_result = router.ResearchWorkflowResult(
            document=DocumentClassification(
                document_type="general",
                confidence=0.84,
                title="General Paper",
                authors=["B. Researcher"],
                publication_year=2024,
            ),
            workflow="general",
            response="Structured paper analysis",
        )
        with (
            patch.dict(os.environ, {"ENABLE_TELEGRAM": "false"}, clear=True),
            patch.object(main, "process_document", new=AsyncMock(return_value=workflow_result)),
            patch.object(main, "extract_pdf", return_value=sample_document()),
        ):
            with TestClient(main.app) as client:
                response = client.post(
                    "/api/analyze-pdf",
                    files={"file": ("paper.pdf", b"%PDF-1.7 test")},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["page_count"], 2)
        self.assertEqual(payload["workflow"], "general")
        self.assertEqual(payload["document"]["type"], "general")
        self.assertEqual(payload["document"]["confidence"], 0.84)
        self.assertEqual(payload["result"]["response"], "Structured paper analysis")

    def test_classifier_failure_is_reported_and_routes_to_general_workflow(self):
        fallback = DocumentClassification(
            document_type="general",
            confidence=0.0,
            classification_uncertain=True,
            classification_status="fallback",
        )
        with (
            patch.dict(os.environ, {"ENABLE_TELEGRAM": "false"}, clear=True),
            patch.object(main, "extract_pdf", return_value=sample_document()),
            patch.object(router, "classify_document", new=AsyncMock(return_value=fallback)),
            patch.object(
                router,
                "run_specialized_agent",
                new=AsyncMock(return_value="Cautious fallback analysis"),
            ) as general_agent,
            patch.object(router, "discard_agent_session", new=AsyncMock()),
        ):
            with TestClient(main.app) as client:
                response = client.post(
                    "/api/analyze-pdf",
                    files={"file": ("paper.pdf", b"%PDF-1.7 test")},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["workflow"], "general")
        self.assertEqual(payload["document"]["confidence"], 0.0)
        self.assertEqual(payload["document"]["classification_status"], "fallback")
        self.assertTrue(payload["document"]["classification_uncertain"])
        self.assertEqual(payload["result"]["response"], "Cautious fallback analysis")
        self.assertIn("general research paper", general_agent.await_args.args[1])

    def test_web_and_telegram_imports_remain_available(self):
        from my_agent.backend import telegram

        self.assertIsNotNone(telegram.chat)
        with patch.dict(os.environ, {"ENABLE_TELEGRAM": "false"}, clear=True):
            with TestClient(main.app) as client:
                self.assertEqual(client.get("/").status_code, 200)
                self.assertEqual(client.get("/health").json(), {"status": "ok"})

    def test_telegram_enabled_startup_keeps_application_lifecycle(self):
        class TelegramApplicationStub:
            initialize = AsyncMock()
            start = AsyncMock()
            stop = AsyncMock()
            shutdown = AsyncMock()

        telegram_app = TelegramApplicationStub()
        with (
            patch.dict(os.environ, {"ENABLE_TELEGRAM": "true"}, clear=True),
            patch.object(main, "is_telegram_enabled", return_value=True),
            patch.object(main, "get_telegram_application", return_value=telegram_app),
            patch.object(main, "TELEGRAM_WEBHOOK_URL", None),
            TestClient(main.app) as client,
        ):
            response = client.get("/")

        self.assertEqual(response.status_code, 200)
        telegram_app.initialize.assert_awaited_once()
        telegram_app.start.assert_awaited_once()
        telegram_app.stop.assert_awaited_once()
        telegram_app.shutdown.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
