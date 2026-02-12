"""Unit tests for conversation context retention in DocumentAgent (T184–T191).

TDD: Tests written BEFORE implementation.

Verifies that the DocumentAgent can accept prior Q&A history and include it
in the LLM context, enabling multi-turn conversations like:
  User: "What are the termination clauses?"
  Agent: "Section 12 covers termination..."
  User: "Any reference to section 5b?"  ← should understand context
"""

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
DOC_ID = "doc-ctx-001"


def _seed_graph(graph: TrustGraph) -> None:
    """Insert a contract with facts and bindings for context testing."""
    contract = Contract(
        document_id=DOC_ID,
        title="Acme Services Agreement",
        file_path="/test.docx",
        file_format="docx",
        file_hash="abc123",
        parties=["Acme Corp", "Beta Inc"],
        page_count=15,
        word_count=8000,
        indexed_at=NOW,
        last_parsed_at=NOW,
        extraction_version="1.0.0",
    )
    graph.insert_contract(contract)

    facts = [
        Fact(
            fact_id="f-t01",
            fact_type=FactType.TEXT_SPAN,
            value="Either party may terminate with 30 days written notice",
            evidence=FactEvidence(
                document_id=DOC_ID,
                text_span="Either party may terminate with 30 days written notice",
                char_start=500, char_end=555, location_hint="§12.1",
                structural_path="body > section[12]",
            ),
            extraction_method="test", extracted_at=NOW,
        ),
        Fact(
            fact_id="f-t02",
            fact_type=FactType.TEXT_SPAN,
            value="Confidentiality obligations survive for 3 years after termination",
            evidence=FactEvidence(
                document_id=DOC_ID,
                text_span="Confidentiality obligations survive for 3 years after termination",
                char_start=600, char_end=665, location_hint="§5b",
                structural_path="body > section[5]",
            ),
            extraction_method="test", extracted_at=NOW,
        ),
        Fact(
            fact_id="f-t03",
            fact_type=FactType.TEXT_SPAN,
            value="Total contract value not to exceed $500,000",
            evidence=FactEvidence(
                document_id=DOC_ID,
                text_span="Total contract value not to exceed $500,000",
                char_start=200, char_end=244, location_hint="§3.1",
                structural_path="body > section[3]",
            ),
            extraction_method="test", extracted_at=NOW,
        ),
    ]
    graph.insert_facts(facts)

    binding = Binding(
        binding_id="b-t01",
        binding_type=BindingType.DEFINITION,
        term="Provider",
        resolves_to="Acme Corp",
        source_fact_id="f-t01",
        document_id=DOC_ID,
        scope=BindingScope.CONTRACT,
    )
    graph.insert_binding(binding)


def _make_query(text: str) -> Query:
    return Query(
        query_id="q-ctx-001",
        text=text,
        scope=QueryScope.SINGLE_DOCUMENT,
        target_document_ids=[DOC_ID],
        submitted_at=NOW,
    )


def _mock_response(
    answer: str,
    answer_type: str = "fact",
    confidence: float = 0.9,
    facts_referenced: list[str] | None = None,
) -> str:
    return json.dumps({
        "answer": answer,
        "answer_type": answer_type,
        "confidence": confidence,
        "facts_referenced": facts_referenced or [],
        "reasoning_chain": "Based on contract analysis.",
    })


@pytest.fixture
def graph() -> TrustGraph:
    g = TrustGraph(":memory:")
    _seed_graph(g)
    yield g
    g.close()


# ── ChatTurn model tests ──────────────────────────────────────────


class TestChatTurnModel:
    """T184: ChatTurn model for representing prior Q&A turns."""

    def test_chat_turn_creation(self) -> None:
        """ChatTurn can be created with question and answer."""
        from contractos.models.query import ChatTurn

        turn = ChatTurn(question="What are the payment terms?", answer="Net 30 days.")
        assert turn.question == "What are the payment terms?"
        assert turn.answer == "Net 30 days."

    def test_chat_turn_serialization(self) -> None:
        """ChatTurn serializes to dict correctly."""
        from contractos.models.query import ChatTurn

        turn = ChatTurn(question="Q1", answer="A1")
        d = turn.model_dump()
        assert d["question"] == "Q1"
        assert d["answer"] == "A1"


# ── DocumentAgent chat_history parameter tests ─────────────────────


class TestDocumentAgentChatHistory:
    """T185–T187: DocumentAgent accepts and uses chat_history."""

    @pytest.mark.asyncio
    async def test_answer_accepts_chat_history(self, graph: TrustGraph) -> None:
        """DocumentAgent.answer() accepts an optional chat_history parameter."""
        from contractos.models.query import ChatTurn

        mock = MockLLMProvider(responses=[
            _mock_response("Section 12 covers termination with 30 days notice.", facts_referenced=["f-t01"]),
        ])
        agent = DocumentAgent(graph, mock)

        history = [
            ChatTurn(question="What are the termination clauses?", answer="Section 12 covers termination."),
        ]

        result = await agent.answer(_make_query("Any reference to section 5b?"), chat_history=history)
        assert result.answer is not None
        assert len(result.answer) > 0

    @pytest.mark.asyncio
    async def test_chat_history_included_in_llm_context(self, graph: TrustGraph) -> None:
        """When chat_history is provided, prior Q&A turns appear in the LLM messages."""
        from contractos.models.query import ChatTurn

        mock = MockLLMProvider(responses=[
            _mock_response("Section 5b discusses confidentiality surviving termination.", facts_referenced=["f-t02"]),
        ])
        agent = DocumentAgent(graph, mock)

        history = [
            ChatTurn(question="What are the termination clauses?", answer="Section 12 covers termination with 30 days notice."),
        ]

        await agent.answer(_make_query("Any reference to section 5b?"), chat_history=history)

        # The LLM should receive multiple messages: prior turns + current question
        assert len(mock.call_log) == 1
        messages = mock.call_log[0]["messages"]

        # Should have at least 3 messages: prior user, prior assistant, current user
        assert len(messages) >= 3

        # First message should be the prior user question
        assert messages[0]["role"] == "user"
        assert "termination clauses" in messages[0]["content"]

        # Second message should be the prior assistant answer
        assert messages[1]["role"] == "assistant"
        assert "Section 12" in messages[1]["content"]

        # Last message should be the current question with context
        assert messages[-1]["role"] == "user"
        assert "section 5b" in messages[-1]["content"]

    @pytest.mark.asyncio
    async def test_empty_chat_history_works_like_before(self, graph: TrustGraph) -> None:
        """When chat_history is empty or None, behavior is unchanged (single user message)."""
        mock = MockLLMProvider(responses=[
            _mock_response("The contract value is $500,000.", facts_referenced=["f-t03"]),
        ])
        agent = DocumentAgent(graph, mock)

        # With empty list
        result = await agent.answer(_make_query("What is the contract value?"), chat_history=[])
        assert result.answer is not None
        assert len(mock.call_log) == 1
        messages = mock.call_log[0]["messages"]
        # Should be just one user message (the context + question)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_none_chat_history_backward_compatible(self, graph: TrustGraph) -> None:
        """When chat_history is not provided (None), behavior is unchanged."""
        mock = MockLLMProvider(responses=[
            _mock_response("The contract value is $500,000.", facts_referenced=["f-t03"]),
        ])
        agent = DocumentAgent(graph, mock)

        # Without chat_history parameter at all
        result = await agent.answer(_make_query("What is the contract value?"))
        assert result.answer is not None
        assert len(mock.call_log) == 1
        messages = mock.call_log[0]["messages"]
        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_multi_turn_history(self, graph: TrustGraph) -> None:
        """Multiple prior turns are all included in the LLM context."""
        from contractos.models.query import ChatTurn

        mock = MockLLMProvider(responses=[
            _mock_response("Yes, section 5b states confidentiality survives for 3 years.", facts_referenced=["f-t02"]),
        ])
        agent = DocumentAgent(graph, mock)

        history = [
            ChatTurn(question="What are the termination clauses?", answer="Section 12 covers termination."),
            ChatTurn(question="What about confidentiality?", answer="Section 5b covers confidentiality obligations."),
        ]

        await agent.answer(_make_query("How long does confidentiality survive?"), chat_history=history)

        messages = mock.call_log[0]["messages"]
        # 2 prior turns (2 user + 2 assistant) + 1 current user = 5 messages
        assert len(messages) >= 5

        # Verify ordering: user, assistant, user, assistant, user (with context)
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[3]["role"] == "assistant"
        assert messages[4]["role"] == "user"

    @pytest.mark.asyncio
    async def test_history_truncated_if_too_long(self, graph: TrustGraph) -> None:
        """If chat history is very long, only the most recent turns are kept."""
        from contractos.models.query import ChatTurn

        mock = MockLLMProvider(responses=[
            _mock_response("Answer to the latest question.", facts_referenced=["f-t01"]),
        ])
        agent = DocumentAgent(graph, mock)

        # Create 20 turns of history — should be truncated
        history = [
            ChatTurn(question=f"Question {i}", answer=f"Answer {i}")
            for i in range(20)
        ]

        await agent.answer(_make_query("Latest question"), chat_history=history)

        messages = mock.call_log[0]["messages"]
        # Should not have all 20*2 + 1 = 41 messages; should be capped
        # We'll allow up to MAX_HISTORY_TURNS * 2 + 1 messages
        # Default MAX_HISTORY_TURNS = 10, so max 21 messages
        assert len(messages) <= 21

    @pytest.mark.asyncio
    async def test_system_prompt_includes_conversation_instruction(self, graph: TrustGraph) -> None:
        """When chat_history is provided, system prompt includes conversation context instruction."""
        from contractos.models.query import ChatTurn

        mock = MockLLMProvider(responses=[
            _mock_response("Answer with context.", facts_referenced=["f-t01"]),
        ])
        agent = DocumentAgent(graph, mock)

        history = [
            ChatTurn(question="What are the termination clauses?", answer="Section 12."),
        ]

        await agent.answer(_make_query("Tell me more"), chat_history=history)

        system = mock.call_log[0]["system"]
        assert system is not None
        # System prompt should mention conversation context
        assert "conversation" in system.lower() or "follow-up" in system.lower() or "prior" in system.lower()


# ── Query endpoint session_id tests ─────────────────────────────


class TestQueryRequestSessionId:
    """T188: QueryRequest accepts optional session_id for context continuity."""

    def test_query_request_with_session_id(self) -> None:
        """QueryRequest model accepts session_id field."""
        from contractos.api.routes.query import QueryRequest

        req = QueryRequest(
            question="Any reference to section 5b?",
            document_id="doc-001",
            session_id="s-abc12345",
        )
        assert req.session_id == "s-abc12345"

    def test_query_request_without_session_id(self) -> None:
        """QueryRequest model works without session_id (backward compatible)."""
        from contractos.api.routes.query import QueryRequest

        req = QueryRequest(
            question="What are the payment terms?",
            document_id="doc-001",
        )
        assert req.session_id is None
