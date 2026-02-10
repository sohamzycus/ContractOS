"""Query / Q&A endpoint — ask questions about contracts."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from contractos.api.deps import AppState, get_state

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    """Request body for asking a question about a contract."""

    question: str = Field(min_length=1)
    document_id: str = Field(min_length=1)


class QueryResponse(BaseModel):
    """Response to a contract question."""

    answer: str
    confidence: float | None = None
    facts_referenced: list[str] = Field(default_factory=list)
    reasoning_chain: str | None = None


@router.post("/ask", response_model=QueryResponse)
async def ask_question(
    request: QueryRequest,
    state: Annotated[AppState, Depends(get_state)],
) -> QueryResponse:
    """Ask a question about a specific contract.

    Phase 2 stub — returns a placeholder. Full implementation in Phase 5.
    """
    contract = state.trust_graph.get_contract(request.document_id)
    if contract is None:
        raise HTTPException(
            status_code=404,
            detail=f"Contract {request.document_id} not found",
        )

    # TODO: Phase 5 will implement full Q&A pipeline
    return QueryResponse(
        answer="Q&A pipeline not yet implemented. Contract found.",
        confidence=None,
        facts_referenced=[],
        reasoning_chain=None,
    )
