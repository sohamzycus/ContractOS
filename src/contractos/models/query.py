"""Query and QueryResult models — the Q&A lifecycle."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from contractos.models.provenance import ProvenanceChain


class QueryScope(StrEnum):
    """Scope of a query — how many documents to search."""

    SINGLE_DOCUMENT = "single_document"
    DOCUMENT_FAMILY = "document_family"
    REPOSITORY = "repository"


class Query(BaseModel):
    """A user's natural language question."""

    query_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    scope: QueryScope = QueryScope.SINGLE_DOCUMENT
    target_document_ids: list[str] = Field(min_length=1)
    submitted_at: datetime


class QueryResult(BaseModel):
    """The answer to a query with full provenance."""

    result_id: str = Field(min_length=1)
    query_id: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    answer_type: Literal["fact", "binding", "inference", "not_found"]
    confidence: float | None = None
    provenance: ProvenanceChain
    facts_referenced: list[str] = Field(default_factory=list)
    bindings_used: list[str] = Field(default_factory=list)
    inferences_generated: list[str] = Field(default_factory=list)
    generated_at: datetime
    generation_time_ms: int = Field(ge=0)
