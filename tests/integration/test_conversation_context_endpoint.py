"""Integration tests for conversation context retention via /query/ask endpoint (T189–T191).

TDD: Tests written BEFORE implementation.

Verifies that when session_id is passed to /query/ask, prior Q&A from that
document session is included as chat history for the LLM, enabling multi-turn
conversations.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from contractos.api.app import create_app
from contractos.api.deps import init_state, shutdown_state
from contractos.config import ContractOSConfig, LLMConfig, StorageConfig
from contractos.llm.provider import MockLLMProvider

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _mock_qa_response(
    answer: str = "The contract has standard termination clauses in Section 12.",
    facts_referenced: list[str] | None = None,
) -> str:
    """Standard mock LLM response for Q&A."""
    return json.dumps({
        "answer": answer,
        "answer_type": "fact",
        "confidence": 0.9,
        "facts_referenced": facts_referenced or [],
        "reasoning_chain": "Based on contract analysis.",
    })


@pytest.fixture
def test_config() -> ContractOSConfig:
    return ContractOSConfig(
        storage=StorageConfig(database_path=":memory:"),
        llm=LLMConfig(provider="mock"),
    )


@pytest.fixture
async def client(test_config: ContractOSConfig):
    """Create async test client with in-memory database."""
    state = init_state(test_config)
    app = create_app(test_config)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    shutdown_state()


@pytest.fixture
def sample_pdf():
    """Path to a test PDF fixture."""
    pdf_path = FIXTURES_DIR / "simple_nda.pdf"
    if pdf_path.exists():
        return pdf_path
    return None


async def _upload_document(c: AsyncClient, pdf_path: Path) -> str:
    """Upload a PDF document and return its document_id."""
    with open(pdf_path, "rb") as f:
        resp = await c.post(
            "/contracts/upload",
            files={"file": (pdf_path.name, f, "application/pdf")},
        )
    assert resp.status_code in (200, 201), f"Upload failed: {resp.status_code} {resp.text}"
    return resp.json()["document_id"]


@pytest.mark.asyncio
class TestConversationContextEndpoint:
    """T189–T191: Integration tests for conversation context retention."""

    async def test_first_query_returns_session_id(self, client, sample_pdf) -> None:
        """First query returns a session_id that can be used for follow-ups."""
        if sample_pdf is None:
            pytest.skip("No PDF fixture available")

        from contractos.api.deps import get_state
        state = get_state()
        doc_id = await _upload_document(client, sample_pdf)

        # Set up mock LLM response for the query
        mock_llm = MockLLMProvider(responses=[_mock_qa_response()])
        state.llm = mock_llm

        # First query
        resp = await client.post("/query/ask", json={
            "question": "What are the termination clauses?",
            "document_id": doc_id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["session_id"] is not None
        assert data["session_id"].startswith("s-")

    async def test_followup_with_session_id_includes_history(self, client, sample_pdf) -> None:
        """When session_id is provided, prior Q&A is sent to the LLM as context."""
        if sample_pdf is None:
            pytest.skip("No PDF fixture available")

        from contractos.api.deps import get_state
        state = get_state()
        doc_id = await _upload_document(client, sample_pdf)

        # Set up mock with two responses
        mock_llm = MockLLMProvider(responses=[
            _mock_qa_response("Section 12 covers termination with 30 days notice."),
            _mock_qa_response("Yes, Section 5b is referenced. Confidentiality survives for 3 years."),
        ])
        state.llm = mock_llm

        # First query
        resp1 = await client.post("/query/ask", json={
            "question": "What are the termination clauses?",
            "document_id": doc_id,
        })
        assert resp1.status_code == 200
        session_id = resp1.json()["session_id"]

        # Follow-up query WITH session_id
        resp2 = await client.post("/query/ask", json={
            "question": "Any reference to section 5b?",
            "document_id": doc_id,
            "session_id": session_id,
        })
        assert resp2.status_code == 200

        # The second LLM call should have received chat history
        assert len(mock_llm.call_log) == 2
        second_call_messages = mock_llm.call_log[1]["messages"]

        # Should have more than 1 message (prior context + current)
        assert len(second_call_messages) >= 3

        # Prior user question should be in the messages
        prior_user_content = second_call_messages[0]["content"]
        assert "termination" in prior_user_content.lower()

    async def test_query_without_session_id_has_no_history(self, client, sample_pdf) -> None:
        """When no session_id is provided, no chat history is sent (stateless)."""
        if sample_pdf is None:
            pytest.skip("No PDF fixture available")

        from contractos.api.deps import get_state
        state = get_state()
        doc_id = await _upload_document(client, sample_pdf)

        mock_llm = MockLLMProvider(responses=[
            _mock_qa_response("Termination in Section 12."),
            _mock_qa_response("Section 5b covers confidentiality."),
        ])
        state.llm = mock_llm

        # First query
        await client.post("/query/ask", json={
            "question": "What are the termination clauses?",
            "document_id": doc_id,
        })

        # Second query WITHOUT session_id — should be stateless
        resp2 = await client.post("/query/ask", json={
            "question": "Any reference to section 5b?",
            "document_id": doc_id,
        })
        assert resp2.status_code == 200

        # Second call should have only 1 user message (no history)
        second_call_messages = mock_llm.call_log[1]["messages"]
        assert len(second_call_messages) == 1

    async def test_session_id_enables_multi_turn_conversation(self, client, sample_pdf) -> None:
        """Multiple follow-ups with session_id accumulate conversation context."""
        if sample_pdf is None:
            pytest.skip("No PDF fixture available")

        from contractos.api.deps import get_state
        state = get_state()
        doc_id = await _upload_document(client, sample_pdf)

        mock_llm = MockLLMProvider(responses=[
            _mock_qa_response("Section 12 covers termination."),
            _mock_qa_response("Section 5b covers confidentiality."),
            _mock_qa_response("Payment terms are Net 30 in Section 3."),
        ])
        state.llm = mock_llm

        # Turn 1
        resp1 = await client.post("/query/ask", json={
            "question": "What are the termination clauses?",
            "document_id": doc_id,
        })
        session_id_1 = resp1.json()["session_id"]

        # Turn 2 — with session_id from turn 1
        resp2 = await client.post("/query/ask", json={
            "question": "Any reference to section 5b?",
            "document_id": doc_id,
            "session_id": session_id_1,
        })
        session_id_2 = resp2.json()["session_id"]

        # Turn 3 — with session_id from turn 2 (should have 2 prior turns)
        resp3 = await client.post("/query/ask", json={
            "question": "What about payment terms?",
            "document_id": doc_id,
            "session_id": session_id_2,
        })
        assert resp3.status_code == 200

        # Third call should have accumulated history (2 prior turns = 4 messages + 1 current)
        third_call_messages = mock_llm.call_log[2]["messages"]
        assert len(third_call_messages) >= 5  # 2 prior user + 2 prior assistant + 1 current
