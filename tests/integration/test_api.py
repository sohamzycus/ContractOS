"""Integration tests for the ContractOS REST API — full pipeline."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from contractos.api.app import create_app
from contractos.api.deps import init_state, shutdown_state
from contractos.config import ContractOSConfig, LLMConfig, StorageConfig

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def test_config() -> ContractOSConfig:
    """Config using in-memory DB and mock LLM."""
    return ContractOSConfig(
        llm=LLMConfig(provider="mock"),
        storage=StorageConfig(path=":memory:"),
    )


@pytest.fixture
async def client(test_config: ContractOSConfig):
    init_state(test_config)
    app = create_app(test_config)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    shutdown_state()


# ── Health + Config ────────────────────────────────────────────────


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "contractos"

    @pytest.mark.asyncio
    async def test_config_returns_settings(self, client: AsyncClient) -> None:
        resp = await client.get("/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_provider"] == "mock"
        assert data["storage_backend"] == "sqlite"


# ── Full Upload + Extraction Pipeline ──────────────────────────────


class TestFullPipeline:
    @pytest.mark.asyncio
    async def test_upload_extract_query_pipeline(self, client: AsyncClient) -> None:
        """End-to-end: upload docx → extract facts → query → get answer with provenance."""
        docx_path = FIXTURES_DIR / "simple_procurement.docx"
        if not docx_path.exists():
            pytest.skip("Test fixture not found")

        content = docx_path.read_bytes()

        # Step 1: Upload
        upload_resp = await client.post(
            "/contracts/upload",
            files={"file": ("procurement.docx", io.BytesIO(content), "application/octet-stream")},
        )
        assert upload_resp.status_code == 201
        upload_data = upload_resp.json()
        doc_id = upload_data["document_id"]
        assert upload_data["fact_count"] > 0
        assert upload_data["status"] == "indexed"

        # Step 2: Verify facts stored
        facts_resp = await client.get(f"/contracts/{doc_id}/facts")
        assert facts_resp.status_code == 200
        facts = facts_resp.json()
        assert len(facts) > 0

        # Step 3: Verify clauses
        clauses_resp = await client.get(f"/contracts/{doc_id}/clauses")
        assert clauses_resp.status_code == 200

        # Step 4: Verify bindings
        bindings_resp = await client.get(f"/contracts/{doc_id}/bindings")
        assert bindings_resp.status_code == 200

        # Step 5: Verify gaps
        gaps_resp = await client.get(f"/contracts/{doc_id}/clauses/gaps")
        assert gaps_resp.status_code == 200

        # Step 6: Query
        query_resp = await client.post(
            "/query/ask",
            json={"question": "What are the payment terms?", "document_id": doc_id},
        )
        assert query_resp.status_code == 200
        query_data = query_resp.json()
        assert len(query_data["answer"]) > 0
        assert query_data["confidence"] is not None
        assert query_data["provenance"] is not None

    @pytest.mark.asyncio
    async def test_upload_pdf_extract_pipeline(self, client: AsyncClient) -> None:
        """Upload PDF → extract → verify facts."""
        pdf_path = FIXTURES_DIR / "simple_nda.pdf"
        if not pdf_path.exists():
            pytest.skip("Test fixture not found")

        content = pdf_path.read_bytes()
        upload_resp = await client.post(
            "/contracts/upload",
            files={"file": ("nda.pdf", io.BytesIO(content), "application/pdf")},
        )
        assert upload_resp.status_code == 201
        data = upload_resp.json()
        doc_id = data["document_id"]
        assert data["fact_count"] > 0

        # Verify retrieval
        get_resp = await client.get(f"/contracts/{doc_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["fact_count"] > 0


# ── Contract Upload ────────────────────────────────────────────────


class TestContractUpload:
    @pytest.mark.asyncio
    async def test_upload_unsupported_format(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/contracts/upload",
            files={"file": ("readme.txt", io.BytesIO(b"text"), "text/plain")},
        )
        assert resp.status_code == 400
        assert "Unsupported format" in resp.json()["detail"]


# ── Query ──────────────────────────────────────────────────────────


class TestQuery:
    @pytest.mark.asyncio
    async def test_ask_nonexistent_contract(self, client: AsyncClient) -> None:
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
        assert resp.status_code == 422
