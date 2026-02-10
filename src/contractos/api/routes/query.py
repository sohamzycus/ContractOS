"""Query / Q&A endpoint — ask questions about contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from contractos.agents.document_agent import DocumentAgent
from contractos.api.deps import AppState, get_state
from contractos.models.query import Query, QueryScope

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    """Request body for asking a question about a contract."""

    question: str = Field(min_length=1)
    document_id: str = Field(min_length=1)


class QueryResponse(BaseModel):
    """Response to a contract question."""

    answer: str
    answer_type: str | None = None
    confidence: float | None = None
    facts_referenced: list[str] = Field(default_factory=list)
    reasoning_chain: str | None = None
    generation_time_ms: int | None = None


@router.post("/ask", response_model=QueryResponse)
async def ask_question(
    request: QueryRequest,
    state: Annotated[AppState, Depends(get_state)],
) -> QueryResponse:
    """Ask a question about a specific contract."""
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

    return QueryResponse(
        answer=result.answer,
        answer_type=result.answer_type,
        confidence=result.confidence,
        facts_referenced=result.facts_referenced,
        reasoning_chain=result.provenance.reasoning_summary if result.provenance else None,
        generation_time_ms=result.generation_time_ms,
    )
