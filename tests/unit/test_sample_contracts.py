"""Unit tests for sample contracts listing (T191–T193).

TDD: Tests written BEFORE implementation.

Verifies that the /contracts/samples endpoint correctly reads the
manifest.json and returns structured sample contract metadata, and
that POST /contracts/samples/{filename}/load uploads a sample contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from contractos.api.app import create_app
from contractos.api.deps import init_state, shutdown_state
from contractos.config import ContractOSConfig, LLMConfig, StorageConfig

SAMPLES_DIR = Path(__file__).parent.parent.parent / "demo" / "samples"


@pytest.fixture
def test_config() -> ContractOSConfig:
    return ContractOSConfig(
        storage=StorageConfig(database_path=":memory:"),
        llm=LLMConfig(provider="mock"),
    )


@pytest.fixture
async def client(test_config: ContractOSConfig):
    state = init_state(test_config)
    app = create_app(test_config)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    shutdown_state()


class TestSampleContractsEndpoint:
    """T191: GET /contracts/samples returns sample contract metadata."""

    @pytest.mark.asyncio
    async def test_samples_returns_list(self, client) -> None:
        """Endpoint returns a list of sample contracts."""
        resp = await client.get("/contracts/samples")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # At least simple_nda.pdf and one other

    @pytest.mark.asyncio
    async def test_samples_have_required_fields(self, client) -> None:
        """Each sample has filename, title, description, format, complexity."""
        resp = await client.get("/contracts/samples")
        data = resp.json()
        for sample in data:
            assert "filename" in sample
            assert "title" in sample
            assert "description" in sample
            assert "format" in sample
            assert sample["format"] in ("pdf", "docx")
            assert "complexity" in sample
            assert sample["complexity"] in ("simple", "complex")

    @pytest.mark.asyncio
    async def test_samples_include_both_formats(self, client) -> None:
        """Samples include both PDF and DOCX files."""
        resp = await client.get("/contracts/samples")
        data = resp.json()
        formats = {s["format"] for s in data}
        assert "pdf" in formats
        assert "docx" in formats


class TestSampleContractLoad:
    """T192: POST /contracts/samples/{filename}/load uploads a sample."""

    @pytest.mark.asyncio
    async def test_load_sample_returns_contract(self, client) -> None:
        """Loading a sample contract returns a ContractResponse with document_id."""
        resp = await client.post("/contracts/samples/simple_nda.pdf/load")
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "document_id" in data
        assert data["document_id"].startswith("doc-")
        assert data["title"] == "simple_nda"

    @pytest.mark.asyncio
    async def test_load_nonexistent_sample_returns_404(self, client) -> None:
        """Loading a non-existent sample returns 404."""
        resp = await client.post("/contracts/samples/nonexistent.pdf/load")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_load_sample_docx(self, client) -> None:
        """Loading a DOCX sample works."""
        resp = await client.post("/contracts/samples/simple_procurement.docx/load")
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "document_id" in data
        assert data["fact_count"] >= 0

    @pytest.mark.asyncio
    async def test_loaded_sample_queryable(self, client) -> None:
        """A loaded sample can be queried via /query/ask."""
        from contractos.api.deps import get_state
        from contractos.llm.provider import MockLLMProvider

        # Load a sample
        resp = await client.post("/contracts/samples/simple_nda.pdf/load")
        assert resp.status_code in (200, 201)
        doc_id = resp.json()["document_id"]

        # Set up mock LLM for query
        state = get_state()
        mock_llm = MockLLMProvider(responses=[json.dumps({
            "answer": "The parties are Gamma Inc and Delta LLC.",
            "answer_type": "fact",
            "confidence": 0.9,
            "facts_referenced": [],
            "reasoning_chain": "Found in section 1.",
        })])
        state.llm = mock_llm

        # Query the loaded sample
        resp2 = await client.post("/query/ask", json={
            "question": "Who are the parties?",
            "document_id": doc_id,
        })
        assert resp2.status_code == 200
        assert "answer" in resp2.json()
