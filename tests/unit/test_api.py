"""Unit tests for the ContractOS API — health, config, contracts, query endpoints."""

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
    """Config that uses in-memory SQLite and mock LLM."""
    return ContractOSConfig(
        llm=LLMConfig(provider="mock"),
        storage=StorageConfig(path=":memory:"),
    )


@pytest.fixture
async def client(test_config: ContractOSConfig):
    """Async test client with the app fully initialised."""
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
        assert data["version"] == "0.1.0"


# ── Config ─────────────────────────────────────────────────────────


class TestConfigEndpoint:
    @pytest.mark.asyncio
    async def test_config_returns_provider(self, client: AsyncClient) -> None:
        resp = await client.get("/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_provider"] == "mock"
        assert "llm_model" in data
        assert data["storage_backend"] == "sqlite"
        assert data["version"] == "0.1.0"

    @pytest.mark.asyncio
    async def test_config_no_api_key_exposed(self, client: AsyncClient) -> None:
        resp = await client.get("/config")
        data = resp.json()
        # Ensure no sensitive fields leak
        assert "api_key" not in data
        assert "ANTHROPIC_API_KEY" not in str(data)


# ── Contract Upload ────────────────────────────────────────────────


class TestContractUpload:
    @pytest.mark.asyncio
    async def test_upload_docx_with_extraction(self, client: AsyncClient) -> None:
        """Upload a real docx fixture and verify extraction runs."""
        docx_path = FIXTURES_DIR / "simple_procurement.docx"
        if not docx_path.exists():
            pytest.skip("Test fixture not found")

        content = docx_path.read_bytes()
        resp = await client.post(
            "/contracts/upload",
            files={"file": ("simple_procurement.docx", io.BytesIO(content), "application/octet-stream")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["document_id"].startswith("doc-")
        assert data["title"] == "simple_procurement"
        assert data["file_format"] == "docx"
        assert data["fact_count"] > 0, "Extraction should produce facts"
        assert data["status"] == "indexed"

    @pytest.mark.asyncio
    async def test_upload_pdf_with_extraction(self, client: AsyncClient) -> None:
        """Upload a real pdf fixture and verify extraction runs."""
        pdf_path = FIXTURES_DIR / "simple_nda.pdf"
        if not pdf_path.exists():
            pytest.skip("Test fixture not found")

        content = pdf_path.read_bytes()
        resp = await client.post(
            "/contracts/upload",
            files={"file": ("simple_nda.pdf", io.BytesIO(content), "application/pdf")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_format"] == "pdf"
        assert data["fact_count"] > 0, "Extraction should produce facts"

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
        docx_path = FIXTURES_DIR / "simple_procurement.docx"
        if not docx_path.exists():
            pytest.skip("Test fixture not found")

        content = docx_path.read_bytes()
        upload_resp = await client.post(
            "/contracts/upload",
            files={"file": ("msa.docx", io.BytesIO(content), "application/octet-stream")},
        )
        doc_id = upload_resp.json()["document_id"]

        resp = await client.get(f"/contracts/{doc_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["document_id"] == doc_id
        assert data["fact_count"] > 0
        assert data["clause_count"] >= 0
        assert data["binding_count"] >= 0

    @pytest.mark.asyncio
    async def test_get_nonexistent_contract_404(self, client: AsyncClient) -> None:
        resp = await client.get("/contracts/no-such-doc")
        assert resp.status_code == 404


# ── Facts Endpoint ─────────────────────────────────────────────────


class TestFactsEndpoint:
    @pytest.mark.asyncio
    async def test_get_facts_for_document(self, client: AsyncClient) -> None:
        docx_path = FIXTURES_DIR / "simple_procurement.docx"
        if not docx_path.exists():
            pytest.skip("Test fixture not found")

        content = docx_path.read_bytes()
        upload_resp = await client.post(
            "/contracts/upload",
            files={"file": ("test.docx", io.BytesIO(content), "application/octet-stream")},
        )
        doc_id = upload_resp.json()["document_id"]

        resp = await client.get(f"/contracts/{doc_id}/facts")
        assert resp.status_code == 200
        facts = resp.json()
        assert len(facts) > 0
        assert "fact_id" in facts[0]
        assert "value" in facts[0]
        assert "location_hint" in facts[0]

    @pytest.mark.asyncio
    async def test_get_facts_nonexistent_404(self, client: AsyncClient) -> None:
        resp = await client.get("/contracts/no-such/facts")
        assert resp.status_code == 404


# ── Clauses Endpoint ───────────────────────────────────────────────


class TestClausesEndpoint:
    @pytest.mark.asyncio
    async def test_get_clauses_for_document(self, client: AsyncClient) -> None:
        docx_path = FIXTURES_DIR / "simple_procurement.docx"
        if not docx_path.exists():
            pytest.skip("Test fixture not found")

        content = docx_path.read_bytes()
        upload_resp = await client.post(
            "/contracts/upload",
            files={"file": ("test.docx", io.BytesIO(content), "application/octet-stream")},
        )
        doc_id = upload_resp.json()["document_id"]

        resp = await client.get(f"/contracts/{doc_id}/clauses")
        assert resp.status_code == 200
        clauses = resp.json()
        assert isinstance(clauses, list)
        if clauses:
            assert "clause_id" in clauses[0]
            assert "clause_type" in clauses[0]
            assert "heading" in clauses[0]


# ── Bindings Endpoint ──────────────────────────────────────────────


class TestBindingsEndpoint:
    @pytest.mark.asyncio
    async def test_get_bindings_for_document(self, client: AsyncClient) -> None:
        docx_path = FIXTURES_DIR / "simple_procurement.docx"
        if not docx_path.exists():
            pytest.skip("Test fixture not found")

        content = docx_path.read_bytes()
        upload_resp = await client.post(
            "/contracts/upload",
            files={"file": ("test.docx", io.BytesIO(content), "application/octet-stream")},
        )
        doc_id = upload_resp.json()["document_id"]

        resp = await client.get(f"/contracts/{doc_id}/bindings")
        assert resp.status_code == 200
        bindings = resp.json()
        assert isinstance(bindings, list)


# ── Clause Gaps Endpoint ───────────────────────────────────────────


class TestClauseGapsEndpoint:
    @pytest.mark.asyncio
    async def test_get_gaps_for_document(self, client: AsyncClient) -> None:
        docx_path = FIXTURES_DIR / "simple_procurement.docx"
        if not docx_path.exists():
            pytest.skip("Test fixture not found")

        content = docx_path.read_bytes()
        upload_resp = await client.post(
            "/contracts/upload",
            files={"file": ("test.docx", io.BytesIO(content), "application/octet-stream")},
        )
        doc_id = upload_resp.json()["document_id"]

        resp = await client.get(f"/contracts/{doc_id}/clauses/gaps")
        assert resp.status_code == 200
        gaps = resp.json()
        assert isinstance(gaps, list)


# ── Query Endpoint ─────────────────────────────────────────────────


class TestQueryEndpoint:
    @pytest.mark.asyncio
    async def test_ask_returns_answer_with_provenance(self, client: AsyncClient) -> None:
        docx_path = FIXTURES_DIR / "simple_procurement.docx"
        if not docx_path.exists():
            pytest.skip("Test fixture not found")

        content = docx_path.read_bytes()
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
        # Should have confidence display
        assert data["confidence"] is not None
        assert "label" in data["confidence"]
        assert "color" in data["confidence"]
        # Should have provenance
        assert data["provenance"] is not None
        assert data["provenance"]["node_count"] >= 1

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
