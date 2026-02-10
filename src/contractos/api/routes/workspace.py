"""Workspace API routes — workspace CRUD, document association, session history."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from contractos.api.deps import get_state
from contractos.models.workspace import ReasoningSession, SessionStatus, Workspace
from contractos.tools.change_detection import compute_file_hash, detect_change

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# ── Request/Response Models ──────────────────────────────────────────


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=1)
    settings: dict = Field(default_factory=dict)


class AddDocumentRequest(BaseModel):
    document_id: str = Field(min_length=1)


class SessionSummary(BaseModel):
    session_id: str
    query_text: str
    answer: str | None
    answer_type: str | None
    confidence: float | None
    status: str
    started_at: str
    completed_at: str | None
    generation_time_ms: int | None


class WorkspaceResponse(BaseModel):
    workspace_id: str
    name: str
    indexed_documents: list[str]
    created_at: str
    last_accessed_at: str
    settings: dict
    recent_sessions: list[SessionSummary] = Field(default_factory=list)


class DocumentCheckResponse(BaseModel):
    document_id: str
    file_path: str
    changed: bool
    current_hash: str
    previous_hash: str | None = None
    message: str


# ── Endpoints ────────────────────────────────────────────────────────


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(req: CreateWorkspaceRequest) -> WorkspaceResponse:
    """Create a new workspace."""
    state = get_state()
    ws_id = f"w-{uuid.uuid4().hex[:8]}"
    now = datetime.now()

    workspace = Workspace(
        workspace_id=ws_id,
        name=req.name,
        indexed_documents=[],
        created_at=now,
        last_accessed_at=now,
        settings=req.settings,
    )
    state.workspace_store.create_workspace(workspace)

    return WorkspaceResponse(
        workspace_id=ws_id,
        name=workspace.name,
        indexed_documents=[],
        created_at=now.isoformat(),
        last_accessed_at=now.isoformat(),
        settings=workspace.settings,
        recent_sessions=[],
    )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(workspace_id: str) -> WorkspaceResponse:
    """Get workspace details including recent sessions."""
    state = get_state()
    ws = state.workspace_store.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")

    # Update last accessed
    state.workspace_store.update_last_accessed(workspace_id)

    # Get recent sessions (last 20)
    sessions = state.workspace_store.get_sessions_by_workspace(workspace_id)
    recent = sessions[:20]

    return WorkspaceResponse(
        workspace_id=ws.workspace_id,
        name=ws.name,
        indexed_documents=ws.indexed_documents,
        created_at=ws.created_at.isoformat(),
        last_accessed_at=ws.last_accessed_at.isoformat(),
        settings=ws.settings,
        recent_sessions=[
            SessionSummary(
                session_id=s.session_id,
                query_text=s.query_text,
                answer=s.answer,
                answer_type=s.answer_type,
                confidence=s.confidence,
                status=s.status.value,
                started_at=s.started_at.isoformat(),
                completed_at=s.completed_at.isoformat() if s.completed_at else None,
                generation_time_ms=s.generation_time_ms,
            )
            for s in recent
        ],
    )


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces() -> list[WorkspaceResponse]:
    """List all workspaces."""
    state = get_state()
    workspaces = state.workspace_store.list_workspaces()
    return [
        WorkspaceResponse(
            workspace_id=ws.workspace_id,
            name=ws.name,
            indexed_documents=ws.indexed_documents,
            created_at=ws.created_at.isoformat(),
            last_accessed_at=ws.last_accessed_at.isoformat(),
            settings=ws.settings,
        )
        for ws in workspaces
    ]


@router.post("/{workspace_id}/documents", status_code=204)
async def add_document_to_workspace(
    workspace_id: str, req: AddDocumentRequest
) -> None:
    """Add a document to a workspace."""
    state = get_state()
    ws = state.workspace_store.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")

    # Verify document exists
    contract = state.trust_graph.get_contract(req.document_id)
    if contract is None:
        raise HTTPException(
            status_code=404, detail=f"Document {req.document_id} not found"
        )

    state.workspace_store.add_document_to_workspace(workspace_id, req.document_id)


@router.delete("/{workspace_id}/documents/{document_id}", status_code=204)
async def remove_document_from_workspace(
    workspace_id: str, document_id: str
) -> None:
    """Remove a document from a workspace."""
    state = get_state()
    ws = state.workspace_store.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")

    state.workspace_store.remove_document_from_workspace(workspace_id, document_id)


@router.get(
    "/{workspace_id}/documents/{document_id}/check",
    response_model=DocumentCheckResponse,
)
async def check_document_change(
    workspace_id: str, document_id: str
) -> DocumentCheckResponse:
    """Check if a document has changed since it was last indexed.

    Compares the current file hash against the stored hash. If changed,
    the client should offer to re-parse the document.
    """
    state = get_state()
    ws = state.workspace_store.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")

    contract = state.trust_graph.get_contract(document_id)
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    try:
        result = detect_change(contract.file_path, contract.file_hash)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"File not found at {contract.file_path}",
        )

    message = (
        "Document has been modified since last indexing. Re-parse recommended."
        if result.changed
        else "Document is up to date."
    )

    return DocumentCheckResponse(
        document_id=document_id,
        file_path=contract.file_path,
        changed=result.changed,
        current_hash=result.current_hash,
        previous_hash=result.previous_hash,
        message=message,
    )


@router.get(
    "/{workspace_id}/sessions",
    response_model=list[SessionSummary],
)
async def get_workspace_sessions(workspace_id: str) -> list[SessionSummary]:
    """Get reasoning session history for a workspace."""
    state = get_state()
    ws = state.workspace_store.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")

    sessions = state.workspace_store.get_sessions_by_workspace(workspace_id)
    return [
        SessionSummary(
            session_id=s.session_id,
            query_text=s.query_text,
            answer=s.answer,
            answer_type=s.answer_type,
            confidence=s.confidence,
            status=s.status.value,
            started_at=s.started_at.isoformat(),
            completed_at=s.completed_at.isoformat() if s.completed_at else None,
            generation_time_ms=s.generation_time_ms,
        )
        for s in sessions
    ]
