"""Query / Q&A endpoint — ask questions about contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from contractos.agents.document_agent import DocumentAgent
from contractos.api.deps import AppState, get_state
from contractos.models.query import Query, QueryScope
from contractos.tools.confidence import ConfidenceDisplay, confidence_label
from contractos.tools.provenance_formatter import format_provenance_chain

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    """Request body for asking a question about a contract."""

    question: str = Field(min_length=1)
    document_id: str = Field(min_length=1)


class ProvenanceNodeResponse(BaseModel):
    """A single provenance node in the response."""

    node_type: str
    reference_id: str
    summary: str
    document_location: str | None = None
    display_label: str
    icon: str


class ProvenanceResponse(BaseModel):
    """Full provenance chain in the response."""

    nodes: list[ProvenanceNodeResponse]
    reasoning_summary: str
    node_count: int
    has_facts: bool
    has_inferences: bool


class QueryResponse(BaseModel):
    """Response to a contract question with full provenance."""

    answer: str
    answer_type: str | None = None
    confidence: ConfidenceDisplay | None = None
    facts_referenced: list[str] = Field(default_factory=list)
    provenance: ProvenanceResponse | None = None
    generation_time_ms: int | None = None


@router.post("/ask", response_model=QueryResponse)
async def ask_question(
    request: QueryRequest,
    state: Annotated[AppState, Depends(get_state)],
) -> QueryResponse:
    """Ask a question about a specific contract.

    Returns an answer with:
    - Confidence label (speculative/low/moderate/high/very_high)
    - Full provenance chain with navigable document locations
    - Facts referenced in the answer
    - Generation time
    """
    contract = state.trust_graph.get_contract(request.document_id)
    if contract is None:
        raise HTTPException(
            status_code=404,
            detail=f"Contract {request.document_id} not found",
        )

    # Build query model
    query = Query(
        query_id=f"q-{request.document_id}-{hash(request.question) % 10000:04d}",
        text=request.question,
        scope=QueryScope.SINGLE_DOCUMENT,
        target_document_ids=[request.document_id],
        submitted_at=datetime.now(),
    )

    # Run through DocumentAgent
    agent = DocumentAgent(state.trust_graph, state.llm)
    result = await agent.answer(query)

    # Format provenance for display
    provenance_data = None
    if result.provenance:
        formatted = format_provenance_chain(result.provenance)
        provenance_data = ProvenanceResponse(
            nodes=[ProvenanceNodeResponse(**n) for n in formatted["nodes"]],
            reasoning_summary=formatted["reasoning_summary"],
            node_count=formatted["node_count"],
            has_facts=formatted["has_facts"],
            has_inferences=formatted["has_inferences"],
        )

    return QueryResponse(
        answer=result.answer,
        answer_type=result.answer_type,
        confidence=confidence_label(result.confidence),
        facts_referenced=result.facts_referenced,
        provenance=provenance_data,
        generation_time_ms=result.generation_time_ms,
    )
