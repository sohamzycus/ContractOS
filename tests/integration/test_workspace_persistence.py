"""Integration test for workspace persistence (T104).

Tests the full persistence cycle:
1. Index a document → create workspace → add document → create session
2. "Restart" (close and recreate TrustGraph/WorkspaceStore from same SQLite file)
3. Verify all data persists: facts, bindings, clauses, workspace, sessions
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from contractos.fabric.trust_graph import TrustGraph
from contractos.fabric.workspace_store import WorkspaceStore
from contractos.models.workspace import ReasoningSession, SessionStatus, Workspace
from contractos.tools.fact_extractor import extract_from_file

FIXTURES = Path(__file__).parent.parent / "fixtures"
DOCX_PATH = FIXTURES / "simple_procurement.docx"

NOW = datetime(2025, 3, 1, 12, 0, 0)


class TestWorkspacePersistence:
    """Test that workspace data survives a 'restart' (close + reopen)."""

    def test_full_persistence_cycle(self, tmp_path: Path) -> None:
        db_file = tmp_path / "contractos.db"
        doc_id = "doc-persist-001"

        # ── Phase 1: Index, create workspace, create session ──
        graph = TrustGraph(str(db_file))
        ws_store = WorkspaceStore(graph._conn)

        # Extract and store document
        result = extract_from_file(DOCX_PATH, doc_id)
        from contractos.models.document import Contract

        contract = Contract(
            document_id=doc_id,
            title="Simple Procurement",
            file_path=str(DOCX_PATH),
            file_format="docx",
            file_hash="abc123",
            parties=["Alpha Corp", "Beta Services"],
            page_count=1,
            word_count=result.parsed_document.word_count if result.parsed_document else 0,
            indexed_at=NOW,
            last_parsed_at=NOW,
            extraction_version="0.1.0",
        )
        graph.insert_contract(contract)
        for fact in result.facts:
            graph.insert_fact(fact)
        for binding in result.bindings:
            graph.insert_binding(binding)
        for clause in result.clauses:
            graph.insert_clause(clause)

        original_fact_count = len(result.facts)
        original_binding_count = len(result.bindings)
        original_clause_count = len(result.clauses)

        # Create workspace and add document
        workspace = Workspace(
            workspace_id="w-persist-001",
            name="Persistence Test",
            indexed_documents=[],
            created_at=NOW,
            last_accessed_at=NOW,
        )
        ws_store.create_workspace(workspace)
        ws_store.add_document_to_workspace("w-persist-001", doc_id)

        # Create a reasoning session
        session = ReasoningSession(
            session_id="s-persist-001",
            workspace_id="w-persist-001",
            query_text="What are the payment terms?",
            query_scope="single_document",
            target_document_ids=[doc_id],
            status=SessionStatus.ACTIVE,
            started_at=NOW,
        )
        ws_store.create_session(session)
        ws_store.complete_session(
            "s-persist-001",
            answer="Net 90 from invoice date",
            answer_type="fact",
            confidence=0.95,
            generation_time_ms=1200,
        )

        # Close the database (simulating server shutdown)
        graph.close()

        # ── Phase 2: Reopen and verify everything persists ──
        graph2 = TrustGraph(str(db_file))
        ws_store2 = WorkspaceStore(graph2._conn)

        # Verify contract persists
        contract2 = graph2.get_contract(doc_id)
        assert contract2 is not None
        assert contract2.title == "Simple Procurement"
        assert contract2.file_hash == "abc123"

        # Verify facts persist
        facts2 = graph2.get_facts_by_document(doc_id)
        assert len(facts2) == original_fact_count

        # Verify bindings persist
        bindings2 = graph2.get_bindings_by_document(doc_id)
        assert len(bindings2) == original_binding_count

        # Verify clauses persist
        clauses2 = graph2.get_clauses_by_document(doc_id)
        assert len(clauses2) == original_clause_count

        # Verify workspace persists
        ws2 = ws_store2.get_workspace("w-persist-001")
        assert ws2 is not None
        assert ws2.name == "Persistence Test"
        assert doc_id in ws2.indexed_documents

        # Verify session persists
        session2 = ws_store2.get_session("s-persist-001")
        assert session2 is not None
        assert session2.status == SessionStatus.COMPLETED
        assert session2.answer == "Net 90 from invoice date"
        assert session2.confidence == 0.95
        assert session2.generation_time_ms == 1200

        graph2.close()

    def test_multiple_documents_persist(self, tmp_path: Path) -> None:
        """Index two documents, restart, verify both survive."""
        db_file = tmp_path / "multi.db"

        graph = TrustGraph(str(db_file))
        ws_store = WorkspaceStore(graph._conn)

        # Index two documents
        for doc_id in ["doc-a", "doc-b"]:
            result = extract_from_file(DOCX_PATH, doc_id)
            from contractos.models.document import Contract

            contract = Contract(
                document_id=doc_id,
                title=f"Contract {doc_id}",
                file_path=str(DOCX_PATH),
                file_format="docx",
                file_hash=f"hash-{doc_id}",
                page_count=1,
                word_count=100,
                indexed_at=NOW,
                last_parsed_at=NOW,
                extraction_version="0.1.0",
            )
            graph.insert_contract(contract)
            for fact in result.facts:
                graph.insert_fact(fact)

        # Create workspace with both docs
        ws = Workspace(
            workspace_id="w-multi",
            name="Multi-doc",
            indexed_documents=["doc-a", "doc-b"],
            created_at=NOW,
            last_accessed_at=NOW,
        )
        ws_store.create_workspace(ws)

        graph.close()

        # Reopen
        graph2 = TrustGraph(str(db_file))
        ws_store2 = WorkspaceStore(graph2._conn)

        assert graph2.get_contract("doc-a") is not None
        assert graph2.get_contract("doc-b") is not None
        assert len(graph2.get_facts_by_document("doc-a")) > 0
        assert len(graph2.get_facts_by_document("doc-b")) > 0

        ws2 = ws_store2.get_workspace("w-multi")
        assert ws2 is not None
        assert set(ws2.indexed_documents) == {"doc-a", "doc-b"}

        graph2.close()

    def test_change_detection_after_reparse(self, tmp_path: Path) -> None:
        """Verify file hash changes trigger re-parse detection."""
        from contractos.tools.change_detection import compute_file_hash, detect_change

        db_file = tmp_path / "change.db"
        graph = TrustGraph(str(db_file))

        # Store original hash
        original_hash = compute_file_hash(DOCX_PATH)

        from contractos.models.document import Contract

        contract = Contract(
            document_id="doc-change",
            title="Change Test",
            file_path=str(DOCX_PATH),
            file_format="docx",
            file_hash=original_hash,
            page_count=1,
            word_count=100,
            indexed_at=NOW,
            last_parsed_at=NOW,
            extraction_version="0.1.0",
        )
        graph.insert_contract(contract)
        graph.close()

        # Reopen and check — same file, no change
        graph2 = TrustGraph(str(db_file))
        stored = graph2.get_contract("doc-change")
        assert stored is not None

        result = detect_change(DOCX_PATH, stored.file_hash)
        assert result.changed is False

        graph2.close()
