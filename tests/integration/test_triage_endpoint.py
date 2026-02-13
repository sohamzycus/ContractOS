"""Integration tests for POST /contracts/{id}/triage endpoint — T225.

Uses httpx.AsyncClient with ASGITransport.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import httpx
from httpx import ASGITransport

from contractos.api.app import create_app
from contractos.api.deps import init_state, shutdown_state
from contractos.config import ContractOSConfig, LLMConfig, StorageConfig


@pytest.fixture
def test_config() -> ContractOSConfig:
    """Config using in-memory DB and mock LLM."""
    return ContractOSConfig(
        llm=LLMConfig(provider="mock"),
        storage=StorageConfig(path=":memory:"),
    )


@pytest.fixture
async def client(test_config):
    """Create an async HTTP client for testing with proper AppState init."""
    init_state(test_config)
    app = create_app(test_config)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    shutdown_state()


@pytest.fixture
def sample_pdf_path():
    path = Path(__file__).resolve().parent.parent.parent / "demo" / "samples" / "simple_nda.pdf"
    if not path.exists():
        pytest.skip("Sample PDF not found")
    return path


class TestTriageEndpoint:

    @pytest.mark.asyncio
    async def test_triage_returns_200(self, client, sample_pdf_path):
        """Upload an NDA and triage it."""
        with open(sample_pdf_path, "rb") as f:
            upload_resp = await client.post(
                "/contracts/upload",
                files={"file": ("nda.pdf", f, "application/pdf")},
            )
        assert upload_resp.status_code == 201
        doc_id = upload_resp.json()["document_id"]

        triage_resp = await client.post(
            f"/contracts/{doc_id}/triage",
            json={},
        )
        assert triage_resp.status_code == 200
        data = triage_resp.json()
        assert "classification" in data
        assert "checklist_results" in data
        assert data["document_id"] == doc_id

    @pytest.mark.asyncio
    async def test_triage_nonexistent_document(self, client):
        resp = await client.post(
            "/contracts/nonexistent-doc/triage",
            json={},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_triage_has_classification(self, client, sample_pdf_path):
        with open(sample_pdf_path, "rb") as f:
            upload_resp = await client.post(
                "/contracts/upload",
                files={"file": ("nda.pdf", f, "application/pdf")},
            )
        doc_id = upload_resp.json()["document_id"]

        triage_resp = await client.post(
            f"/contracts/{doc_id}/triage",
            json={},
        )
        assert triage_resp.status_code == 200
        data = triage_resp.json()
        classification = data["classification"]
        assert classification["level"] in ("green", "yellow", "red")
        assert classification["routing"] != ""
        assert classification["timeline"] != ""
