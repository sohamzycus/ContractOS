"""Integration tests for the hidden fact discovery endpoint."""

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


@pytest.fixture
def test_config() -> ContractOSConfig:
    return ContractOSConfig(
        llm=LLMConfig(provider="mock"),
        storage=StorageConfig(path=":memory:"),
    )


@pytest.fixture
async def client(test_config: ContractOSConfig):
    state = init_state(test_config)
    app = create_app(test_config)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    shutdown_state()


@pytest.fixture
def sample_docx():
    """Path to a test DOCX fixture."""
    docx_files = list(FIXTURES_DIR.glob("*.docx"))
    if docx_files:
        return docx_files[0]
    return None


class TestDiscoveryEndpoint:
    """Tests for POST /contracts/{document_id}/discover."""

    @pytest.mark.asyncio
    async def test_discover_returns_404_for_missing_doc(self, client):
        """Discovery should return 404 for non-existent document."""
        r = await client.post("/contracts/doc-nonexistent/discover")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_discover_endpoint_works(self, client, sample_docx, test_config):
        """Discovery endpoint should return structured facts after upload."""
        if sample_docx is None:
            pytest.skip("No DOCX fixture available")

        # Get the mock LLM from the state
        from contractos.api.deps import get_state
        state = get_state()
        mock_llm = state.llm
        assert isinstance(mock_llm, MockLLMProvider)

        # Upload a document
        with open(sample_docx, "rb") as f:
            r = await client.post(
                "/contracts/upload",
                files={"file": (sample_docx.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )
        assert r.status_code == 201
        doc_id = r.json()["document_id"]

        # Add mock discovery response
        mock_llm.add_response(json.dumps({
            "discovered_facts": [
                {
                    "type": "hidden_risk",
                    "claim": "No force majeure clause exists",
                    "evidence": "The agreement lacks force majeure provisions",
                    "risk_level": "high",
                    "explanation": "Parties cannot excuse performance due to extraordinary events",
                },
                {
                    "type": "implicit_obligation",
                    "claim": "Buyer must maintain records of all transactions",
                    "evidence": "Payment terms imply record-keeping",
                    "risk_level": "medium",
                    "explanation": "Net payment terms require tracking of invoices",
                },
            ],
            "summary": "Found 2 hidden facts beyond pattern extraction",
            "categories_found": "hidden_risk, implicit_obligation",
        }))

        # Run discovery
        r = await client.post(f"/contracts/{doc_id}/discover")
        assert r.status_code == 200

        data = r.json()
        assert data["count"] == 2
        assert len(data["discovered_facts"]) == 2
        assert data["discovered_facts"][0]["type"] == "hidden_risk"
        assert data["discovered_facts"][0]["risk_level"] == "high"
        assert data["discovered_facts"][1]["type"] == "implicit_obligation"
        assert data["summary"] != ""
        assert data["categories_found"] != ""
        assert data["discovery_time_ms"] >= 0
        assert data["confidence"] is not None

    @pytest.mark.asyncio
    async def test_discover_with_empty_results(self, client, sample_docx, test_config):
        """Discovery should handle LLM returning no hidden facts."""
        if sample_docx is None:
            pytest.skip("No DOCX fixture available")

        from contractos.api.deps import get_state
        state = get_state()
        mock_llm = state.llm
        assert isinstance(mock_llm, MockLLMProvider)

        with open(sample_docx, "rb") as f:
            r = await client.post(
                "/contracts/upload",
                files={"file": (sample_docx.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )
        assert r.status_code == 201
        doc_id = r.json()["document_id"]

        mock_llm.add_response(json.dumps({
            "discovered_facts": [],
            "summary": "No hidden facts found — contract is well-structured",
            "categories_found": "",
        }))

        r = await client.post(f"/contracts/{doc_id}/discover")
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 0
        assert len(data["discovered_facts"]) == 0

    @pytest.mark.asyncio
    async def test_copilot_page_has_discover_button(self, client):
        """The copilot page should include the Discover Hidden Facts button."""
        r = await client.get("/demo/copilot.html")
        assert r.status_code == 200
        html = r.text
        assert "Discover Hidden Facts" in html
        assert "discoverHiddenFacts" in html
        assert "discovered-section" in html
