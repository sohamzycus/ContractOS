"""Unit tests for workspace-document association (T103).

Tests:
- Add document to workspace
- Remove document from workspace
- List documents in workspace
- Document appears only in associated workspaces
- Remove document from workspace
"""

from __future__ import annotations

from datetime import datetime

import pytest

from contractos.fabric.trust_graph import TrustGraph
from contractos.fabric.workspace_store import WorkspaceStore
from contractos.models.workspace import Workspace

NOW = datetime(2025, 3, 1, 12, 0, 0)


@pytest.fixture
def store() -> WorkspaceStore:
    graph = TrustGraph(":memory:")
    ws = WorkspaceStore(graph._conn)
    yield ws
    graph.close()


def _ws(ws_id: str = "w-001", name: str = "Test", docs: list[str] | None = None) -> Workspace:
    return Workspace(
        workspace_id=ws_id,
        name=name,
        indexed_documents=docs or [],
        created_at=NOW,
        last_accessed_at=NOW,
    )


class TestWorkspaceDocumentAssociation:
    def test_add_document(self, store: WorkspaceStore) -> None:
        store.create_workspace(_ws())
        store.add_document_to_workspace("w-001", "doc-001")
        ws = store.get_workspace("w-001")
        assert ws is not None
        assert "doc-001" in ws.indexed_documents

    def test_add_multiple_documents(self, store: WorkspaceStore) -> None:
        store.create_workspace(_ws())
        store.add_document_to_workspace("w-001", "doc-001")
        store.add_document_to_workspace("w-001", "doc-002")
        store.add_document_to_workspace("w-001", "doc-003")
        ws = store.get_workspace("w-001")
        assert ws is not None
        assert len(ws.indexed_documents) == 3
        assert set(ws.indexed_documents) == {"doc-001", "doc-002", "doc-003"}

    def test_remove_document(self, store: WorkspaceStore) -> None:
        store.create_workspace(_ws(docs=["doc-001", "doc-002"]))
        store.remove_document_from_workspace("w-001", "doc-001")
        ws = store.get_workspace("w-001")
        assert ws is not None
        assert "doc-001" not in ws.indexed_documents
        assert "doc-002" in ws.indexed_documents

    def test_remove_nonexistent_document_is_noop(self, store: WorkspaceStore) -> None:
        store.create_workspace(_ws(docs=["doc-001"]))
        store.remove_document_from_workspace("w-001", "doc-999")
        ws = store.get_workspace("w-001")
        assert ws is not None
        assert ws.indexed_documents == ["doc-001"]

    def test_remove_from_nonexistent_workspace_raises(self, store: WorkspaceStore) -> None:
        with pytest.raises(ValueError, match="not found"):
            store.remove_document_from_workspace("no-such", "doc-001")

    def test_document_in_only_associated_workspace(self, store: WorkspaceStore) -> None:
        store.create_workspace(_ws("w-001", "Workspace A"))
        store.create_workspace(_ws("w-002", "Workspace B"))
        store.add_document_to_workspace("w-001", "doc-shared")
        store.add_document_to_workspace("w-002", "doc-shared")
        store.add_document_to_workspace("w-001", "doc-only-a")

        ws_a = store.get_workspace("w-001")
        ws_b = store.get_workspace("w-002")
        assert ws_a is not None and ws_b is not None
        assert "doc-shared" in ws_a.indexed_documents
        assert "doc-shared" in ws_b.indexed_documents
        assert "doc-only-a" in ws_a.indexed_documents
        assert "doc-only-a" not in ws_b.indexed_documents

    def test_list_documents_empty_workspace(self, store: WorkspaceStore) -> None:
        store.create_workspace(_ws())
        ws = store.get_workspace("w-001")
        assert ws is not None
        assert ws.indexed_documents == []

    def test_duplicate_add_is_idempotent(self, store: WorkspaceStore) -> None:
        store.create_workspace(_ws())
        store.add_document_to_workspace("w-001", "doc-001")
        store.add_document_to_workspace("w-001", "doc-001")
        ws = store.get_workspace("w-001")
        assert ws is not None
        assert ws.indexed_documents.count("doc-001") == 1
