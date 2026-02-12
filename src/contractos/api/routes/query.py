"""Query / Q&A endpoint — ask questions about contracts.

Supports:
- Single-document queries (document_id)
- Multi-document queries (document_ids list)
- Query persistence via reasoning_sessions
- Chat history retrieval
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from contractos.agents.document_agent import DocumentAgent
from contractos.api.deps import AppState, get_state
from contractos.models.query import ChatTurn, Query, QueryScope
from contractos.models.workspace import ReasoningSession, SessionStatus
from contractos.tools.confidence import ConfidenceDisplay, confidence_label
from contractos.tools.provenance_formatter import format_provenance_chain

router = APIRouter(prefix="/query", tags=["query"])

# Default workspace for session persistence (auto-created)
_DEFAULT_WORKSPACE_ID = "w-default"


class QueryRequest(BaseModel):
    """Request body for asking a question about a contract."""

    question: str = Field(min_length=1)
    document_id: str | None = None  # Single document (backward compatible)
    document_ids: list[str] | None = None  # Multi-document support
    session_id: str | None = None  # Optional: pass to include prior Q&A as context


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
    retrieval_method: str | None = None  # "full_scan" or "faiss_semantic"
    session_id: str | None = None  # Persisted session ID
    document_ids: list[str] = Field(default_factory=list)  # Which docs were queried


class ChatHistoryItem(BaseModel):
    """A single item in the chat history."""

    session_id: str
    question: str
    answer: str | None
    answer_type: str | None
    confidence: float | None
    document_ids: list[str]
    status: str
    asked_at: str
    generation_time_ms: int | None


def _ensure_default_workspace(state: AppState) -> None:
    """Create the default workspace if it doesn't exist."""
    ws = state.workspace_store.get_workspace(_DEFAULT_WORKSPACE_ID)
    if ws is None:
        from contractos.models.workspace import Workspace

        now = datetime.now()
        state.workspace_store.create_workspace(Workspace(
            workspace_id=_DEFAULT_WORKSPACE_ID,
            name="Default Workspace",
            indexed_documents=[],
            created_at=now,
            last_accessed_at=now,
        ))


def _build_chat_history(
    state: AppState, session_id: str, current_doc_ids: list[str],
) -> list[ChatTurn]:
    """Build chat history from prior completed sessions for the same document(s).

    Retrieves all completed sessions from the default workspace that target
    the same document(s), ordered chronologically, and returns them as
    ChatTurn objects for the DocumentAgent.

    The session identified by session_id is used to find the originating
    workspace and document scope. Only sessions that were completed (have
    both question and answer) and target overlapping documents are included.
    """
    # Look up the referenced session to find its document scope
    ref_session = state.workspace_store.get_session(session_id)
    if ref_session is None:
        return []

    # Get all sessions for the workspace, ordered by started_at DESC
    all_sessions = state.workspace_store.get_sessions_by_workspace(
        ref_session.workspace_id
    )

    # Filter: completed sessions targeting overlapping documents, chronological order
    doc_set = set(current_doc_ids)
    turns: list[ChatTurn] = []
    for s in reversed(all_sessions):  # reversed = oldest first (chronological)
        if s.status != SessionStatus.COMPLETED:
            continue
        if not s.answer:
            continue
        # Only include sessions that target at least one of the same documents
        if not doc_set.intersection(s.target_document_ids):
            continue
        turns.append(ChatTurn(question=s.query_text, answer=s.answer))

    return turns


@router.post("/ask", response_model=QueryResponse)
async def ask_question(
    request: QueryRequest,
    state: Annotated[AppState, Depends(get_state)],
) -> QueryResponse:
    """Ask a question about one or more contracts.

    Supports:
    - Single document: pass `document_id`
    - Multiple documents: pass `document_ids` list
    - Queries are persisted as reasoning sessions for chat history

    Returns an answer with:
    - Confidence label (speculative/low/moderate/high/very_high)
    - Full provenance chain with navigable document locations
    - Facts referenced in the answer
    - Generation time
    - Session ID for history tracking
    """
    # Resolve document IDs (support both single and multi)
    doc_ids: list[str] = []
    if request.document_ids:
        doc_ids = request.document_ids
    elif request.document_id:
        doc_ids = [request.document_id]
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide document_id or document_ids",
        )

    # Validate all documents exist
    for did in doc_ids:
        contract = state.trust_graph.get_contract(did)
        if contract is None:
            raise HTTPException(
                status_code=404,
                detail=f"Contract {did} not found",
            )

    # Determine scope
    scope = QueryScope.SINGLE_DOCUMENT if len(doc_ids) == 1 else QueryScope.REPOSITORY

    # Build query model
    query_id = f"q-{uuid.uuid4().hex[:8]}"
    query = Query(
        query_id=query_id,
        text=request.question,
        scope=scope,
        target_document_ids=doc_ids,
        submitted_at=datetime.now(),
    )

    # Persist session (start)
    _ensure_default_workspace(state)
    session_id = f"s-{uuid.uuid4().hex[:8]}"
    session = ReasoningSession(
        session_id=session_id,
        workspace_id=_DEFAULT_WORKSPACE_ID,
        query_text=request.question,
        query_scope=scope.value,
        target_document_ids=doc_ids,
        status=SessionStatus.ACTIVE,
        started_at=datetime.now(),
    )
    state.workspace_store.create_session(session)

    # Build chat history from prior sessions (if session_id provided)
    chat_history: list[ChatTurn] = []
    if request.session_id:
        chat_history = _build_chat_history(state, request.session_id, doc_ids)

    # Run through DocumentAgent (with FAISS semantic retrieval)
    agent = DocumentAgent(state.trust_graph, state.llm, state.embedding_index)
    result = await agent.answer(query, chat_history=chat_history)

    # Persist session (complete)
    try:
        state.workspace_store.complete_session(
            session_id=session_id,
            answer=result.answer,
            answer_type=result.answer_type,
            confidence=result.confidence,
            generation_time_ms=result.generation_time_ms,
        )
    except Exception:
        pass  # Don't fail the response if session persistence fails

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
        retrieval_method=result.retrieval_method,
        session_id=session_id,
        document_ids=doc_ids,
    )


@router.get("/history", response_model=list[ChatHistoryItem])
async def get_chat_history(
    state: Annotated[AppState, Depends(get_state)],
    limit: int = 50,
) -> list[ChatHistoryItem]:
    """Get chat/query history (most recent first).

    Returns all persisted Q&A sessions from the default workspace.
    """
    _ensure_default_workspace(state)
    sessions = state.workspace_store.get_sessions_by_workspace(_DEFAULT_WORKSPACE_ID)
    return [
        ChatHistoryItem(
            session_id=s.session_id,
            question=s.query_text,
            answer=s.answer,
            answer_type=s.answer_type,
            confidence=s.confidence,
            document_ids=s.target_document_ids,
            status=s.status.value,
            asked_at=s.started_at.isoformat(),
            generation_time_ms=s.generation_time_ms,
        )
        for s in sessions[:limit]
    ]


class ClearResponse(BaseModel):
    """Response for clear operations."""

    cleared: int
    message: str


@router.delete("/history", response_model=ClearResponse)
async def clear_chat_history(
    state: Annotated[AppState, Depends(get_state)],
) -> ClearResponse:
    """Clear all chat/query history."""
    _ensure_default_workspace(state)
    count = state.workspace_store.clear_sessions_by_workspace(_DEFAULT_WORKSPACE_ID)
    return ClearResponse(cleared=count, message=f"Cleared {count} chat sessions")
