"""Unit tests for the ContractOS API shell — health, contracts, query endpoints."""

from __future__ import annotations

import io

import pytest
from httpx import ASGITransport, AsyncClient

from contractos.api.app import create_app
from contractos.api.deps import init_state, shutdown_state
from contractos.config import ContractOSConfig, LLMConfig, StorageConfig


@pytest.fixture
def test_config() -> ContractOSConfig:
    """Config that uses in-memory SQLite and mock LLM."""
    return ContractOSConfig(
        llm=LLMConfig(provider="mock"),
        storage=StorageConfig(path=":memory:"),
    )


@pytest.fixture
async def client(test_config: ContractOSConfig):
    """Async test client with the app fully initialised."""
    # Manually init state so it's available before the first request
    init_state(test_config)
    app = create_app(test_config)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    shutdown_state()


# ── Health ─────────────────────────────────────────────────────────


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "contractos"


# ── Contract Upload ────────────────────────────────────────────────


class TestContractUpload:
    @pytest.mark.asyncio
    async def test_upload_docx(self, client: AsyncClient) -> None:
        content = b"PK\x03\x04fake docx content"
        resp = await client.post(
            "/contracts/upload",
            files={"file": ("test_contract.docx", io.BytesIO(content), "application/octet-stream")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["document_id"].startswith("doc-")
        assert data["title"] == "test_contract"
        assert data["file_format"] == "docx"

    @pytest.mark.asyncio
    async def test_upload_pdf(self, client: AsyncClient) -> None:
        content = b"%PDF-1.4 fake pdf content"
        resp = await client.post(
            "/contracts/upload",
            files={"file": ("agreement.pdf", io.BytesIO(content), "application/pdf")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_format"] == "pdf"

    @pytest.mark.asyncio
    async def test_upload_unsupported_format_rejected(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/contracts/upload",
            files={"file": ("readme.txt", io.BytesIO(b"text"), "text/plain")},
        )
        assert resp.status_code == 400
        assert "Unsupported format" in resp.json()["detail"]


# ── Contract Retrieval ─────────────────────────────────────────────


class TestContractRetrieval:
    @pytest.mark.asyncio
    async def test_get_uploaded_contract(self, client: AsyncClient) -> None:
        # Upload first
        content = b"PK\x03\x04fake docx"
        upload_resp = await client.post(
            "/contracts/upload",
            files={"file": ("msa.docx", io.BytesIO(content), "application/octet-stream")},
        )
        doc_id = upload_resp.json()["document_id"]

        # Retrieve
        resp = await client.get(f"/contracts/{doc_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["document_id"] == doc_id
        assert data["title"] == "msa"
        assert data["fact_count"] == 0

    @pytest.mark.asyncio
    async def test_get_nonexistent_contract_404(self, client: AsyncClient) -> None:
        resp = await client.get("/contracts/no-such-doc")
        assert resp.status_code == 404


# ── Query Endpoint (Phase 2 Stub) ─────────────────────────────────


class TestQueryEndpoint:
    @pytest.mark.asyncio
    async def test_ask_returns_answer(self, client: AsyncClient) -> None:
        # Upload a contract first
        content = b"PK\x03\x04fake"
        upload_resp = await client.post(
            "/contracts/upload",
            files={"file": ("test.docx", io.BytesIO(content), "application/octet-stream")},
        )
        doc_id = upload_resp.json()["document_id"]

        resp = await client.post(
            "/query/ask",
            json={"question": "What are the payment terms?", "document_id": doc_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["answer"]) > 0
        # No facts uploaded, so answer should indicate not found
        assert data["answer_type"] == "not_found"

    @pytest.mark.asyncio
    async def test_ask_nonexistent_contract_404(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/query/ask",
            json={"question": "What?", "document_id": "no-such"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_ask_empty_question_rejected(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/query/ask",
            json={"question": "", "document_id": "doc-001"},
        )
        assert resp.status_code == 422  # Pydantic validation
