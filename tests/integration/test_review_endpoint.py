"""Integration tests for POST /contracts/{id}/review endpoint — T209.

TDD Red: Write tests FIRST, verify they FAIL, then implement endpoint.
Uses httpx.AsyncClient with ASGITransport to avoid SQLite threading issues.
"""

from __future__ import annotations

import json
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
    """Path to a sample PDF for testing."""
    path = Path(__file__).resolve().parent.parent.parent / "demo" / "samples" / "simple_nda.pdf"
    if not path.exists():
        pytest.skip("Sample PDF not found")
    return path


class TestReviewEndpoint:
    """Test POST /contracts/{document_id}/review."""

    @pytest.mark.asyncio
    async def test_review_returns_200(self, client, sample_pdf_path):
        """Upload a contract and review it — should return 200 with ReviewResult."""
        # Upload first
        with open(sample_pdf_path, "rb") as f:
            upload_resp = await client.post(
                "/contracts/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        assert upload_resp.status_code == 201
        doc_id = upload_resp.json()["document_id"]

        # Review
        review_resp = await client.post(
            f"/contracts/{doc_id}/review",
            json={},
        )
        assert review_resp.status_code == 200
        data = review_resp.json()
        assert "findings" in data
        assert "summary" in data
        assert "document_id" in data
        assert data["document_id"] == doc_id

    @pytest.mark.asyncio
    async def test_review_has_risk_profile(self, client, sample_pdf_path):
        """Review response includes risk_profile."""
        with open(sample_pdf_path, "rb") as f:
            upload_resp = await client.post(
                "/contracts/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        doc_id = upload_resp.json()["document_id"]

        review_resp = await client.post(
            f"/contracts/{doc_id}/review",
            json={},
        )
        assert review_resp.status_code == 200
        data = review_resp.json()
        assert "risk_profile" in data

    @pytest.mark.asyncio
    async def test_review_nonexistent_document(self, client):
        """Review of nonexistent document returns 404."""
        resp = await client.post(
            "/contracts/nonexistent-doc-id/review",
            json={},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_review_with_custom_playbook_params(self, client, sample_pdf_path):
        """Review with custom parameters."""
        with open(sample_pdf_path, "rb") as f:
            upload_resp = await client.post(
                "/contracts/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        doc_id = upload_resp.json()["document_id"]

        review_resp = await client.post(
            f"/contracts/{doc_id}/review",
            json={
                "user_side": "buyer",
                "generate_redlines": False,
            },
        )
        assert review_resp.status_code == 200
        data = review_resp.json()
        assert "findings" in data
