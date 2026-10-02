import json
import logging
import uuid
from dataclasses import dataclass
from typing import Literal

from my_agent.backend.adk_runner import (
    ask_agent,
    discard_agent_session,
    run_specialized_agent,
)
from my_agent.backend.pdf.document_classifier import (
    SEMINAL_CONFIDENCE_THRESHOLD,
    DocumentClassification,
    classify_document,
)
from my_agent.backend.pdf.extractor import ExtractedDocument
from my_agent.sub_agents.academic_generalresearch.agent import (
    academic_generalresearch_agent,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResearchWorkflowResult:
    document: DocumentClassification
    workflow: Literal["seminal", "general"]
    response: str


def _workflow_message(document: ExtractedDocument, classification: DocumentClassification) -> str:
    paper_text = document.research_text()
    target_paper = {
        "title": classification.title,
        "authors": classification.authors,
        "year": classification.publication_year,
        "doi": None,
        "url": None,
    }
    paper_context = (
        f"Document type: {classification.document_type}\n"
        "Known target_paper metadata (null means not identified by the classifier):\n"
        f"{json.dumps(target_paper, ensure_ascii=False)}\n"
    )
    if classification.document_type == "seminal":
        return (
            "The uploaded document has been classified as a seminal/foundational "
            f"paper with {classification.confidence:.0%} confidence.\n"
            f"{paper_context}\nAnalyze it "
            "using the existing seminal-paper ResearchFlow workflow: establish "
            "paper context, find recent citing papers, and synthesize future "
            "research directions. Do not ask the user to provide the paper again. "
            "Page labels identify original PDF page boundaries.\n\n"
            f"{paper_text}"
        )
    return (
        "The uploaded document is being analyzed as a general research paper. "
        f"{paper_context}\n"
        "Analyze the supplied paper using the general paper-analysis workflow. "
        "Do not ask for a seminal paper or assume this paper is foundational. "
        "Explicitly distinguish document-supported information from suggestions "
        "and identify unavailable information as not identified in the provided "
        "document. Page labels identify original PDF page boundaries.\n\n"
        f"{paper_text}"
    )


async def process_document(document: ExtractedDocument) -> ResearchWorkflowResult:
    """Understand a PDF and route it to its specialized research workflow."""
    document_text = document.research_text()
    classification = await classify_document(document_text)
    use_seminal_workflow = (
        classification.document_type == "seminal"
        and not classification.classification_uncertain
        and classification.classification_status == "classified"
        and classification.confidence >= SEMINAL_CONFIDENCE_THRESHOLD
    )

    if use_seminal_workflow:
        workflow: Literal["seminal", "general"] = "seminal"
        classification = classification.model_copy(
            update={"document_type": "seminal", "classification_uncertain": False}
        )
    else:
        workflow = "general"
        if (
            classification.document_type == "seminal"
            or classification.classification_uncertain
            or classification.classification_status == "fallback"
        ):
            classification = classification.model_copy(
                update={"document_type": "general", "classification_uncertain": True}
            )

    user_id = f"pdf-{workflow}-{uuid.uuid4().hex}"
    message = _workflow_message(document, classification)
    target_paper_present = bool(document_text.strip())
    logger.info(
        "Research workflow state: document_text_present=%s, document_type=%s, "
        "target_paper_present=%s, recent_research_present=%s, "
        "recent_research_type=%s",
        bool(document_text.strip()),
        workflow,
        target_paper_present,
        False,
        "pending",
    )
    try:
        if workflow == "seminal":
            response = await ask_agent(user_id, message)
        else:
            response = await run_specialized_agent(
                user_id,
                message,
                academic_generalresearch_agent,
            )
    except Exception:
        logger.exception("PDF research workflow failed (%s)", workflow)
        raise
    finally:
        try:
            await discard_agent_session(user_id)
        except Exception:
            logger.exception("Failed to clear PDF research session (%s)", workflow)
            raise

    return ResearchWorkflowResult(
        document=classification,
        workflow=workflow,
        response=response,
    )
