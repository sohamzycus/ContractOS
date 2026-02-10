"""Unit tests for Workspace and ReasoningSession models (T015)."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from contractos.models.workspace import ReasoningSession, SessionStatus, Workspace


class TestSessionStatus:
    def test_all_statuses(self):
        expected = {"active", "completed", "failed"}
        assert {s.value for s in SessionStatus} == expected


class TestWorkspace:
    def test_valid_workspace(self, sample_workspace):
        assert sample_workspace.name == "Dell Contracts Review"
        assert len(sample_workspace.indexed_documents) == 1
        assert sample_workspace.settings == {}

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            Workspace(
                workspace_id="w-bad",
                name="",
                created_at=datetime.now(),
                last_accessed_at=datetime.now(),
            )

    def test_default_empty_documents(self):
        w = Workspace(
            workspace_id="w-empty",
            name="Empty",
            created_at=datetime.now(),
            last_accessed_at=datetime.now(),
        )
        assert w.indexed_documents == []

    def test_settings_dict(self):
        w = Workspace(
            workspace_id="w-settings",
            name="With Settings",
            created_at=datetime.now(),
            last_accessed_at=datetime.now(),
            settings={"theme": "dark", "auto_parse": True},
        )
        assert w.settings["theme"] == "dark"

    def test_serialization_roundtrip(self, sample_workspace):
        data = sample_workspace.model_dump()
        restored = Workspace.model_validate(data)
        assert restored == sample_workspace


class TestReasoningSession:
    def test_valid_session(self, sample_session):
        assert sample_session.status == SessionStatus.ACTIVE
        assert sample_session.answer is None
        assert sample_session.completed_at is None

    def test_completed_session(self):
        now = datetime.now()
        session = ReasoningSession(
            session_id="s-done",
            workspace_id="w-001",
            query_text="What are the payment terms?",
            query_scope="single_document",
            target_document_ids=["doc-001"],
            answer="Net 90 from invoice date",
            answer_type="fact",
            status=SessionStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            generation_time_ms=1200,
        )
        assert session.status == SessionStatus.COMPLETED
        assert session.answer is not None

    def test_default_status_is_active(self):
        session = ReasoningSession(
            session_id="s-new",
            workspace_id="w-001",
            query_text="test",
            query_scope="single_document",
            started_at=datetime.now(),
        )
        assert session.status == SessionStatus.ACTIVE

    def test_serialization_roundtrip(self, sample_session):
        data = sample_session.model_dump()
        restored = ReasoningSession.model_validate(data)
        assert restored == sample_session
