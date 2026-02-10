"""Unit tests for DocumentAgent — Q&A over a single contract (T076–T080)."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from contractos.agents.document_agent import DocumentAgent
from contractos.fabric.trust_graph import TrustGraph
from contractos.llm.provider import MockLLMProvider
from contractos.models.binding import Binding, BindingScope, BindingType
from contractos.models.document import Contract
from contractos.models.fact import EntityType, Fact, FactEvidence, FactType
from contractos.models.query import Query, QueryScope

NOW = datetime(2025, 2, 9, 12, 0, 0)
DOC_ID = "doc-001"


def _seed_graph(graph: TrustGraph) -> None:
    """Insert a contract with facts and bindings into the graph."""
    contract = Contract(
        document_id=DOC_ID,
        title="Dell MSA",
        file_path="/test.docx",
        file_format="docx",
        file_hash="abc",
        parties=["Dell", "Acme"],
        page_count=10,
        word_count=5000,
        indexed_at=NOW,
        last_parsed_at=NOW,
        extraction_version="1.0.0",
    )
    graph.insert_contract(contract)

    facts = [
        Fact(
            fact_id="f-001",
            fact_type=FactType.TEXT_SPAN,
            value="Net 90 from invoice date",
            evidence=FactEvidence(
                document_id=DOC_ID, text_span="Net 90 from invoice date",
                char_start=100, char_end=124, location_hint="§5.2",
                structural_path="body > section[5]",
            ),
            extraction_method="test", extracted_at=NOW,
        ),
        Fact(
            fact_id="f-002",
            fact_type=FactType.ENTITY,
            entity_type=EntityType.PARTY,
            value="Dell Technologies",
            evidence=FactEvidence(
                document_id=DOC_ID, text_span="Dell Technologies",
                char_start=50, char_end=67, location_hint="§1.1",
                structural_path="body > section[1]",
            ),
            extraction_method="test", extracted_at=NOW,
        ),
        Fact(
            fact_id="f-003",
            fact_type=FactType.TEXT_SPAN,
            value="$150,000.00",
            evidence=FactEvidence(
                document_id=DOC_ID, text_span="$150,000.00",
                char_start=200, char_end=211, location_hint="§3.1",
                structural_path="body > section[3]",
            ),
            extraction_method="test", extracted_at=NOW,
        ),
    ]
    graph.insert_facts(facts)

    binding = Binding(
        binding_id="b-001",
        binding_type=BindingType.DEFINITION,
        term="Supplier",
        resolves_to="Dell Technologies",
        source_fact_id="f-002",
        document_id=DOC_ID,
        scope=BindingScope.CONTRACT,
    )
    graph.insert_binding(binding)


def _make_query(text: str = "What are the payment terms?") -> Query:
    return Query(
        query_id="q-001",
        text=text,
        scope=QueryScope.SINGLE_DOCUMENT,
        target_document_ids=[DOC_ID],
        submitted_at=NOW,
    )


def _mock_llm_response(
    answer: str = "Payment terms are Net 90 from invoice date.",
    answer_type: str = "fact",
    confidence: float = 0.95,
    facts_referenced: list[str] | None = None,
) -> str:
    return json.dumps({
        "answer": answer,
        "answer_type": answer_type,
        "confidence": confidence,
        "facts_referenced": facts_referenced or ["f-001"],
        "reasoning_chain": "Found payment terms in §5.2.",
    })


@pytest.fixture
def graph() -> TrustGraph:
    g = TrustGraph(":memory:")
    _seed_graph(g)
    yield g
    g.close()


@pytest.fixture
def mock_llm() -> MockLLMProvider:
    return MockLLMProvider(responses=[_mock_llm_response()])


@pytest.fixture
def agent(graph: TrustGraph, mock_llm: MockLLMProvider) -> DocumentAgent:
    return DocumentAgent(graph, mock_llm)


class TestDocumentAgentBasics:
    @pytest.mark.asyncio
    async def test_returns_query_result(self, agent: DocumentAgent) -> None:
        result = await agent.answer(_make_query())
        assert result.query_id == "q-001"
        assert result.answer_type in ("fact", "inference", "not_found", "opinion")

    @pytest.mark.asyncio
    async def test_answer_contains_content(self, agent: DocumentAgent) -> None:
        result = await agent.answer(_make_query())
        assert len(result.answer) > 0
        assert "Net 90" in result.answer

    @pytest.mark.asyncio
    async def test_has_confidence(self, agent: DocumentAgent) -> None:
        result = await agent.answer(_make_query())
        assert result.confidence is not None
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_has_provenance(self, agent: DocumentAgent) -> None:
        result = await agent.answer(_make_query())
        assert result.provenance is not None
        assert len(result.provenance.nodes) > 0

    @pytest.mark.asyncio
    async def test_facts_referenced(self, agent: DocumentAgent) -> None:
        result = await agent.answer(_make_query())
        assert "f-001" in result.facts_referenced

    @pytest.mark.asyncio
    async def test_generation_time_recorded(self, agent: DocumentAgent) -> None:
        result = await agent.answer(_make_query())
        assert result.generation_time_ms >= 0


class TestDocumentAgentContext:
    @pytest.mark.asyncio
    async def test_llm_receives_facts_in_context(self, graph: TrustGraph) -> None:
        mock = MockLLMProvider(responses=[_mock_llm_response()])
        agent = DocumentAgent(graph, mock)
        await agent.answer(_make_query())
        # Check that the LLM was called with facts in the message
        assert len(mock.call_log) == 1
        user_msg = mock.call_log[0]["messages"][0]["content"]
        assert "f-001" in user_msg
        assert "Net 90" in user_msg

    @pytest.mark.asyncio
    async def test_llm_receives_bindings_in_context(self, graph: TrustGraph) -> None:
        mock = MockLLMProvider(responses=[_mock_llm_response()])
        agent = DocumentAgent(graph, mock)
        await agent.answer(_make_query())
        user_msg = mock.call_log[0]["messages"][0]["content"]
        assert "Supplier" in user_msg
        assert "Dell Technologies" in user_msg

    @pytest.mark.asyncio
    async def test_system_prompt_sent(self, graph: TrustGraph) -> None:
        mock = MockLLMProvider(responses=[_mock_llm_response()])
        agent = DocumentAgent(graph, mock)
        await agent.answer(_make_query())
        assert mock.call_log[0]["system"] is not None
        assert "ContractOS" in mock.call_log[0]["system"]


class TestDocumentAgentEdgeCases:
    @pytest.mark.asyncio
    async def test_nonexistent_document(self, graph: TrustGraph) -> None:
        mock = MockLLMProvider()
        agent = DocumentAgent(graph, mock)
        query = Query(
            query_id="q-002", text="What?",
            scope=QueryScope.SINGLE_DOCUMENT,
            target_document_ids=["doc-nonexistent"], submitted_at=NOW,
        )
        result = await agent.answer(query)
        assert result.answer_type == "not_found"
        assert "No facts" in result.answer

    @pytest.mark.asyncio
    async def test_no_facts_for_document(self, graph: TrustGraph) -> None:
        # Insert a contract with no facts
        from contractos.models.document import Contract
        graph.insert_contract(Contract(
            document_id="doc-empty", title="Empty", file_path="/e.docx",
            file_format="docx", file_hash="x", page_count=0, word_count=0,
            indexed_at=NOW, last_parsed_at=NOW, extraction_version="1.0.0",
        ))
        mock = MockLLMProvider()
        agent = DocumentAgent(graph, mock)
        query = Query(
            query_id="q-003", text="What?",
            scope=QueryScope.SINGLE_DOCUMENT,
            target_document_ids=["doc-empty"], submitted_at=NOW,
        )
        result = await agent.answer(query)
        assert result.answer_type == "not_found"
        assert "No facts" in result.answer

    @pytest.mark.asyncio
    async def test_llm_error_handled(self, graph: TrustGraph) -> None:
        mock = MockLLMProvider(responses=["not valid json"])
        agent = DocumentAgent(graph, mock)
        result = await agent.answer(_make_query())
        assert "Error" in result.answer
        assert result.answer_type == "not_found"

    @pytest.mark.asyncio
    async def test_multiple_facts_referenced(self, graph: TrustGraph) -> None:
        resp = _mock_llm_response(
            answer="The total is $150,000 with Net 90 terms.",
            facts_referenced=["f-001", "f-003"],
        )
        mock = MockLLMProvider(responses=[resp])
        agent = DocumentAgent(graph, mock)
        result = await agent.answer(_make_query())
        assert len(result.facts_referenced) == 2
        assert len(result.provenance.nodes) == 2
