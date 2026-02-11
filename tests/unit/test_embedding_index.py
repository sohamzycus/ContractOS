"""Unit tests for EmbeddingIndex — FAISS-backed semantic vector search."""

from __future__ import annotations

import pytest

from contractos.fabric.embedding_index import (
    EmbeddingIndex,
    IndexedChunk,
    SearchResult,
    build_chunks_from_extraction,
)


@pytest.fixture
def sample_chunks() -> list[IndexedChunk]:
    """Create sample chunks for testing."""
    return [
        IndexedChunk(
            chunk_id="f-001",
            chunk_type="fact",
            text="The contract value is $5,000,000 payable over 3 years",
            document_id="doc-1",
            metadata={"fact_type": "text_span"},
        ),
        IndexedChunk(
            chunk_id="f-002",
            chunk_type="fact",
            text="Termination requires 90 days written notice to the other party",
            document_id="doc-1",
            metadata={"fact_type": "text_span"},
        ),
        IndexedChunk(
            chunk_id="f-003",
            chunk_type="fact",
            text="The governing law is the State of New York",
            document_id="doc-1",
            metadata={"fact_type": "text_span"},
        ),
        IndexedChunk(
            chunk_id="f-004",
            chunk_type="fact",
            text="Confidential information must not be disclosed to third parties",
            document_id="doc-1",
            metadata={"fact_type": "text_span"},
        ),
        IndexedChunk(
            chunk_id="c-001",
            chunk_type="clause",
            text="[termination] Termination and Notice Period",
            document_id="doc-1",
            metadata={"clause_type": "termination"},
        ),
        IndexedChunk(
            chunk_id="c-002",
            chunk_type="clause",
            text="[payment] Payment Terms and Schedule",
            document_id="doc-1",
            metadata={"clause_type": "payment"},
        ),
        IndexedChunk(
            chunk_id="b-001",
            chunk_type="binding",
            text="Buyer means Alpha Corporation Inc.",
            document_id="doc-1",
            metadata={"term": "Buyer", "resolves_to": "Alpha Corporation Inc."},
        ),
        IndexedChunk(
            chunk_id="b-002",
            chunk_type="binding",
            text="Vendor means Beta Technologies Ltd.",
            document_id="doc-1",
            metadata={"term": "Vendor", "resolves_to": "Beta Technologies Ltd."},
        ),
    ]


@pytest.fixture
def index_with_data(sample_chunks: list[IndexedChunk]) -> EmbeddingIndex:
    """Create an EmbeddingIndex with sample data indexed."""
    idx = EmbeddingIndex()
    idx.index_document("doc-1", sample_chunks)
    return idx


class TestEmbeddingIndexCreation:
    """Test EmbeddingIndex initialization and document indexing."""

    def test_create_empty_index(self) -> None:
        idx = EmbeddingIndex()
        assert not idx.has_document("doc-1")
        assert idx.document_chunk_count("doc-1") == 0

    def test_index_document(self, sample_chunks: list[IndexedChunk]) -> None:
        idx = EmbeddingIndex()
        count = idx.index_document("doc-1", sample_chunks)
        assert count == len(sample_chunks)
        assert idx.has_document("doc-1")
        assert idx.document_chunk_count("doc-1") == len(sample_chunks)

    def test_index_empty_chunks(self) -> None:
        idx = EmbeddingIndex()
        count = idx.index_document("doc-1", [])
        assert count == 0
        assert not idx.has_document("doc-1")

    def test_index_multiple_documents(self, sample_chunks: list[IndexedChunk]) -> None:
        idx = EmbeddingIndex()
        idx.index_document("doc-1", sample_chunks)
        chunks2 = [
            IndexedChunk(
                chunk_id="f-100",
                chunk_type="fact",
                text="Insurance coverage of $10 million is required",
                document_id="doc-2",
            ),
        ]
        idx.index_document("doc-2", chunks2)
        assert idx.has_document("doc-1")
        assert idx.has_document("doc-2")
        assert idx.document_chunk_count("doc-1") == len(sample_chunks)
        assert idx.document_chunk_count("doc-2") == 1

    def test_remove_document(self, index_with_data: EmbeddingIndex) -> None:
        assert index_with_data.has_document("doc-1")
        index_with_data.remove_document("doc-1")
        assert not index_with_data.has_document("doc-1")
        assert index_with_data.document_chunk_count("doc-1") == 0


class TestEmbeddingSearch:
    """Test semantic search functionality."""

    def test_search_returns_results(self, index_with_data: EmbeddingIndex) -> None:
        results = index_with_data.search("doc-1", "What is the contract value?")
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)

    def test_search_results_have_scores(self, index_with_data: EmbeddingIndex) -> None:
        results = index_with_data.search("doc-1", "termination notice period")
        assert all(r.score > -1.0 for r in results)
        # Results should be ordered by descending score
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_nonexistent_document(self) -> None:
        idx = EmbeddingIndex()
        results = idx.search("nonexistent", "test query")
        assert results == []

    def test_search_top_k_limit(self, index_with_data: EmbeddingIndex) -> None:
        results = index_with_data.search("doc-1", "contract terms", top_k=3)
        assert len(results) <= 3

    def test_search_filter_by_chunk_type(self, index_with_data: EmbeddingIndex) -> None:
        # Only facts
        fact_results = index_with_data.search(
            "doc-1", "termination", chunk_types=["fact"]
        )
        assert all(r.chunk.chunk_type == "fact" for r in fact_results)

        # Only clauses
        clause_results = index_with_data.search(
            "doc-1", "termination", chunk_types=["clause"]
        )
        assert all(r.chunk.chunk_type == "clause" for r in clause_results)

        # Only bindings
        binding_results = index_with_data.search(
            "doc-1", "who is the buyer", chunk_types=["binding"]
        )
        assert all(r.chunk.chunk_type == "binding" for r in binding_results)

    def test_search_semantic_relevance_payment(self, index_with_data: EmbeddingIndex) -> None:
        """Verify payment-related query returns payment-related facts first."""
        results = index_with_data.search("doc-1", "How much does the contract cost?", top_k=3)
        # The $5,000,000 fact should be in top results
        top_texts = [r.chunk.text for r in results]
        assert any("5,000,000" in t for t in top_texts), (
            f"Payment fact not in top 3 results: {top_texts}"
        )

    def test_search_semantic_relevance_termination(self, index_with_data: EmbeddingIndex) -> None:
        """Verify termination query returns termination facts first."""
        results = index_with_data.search("doc-1", "How can the contract be terminated?", top_k=3)
        top_texts = [r.chunk.text for r in results]
        assert any("termination" in t.lower() or "90 days" in t.lower() for t in top_texts), (
            f"Termination fact not in top 3 results: {top_texts}"
        )

    def test_search_semantic_relevance_parties(self, index_with_data: EmbeddingIndex) -> None:
        """Verify party query returns binding results."""
        results = index_with_data.search("doc-1", "Who are the parties to this contract?", top_k=5)
        top_texts = [r.chunk.text for r in results]
        assert any("alpha" in t.lower() or "beta" in t.lower() or "buyer" in t.lower() for t in top_texts), (
            f"Party binding not in top 5 results: {top_texts}"
        )


class TestBuildChunksFromExtraction:
    """Test the helper that converts extraction results to IndexedChunks."""

    def test_build_from_facts(self) -> None:
        from datetime import datetime
        from contractos.models.fact import Fact, FactEvidence, FactType

        facts = [
            Fact(
                fact_id="f-test-1",
                fact_type=FactType.TEXT_SPAN,
                value="Net 90 payment terms",
                evidence=FactEvidence(
                    document_id="doc-1",
                    text_span="Net 90",
                    char_start=100,
                    char_end=106,
                    location_hint="paragraph 3",
                    structural_path="body > p[3]",
                ),
                extraction_method="test",
                extracted_at=datetime.now(),
            ),
        ]
        chunks = build_chunks_from_extraction("doc-1", facts, [], [])
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "fact"
        assert "Net 90" in chunks[0].text
        assert chunks[0].chunk_id == "f-test-1"

    def test_build_from_clauses(self) -> None:
        from contractos.models.clause import Clause, ClauseTypeEnum

        clauses = [
            Clause(
                clause_id="c-test-1",
                document_id="doc-1",
                clause_type=ClauseTypeEnum.TERMINATION,
                heading="Termination",
                fact_id="f-1",
                classification_method="test",
            ),
        ]
        chunks = build_chunks_from_extraction("doc-1", [], clauses, [])
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "clause"
        assert "termination" in chunks[0].text.lower()

    def test_build_from_bindings(self) -> None:
        from contractos.models.binding import Binding, BindingType

        bindings = [
            Binding(
                binding_id="b-test-1",
                binding_type=BindingType.DEFINITION,
                term="Buyer",
                resolves_to="Alpha Corp",
                source_fact_id="f-1",
                document_id="doc-1",
            ),
        ]
        chunks = build_chunks_from_extraction("doc-1", [], [], bindings)
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "binding"
        assert "Buyer" in chunks[0].text
        assert "Alpha Corp" in chunks[0].text

    def test_build_skips_short_facts(self) -> None:
        from datetime import datetime
        from contractos.models.fact import Fact, FactEvidence, FactType

        facts = [
            Fact(
                fact_id="f-short",
                fact_type=FactType.TEXT_SPAN,
                value="a",  # Too short
                evidence=FactEvidence(
                    document_id="doc-1",
                    text_span="a",
                    char_start=0,
                    char_end=1,
                    location_hint="p1",
                    structural_path="body",
                ),
                extraction_method="test",
                extracted_at=datetime.now(),
            ),
        ]
        chunks = build_chunks_from_extraction("doc-1", facts, [], [])
        assert len(chunks) == 0

    def test_build_combined(self) -> None:
        from datetime import datetime
        from contractos.models.binding import Binding, BindingType
        from contractos.models.clause import Clause, ClauseTypeEnum
        from contractos.models.fact import Fact, FactEvidence, FactType

        facts = [
            Fact(
                fact_id="f-1",
                fact_type=FactType.TEXT_SPAN,
                value="$5,000,000 total value",
                evidence=FactEvidence(
                    document_id="doc-1",
                    text_span="$5,000,000",
                    char_start=0,
                    char_end=10,
                    location_hint="section 4",
                    structural_path="body",
                ),
                extraction_method="test",
                extracted_at=datetime.now(),
            ),
        ]
        clauses = [
            Clause(
                clause_id="c-1",
                document_id="doc-1",
                clause_type=ClauseTypeEnum.PAYMENT,
                heading="Payment Terms",
                fact_id="f-1",
                classification_method="test",
            ),
        ]
        bindings = [
            Binding(
                binding_id="b-1",
                binding_type=BindingType.DEFINITION,
                term="Vendor",
                resolves_to="Acme Inc",
                source_fact_id="f-1",
                document_id="doc-1",
            ),
        ]
        chunks = build_chunks_from_extraction("doc-1", facts, clauses, bindings)
        assert len(chunks) == 3
        types = {c.chunk_type for c in chunks}
        assert types == {"fact", "clause", "binding"}
