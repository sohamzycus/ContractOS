"""Integration test for session history (T105).

Tests:
- Create 5 reasoning sessions
- Retrieve workspace sessions
- Verify sessions listed in reverse chronological order
- Verify query text and answer summary present
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from contractos.fabric.trust_graph import TrustGraph
from contractos.fabric.workspace_store import WorkspaceStore
from contractos.models.workspace import ReasoningSession, SessionStatus, Workspace

BASE_TIME = datetime(2025, 3, 1, 10, 0, 0)


@pytest.fixture
def store_with_sessions():
    """Create a workspace with 5 completed sessions."""
    graph = TrustGraph(":memory:")
    ws_store = WorkspaceStore(graph._conn)

    # Create workspace
    ws = Workspace(
        workspace_id="w-history",
        name="Session History Test",
        indexed_documents=["doc-001"],
        created_at=BASE_TIME,
        last_accessed_at=BASE_TIME,
    )
    ws_store.create_workspace(ws)

    # Create 5 sessions at different times
    queries = [
        ("What are the payment terms?", "Net 90 from invoice date", "fact", 0.95),
        ("Who are the parties?", "Alpha Corp and Beta Services", "fact", 1.0),
        ("What is the termination notice period?", "60 days written notice", "fact", 0.9),
        ("Does this cover IT equipment?", "Yes, Dell Inspiron is in Schedule A", "inference", 0.85),
        ("What are the confidentiality obligations?", "Both parties maintain confidentiality per Appendix A", "fact", 0.88),
    ]

    for i, (query, answer, atype, conf) in enumerate(queries):
        started = BASE_TIME + timedelta(hours=i)
        session = ReasoningSession(
            session_id=f"s-{i+1:03d}",
            workspace_id="w-history",
            query_text=query,
            query_scope="single_document",
            target_document_ids=["doc-001"],
            status=SessionStatus.ACTIVE,
            started_at=started,
        )
        ws_store.create_session(session)
        ws_store.complete_session(
            f"s-{i+1:03d}",
            answer=answer,
            answer_type=atype,
            confidence=conf,
            generation_time_ms=1000 + i * 200,
        )

    yield ws_store
    graph.close()


class TestSessionHistory:
    def test_retrieves_all_sessions(self, store_with_sessions: WorkspaceStore) -> None:
        sessions = store_with_sessions.get_sessions_by_workspace("w-history")
        assert len(sessions) == 5

    def test_sessions_in_reverse_chronological_order(
        self, store_with_sessions: WorkspaceStore
    ) -> None:
        sessions = store_with_sessions.get_sessions_by_workspace("w-history")
        # Most recent first (s-005 started latest)
        for i in range(len(sessions) - 1):
            assert sessions[i].started_at >= sessions[i + 1].started_at

    def test_most_recent_session_is_last_query(
        self, store_with_sessions: WorkspaceStore
    ) -> None:
        sessions = store_with_sessions.get_sessions_by_workspace("w-history")
        assert sessions[0].query_text == "What are the confidentiality obligations?"

    def test_all_sessions_completed(self, store_with_sessions: WorkspaceStore) -> None:
        sessions = store_with_sessions.get_sessions_by_workspace("w-history")
        for session in sessions:
            assert session.status == SessionStatus.COMPLETED
            assert session.answer is not None
            assert session.answer_type is not None
            assert session.confidence is not None
            assert session.completed_at is not None

    def test_session_has_query_text(self, store_with_sessions: WorkspaceStore) -> None:
        sessions = store_with_sessions.get_sessions_by_workspace("w-history")
        for session in sessions:
            assert len(session.query_text) > 0

    def test_session_has_answer_summary(self, store_with_sessions: WorkspaceStore) -> None:
        sessions = store_with_sessions.get_sessions_by_workspace("w-history")
        for session in sessions:
            assert len(session.answer) > 0

    def test_empty_workspace_has_no_sessions(
        self, store_with_sessions: WorkspaceStore
    ) -> None:
        sessions = store_with_sessions.get_sessions_by_workspace("no-such-workspace")
        assert sessions == []

    def test_generation_times_recorded(self, store_with_sessions: WorkspaceStore) -> None:
        sessions = store_with_sessions.get_sessions_by_workspace("w-history")
        for session in sessions:
            assert session.generation_time_ms is not None
            assert session.generation_time_ms > 0
