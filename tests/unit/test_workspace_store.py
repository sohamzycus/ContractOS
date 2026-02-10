"""Unit tests for WorkspaceStore — workspace and session persistence."""

from __future__ import annotations

from datetime import datetime

import pytest

from contractos.fabric.trust_graph import TrustGraph
from contractos.fabric.workspace_store import WorkspaceStore
from contractos.models.workspace import ReasoningSession, SessionStatus, Workspace

NOW = datetime(2025, 2, 9, 12, 0, 0)


@pytest.fixture
def store() -> WorkspaceStore:
    graph = TrustGraph(":memory:")
    ws = WorkspaceStore(graph._conn)
    yield ws
    graph.close()


def _make_workspace(
    workspace_id: str = "w-001",
    name: str = "Dell Review",
    docs: list[str] | None = None,
) -> Workspace:
    return Workspace(
        workspace_id=workspace_id,
        name=name,
        indexed_documents=docs or ["doc-001"],
        created_at=NOW,
        last_accessed_at=NOW,
    )


def _make_session(
    session_id: str = "s-001",
    workspace_id: str = "w-001",
) -> ReasoningSession:
    return ReasoningSession(
        session_id=session_id,
        workspace_id=workspace_id,
        query_text="What are the payment terms?",
        query_scope="single_document",
        target_document_ids=["doc-001"],
        status=SessionStatus.ACTIVE,
        started_at=NOW,
    )


# ── Workspace CRUD ─────────────────────────────────────────────────


class TestWorkspaceCRUD:
    def test_create_and_get(self, store: WorkspaceStore) -> None:
        ws = _make_workspace()
        store.create_workspace(ws)
        result = store.get_workspace("w-001")
        assert result is not None
        assert result.workspace_id == "w-001"
        assert result.name == "Dell Review"
        assert result.indexed_documents == ["doc-001"]

    def test_get_nonexistent(self, store: WorkspaceStore) -> None:
        assert store.get_workspace("no-such") is None

    def test_list_workspaces_ordered_by_last_accessed(self, store: WorkspaceStore) -> None:
        ws1 = _make_workspace("w-001", "First")
        ws2 = Workspace(
            workspace_id="w-002", name="Second", indexed_documents=[],
            created_at=NOW, last_accessed_at=datetime(2025, 3, 1, 12, 0, 0),
        )
        store.create_workspace(ws1)
        store.create_workspace(ws2)
        workspaces = store.list_workspaces()
        assert len(workspaces) == 2
        # Most recently accessed first
        assert workspaces[0].workspace_id == "w-002"

    def test_list_empty(self, store: WorkspaceStore) -> None:
        assert store.list_workspaces() == []

    def test_update_last_accessed(self, store: WorkspaceStore) -> None:
        store.create_workspace(_make_workspace())
        new_ts = datetime(2025, 6, 15, 10, 0, 0)
        store.update_last_accessed("w-001", new_ts)
        result = store.get_workspace("w-001")
        assert result is not None
        assert result.last_accessed_at == new_ts

    def test_add_document_to_workspace(self, store: WorkspaceStore) -> None:
        store.create_workspace(_make_workspace())
        store.add_document_to_workspace("w-001", "doc-002")
        result = store.get_workspace("w-001")
        assert result is not None
        assert "doc-002" in result.indexed_documents
        assert "doc-001" in result.indexed_documents

    def test_add_duplicate_document_is_noop(self, store: WorkspaceStore) -> None:
        store.create_workspace(_make_workspace())
        store.add_document_to_workspace("w-001", "doc-001")  # already there
        result = store.get_workspace("w-001")
        assert result is not None
        assert result.indexed_documents == ["doc-001"]

    def test_add_document_to_nonexistent_workspace_raises(self, store: WorkspaceStore) -> None:
        with pytest.raises(ValueError, match="not found"):
            store.add_document_to_workspace("no-such", "doc-001")

    def test_delete_workspace(self, store: WorkspaceStore) -> None:
        store.create_workspace(_make_workspace())
        assert store.delete_workspace("w-001") is True
        assert store.get_workspace("w-001") is None

    def test_delete_nonexistent_returns_false(self, store: WorkspaceStore) -> None:
        assert store.delete_workspace("no-such") is False

    def test_settings_roundtrip(self, store: WorkspaceStore) -> None:
        ws = Workspace(
            workspace_id="w-001", name="Custom",
            indexed_documents=[], created_at=NOW, last_accessed_at=NOW,
            settings={"theme": "dark", "max_results": 10},
        )
        store.create_workspace(ws)
        result = store.get_workspace("w-001")
        assert result is not None
        assert result.settings == {"theme": "dark", "max_results": 10}


# ── Session CRUD ───────────────────────────────────────────────────


class TestSessionCRUD:
    def test_create_and_get(self, store: WorkspaceStore) -> None:
        store.create_workspace(_make_workspace())
        session = _make_session()
        store.create_session(session)
        result = store.get_session("s-001")
        assert result is not None
        assert result.session_id == "s-001"
        assert result.status == SessionStatus.ACTIVE
        assert result.answer is None

    def test_get_nonexistent(self, store: WorkspaceStore) -> None:
        assert store.get_session("no-such") is None

    def test_get_sessions_by_workspace(self, store: WorkspaceStore) -> None:
        store.create_workspace(_make_workspace())
        store.create_session(_make_session("s-001"))
        store.create_session(_make_session("s-002"))
        sessions = store.get_sessions_by_workspace("w-001")
        assert len(sessions) == 2

    def test_complete_session(self, store: WorkspaceStore) -> None:
        store.create_workspace(_make_workspace())
        store.create_session(_make_session())
        store.complete_session(
            "s-001",
            answer="Net 90 from invoice date",
            answer_type="fact",
            confidence=0.95,
            generation_time_ms=1200,
        )
        result = store.get_session("s-001")
        assert result is not None
        assert result.status == SessionStatus.COMPLETED
        assert result.answer == "Net 90 from invoice date"
        assert result.answer_type == "fact"
        assert result.confidence == 0.95
        assert result.completed_at is not None
        assert result.generation_time_ms == 1200

    def test_fail_session(self, store: WorkspaceStore) -> None:
        store.create_workspace(_make_workspace())
        store.create_session(_make_session())
        store.fail_session("s-001", "LLM timeout")
        result = store.get_session("s-001")
        assert result is not None
        assert result.status == SessionStatus.FAILED
        assert result.answer == "LLM timeout"
        assert result.completed_at is not None

    def test_sessions_cascade_on_workspace_delete(self, store: WorkspaceStore) -> None:
        store.create_workspace(_make_workspace())
        store.create_session(_make_session())
        store.delete_workspace("w-001")
        assert store.get_session("s-001") is None
