"""Unit tests for Query and QueryResult models (T014)."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from contractos.models.provenance import ProvenanceChain, ProvenanceNode
from contractos.models.query import Query, QueryResult, QueryScope


class TestQueryScope:
    def test_all_scopes(self):
        expected = {"single_document", "document_family", "repository"}
        assert {s.value for s in QueryScope} == expected


class TestQuery:
    def test_valid_query(self, sample_query):
        assert sample_query.text == "What are the payment terms?"
        assert sample_query.scope == QueryScope.SINGLE_DOCUMENT

    def test_empty_text_rejected(self):
        with pytest.raises(ValidationError):
            Query(
                query_id="q-bad",
                text="",
                target_document_ids=["doc-1"],
                submitted_at=datetime.now(),
            )

    def test_empty_document_ids_rejected(self):
        with pytest.raises(ValidationError):
            Query(
                query_id="q-bad",
                text="test question",
                target_document_ids=[],
                submitted_at=datetime.now(),
            )

    def test_default_scope_is_single_document(self):
        q = Query(
            query_id="q-test",
            text="test",
            target_document_ids=["doc-1"],
            submitted_at=datetime.now(),
        )
        assert q.scope == QueryScope.SINGLE_DOCUMENT


class TestQueryResult:
    def test_valid_result(self, sample_query_result):
        assert sample_query_result.answer_type == "fact"
        assert sample_query_result.confidence is None  # facts have no confidence
        assert sample_query_result.provenance is not None

    def test_provenance_is_required(self):
        """Every answer must have a provenance chain."""
        with pytest.raises(ValidationError):
            QueryResult(
                result_id="r-bad",
                query_id="q-1",
                answer="test",
                answer_type="fact",
                provenance=None,  # type: ignore[arg-type]
                generated_at=datetime.now(),
                generation_time_ms=100,
            )

    def test_valid_answer_types(self):
        provenance = ProvenanceChain(
            nodes=[ProvenanceNode(node_type="fact", reference_id="f-1", summary="test")],
            reasoning_summary="test",
        )
        for at in ["fact", "binding", "inference", "not_found"]:
            result = QueryResult(
                result_id="r-1",
                query_id="q-1",
                answer="test",
                answer_type=at,
                provenance=provenance,
                generated_at=datetime.now(),
                generation_time_ms=100,
            )
            assert result.answer_type == at

    def test_invalid_answer_type_rejected(self):
        provenance = ProvenanceChain(
            nodes=[ProvenanceNode(node_type="fact", reference_id="f-1", summary="test")],
            reasoning_summary="test",
        )
        with pytest.raises(ValidationError):
            QueryResult(
                result_id="r-1",
                query_id="q-1",
                answer="test",
                answer_type="opinion",
                provenance=provenance,
                generated_at=datetime.now(),
                generation_time_ms=100,
            )

    def test_negative_generation_time_rejected(self):
        provenance = ProvenanceChain(
            nodes=[ProvenanceNode(node_type="fact", reference_id="f-1", summary="test")],
            reasoning_summary="test",
        )
        with pytest.raises(ValidationError):
            QueryResult(
                result_id="r-1",
                query_id="q-1",
                answer="test",
                answer_type="fact",
                provenance=provenance,
                generated_at=datetime.now(),
                generation_time_ms=-1,
            )

    def test_serialization_roundtrip(self, sample_query_result):
        data = sample_query_result.model_dump()
        restored = QueryResult.model_validate(data)
        assert restored == sample_query_result
