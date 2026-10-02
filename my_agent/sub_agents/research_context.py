from typing import Literal

from pydantic import BaseModel, Field


class TargetPaper(BaseModel):
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    url: str | None = None
    abstract: str | None = None
    key_contributions: list[str] = Field(default_factory=list)
    methodology: str | None = None
    findings: str | None = None
    limitations: list[str] = Field(default_factory=list)


class WebSearchInput(BaseModel):
    document_type: Literal["seminal", "general"]
    target_paper: TargetPaper


class FutureResearchInput(BaseModel):
    document_type: Literal["seminal", "general"]
    target_paper: TargetPaper
    recent_research: str
    paper_analysis: str | None = None
