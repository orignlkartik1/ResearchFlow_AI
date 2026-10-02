import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from google.adk.events import Event
from google.adk.utils.instructions_utils import inject_session_state
from google.genai import types

from my_agent.backend import adk_runner
from my_agent.backend import main
from my_agent.backend.adk_runner import run_specialized_agent
from my_agent.backend.pdf.document_classifier import (
    DOCUMENT_CLASSIFIER_INSTRUCTION,
    DocumentClassification,
    classify_document,
)
from my_agent.backend.pdf.extractor import ExtractedDocument, ExtractedPage
from my_agent.backend.research import router
from my_agent.sub_agents.academic_generalresearch.agent import (
    academic_generalresearch_agent,
)
from my_agent.sub_agents.academic_generalresearch.prompt import (
    ACADEMIC_GENERALRESEARCH_PROMPT,
)
from my_agent.sub_agents.academic_newresearch.agent import (
    academic_newresearch_agent,
)
from my_agent.sub_agents.academic_webresearch.agent import (
    academic_websearch_agent,
)
from my_agent.sub_agents.research_context import (
    FutureResearchInput,
    TargetPaper,
    WebSearchInput,
)
from my_agent.agent import root_agent
from my_agent.prompt import ACADEMIC_COORDINATOR_PROMPT


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


class StubRunner:
    def __init__(self, events):
        self.events = events

    async def run_async(self, **kwargs):
        for event in self.events:
            yield event


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
        self.assertIn("Document type: seminal", ask_agent.await_args.args[1])
        self.assertIn('"title": "Foundational Paper"', ask_agent.await_args.args[1])
        self.assertIn("target_paper", ask_agent.await_args.args[1])
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
        self.assertIn("Document type: general", general_agent.await_args.args[1])
        self.assertIn('"title": "Recent Paper"', general_agent.await_args.args[1])
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
    async def run_events(self, events):
        with patch.object(
            adk_runner,
            "_create_runner",
            return_value=StubRunner(events),
        ):
            return await adk_runner._run_once(
                user_id="runner-test",
                session_id="runner-test",
                message="test message",
                llm_model=None,
            )

    async def test_extracts_normal_text_response(self):
        result = await self.run_events(
            [Event(content=types.Content(parts=[types.Part(text="Agent response")]))]
        )

        self.assertEqual(result, "Agent response")

    async def test_event_without_content_does_not_raise(self):
        result = await self.run_events([Event()])

        self.assertEqual(result, "")

    async def test_content_without_parts_does_not_raise(self):
        result = await self.run_events([Event(content=types.Content())])

        self.assertEqual(result, "")

    async def test_extracts_all_text_parts_in_order(self):
        result = await self.run_events(
            [
                Event(
                    content=types.Content(
                        parts=[
                            types.Part(text="First "),
                            types.Part(),
                            types.Part(text="second"),
                        ]
                    )
                )
            ]
        )

        self.assertEqual(result, "First second")

    async def test_tool_call_event_does_not_hide_final_text(self):
        tool_event = Event(
            content=types.Content(
                parts=[types.Part(function_call=types.FunctionCall(name="search"))]
            )
        )
        final_event = Event(
            content=types.Content(parts=[types.Part(text="Research completed")])
        )

        result = await self.run_events([tool_event, final_event])

        self.assertFalse(tool_event.is_final_response())
        self.assertEqual(result, "Research completed")

    async def test_later_empty_final_event_does_not_erase_agent_text(self):
        text_event = Event(content=types.Content(parts=[types.Part(text="Useful result")]))

        result = await self.run_events([text_event, Event()])

        self.assertEqual(result, "Useful result")

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


class AgentContextContractTests(unittest.IsolatedAsyncioTestCase):
    def test_agents_use_explicit_paper_data_and_no_template_references(self):
        self.assertIsNone(root_agent.output_key)
        self.assertIs(academic_websearch_agent.input_schema, WebSearchInput)
        self.assertIs(academic_newresearch_agent.input_schema, FutureResearchInput)

        for instruction in (
            ACADEMIC_COORDINATOR_PROMPT,
            academic_websearch_agent.instruction,
            academic_newresearch_agent.instruction,
            ACADEMIC_GENERALRESEARCH_PROMPT,
        ):
            self.assertNotIn("{", instruction)
            self.assertNotIn("}", instruction)

    async def test_adk_instruction_injection_requires_no_implicit_state(self):
        context = SimpleNamespace(
            _invocation_context=SimpleNamespace(
                session=SimpleNamespace(state={}),
            )
        )
        for instruction in (
            ACADEMIC_COORDINATOR_PROMPT,
            academic_websearch_agent.instruction,
            academic_newresearch_agent.instruction,
            ACADEMIC_GENERALRESEARCH_PROMPT,
            DOCUMENT_CLASSIFIER_INSTRUCTION,
        ):
            with self.subTest(instruction=instruction[:30]):
                self.assertEqual(
                    await inject_session_state(instruction, context),
                    instruction,
                )

    async def test_target_paper_metadata_is_optional_in_downstream_inputs(self):
        target = TargetPaper(title="Example paper", authors=["A. Author"], year=2024)
        search_input = WebSearchInput(
            document_type="general",
            target_paper=target,
        )
        future_input = FutureResearchInput(
            document_type="general",
            target_paper=target,
            recent_research="No useful results found.",
        )

        self.assertIsNone(search_input.target_paper.doi)
        self.assertIsNone(future_input.target_paper.url)
        self.assertEqual(future_input.recent_research, "No useful results found.")

    async def test_general_paper_agent_has_both_research_tools(self):
        tool_agents = {tool.agent.name for tool in academic_generalresearch_agent.tools}

        self.assertEqual(
            tool_agents,
            {"academic_websearch_agent", "academic_newresearch_agent"},
        )


class ApplicationIntegrationTests(unittest.TestCase):
    def test_pdf_endpoint_returns_final_adk_text_without_502(self):
        classification = DocumentClassification(
            document_type="general",
            confidence=0.86,
            title="Recent Paper",
        )
        runner = StubRunner(
            [
                Event(
                    content=types.Content(
                        parts=[types.Part(text="Analyzed "), types.Part(text="paper.")]
                    )
                )
            ]
        )
        with (
            patch.dict(os.environ, {"ENABLE_TELEGRAM": "false"}, clear=True),
            patch.object(main, "extract_pdf", return_value=sample_document()),
            patch.object(
                router,
                "classify_document",
                new=AsyncMock(return_value=classification),
            ),
            patch.object(adk_runner, "_ensure_session", new=AsyncMock()),
            patch.object(adk_runner, "_create_runner", return_value=runner),
            patch.object(router, "discard_agent_session", new=AsyncMock()),
            TestClient(main.app) as client,
        ):
            response = client.post(
                "/api/analyze-pdf",
                files={"file": ("paper.pdf", b"%PDF-1.7 test")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["workflow"], "general")
        self.assertEqual(response.json()["result"]["response"], "Analyzed paper.")

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
