"""Integration tests for the Copilot document viewer page.

Verifies that the copilot.html page is served and the API endpoints
it depends on work correctly for the Copilot workflow:
1. Upload document → 2. View extraction summary → 3. Ask questions
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from contractos.api.app import create_app
from contractos.api.deps import init_state, shutdown_state
from contractos.config import ContractOSConfig, LLMConfig, StorageConfig

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def test_config() -> ContractOSConfig:
    return ContractOSConfig(
        llm=LLMConfig(provider="mock"),
        storage=StorageConfig(path=":memory:"),
    )


@pytest.fixture
async def client(test_config: ContractOSConfig):
    init_state(test_config)
    app = create_app(test_config)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    shutdown_state()


class TestCopilotPageServing:
    """Verify the Copilot page is served correctly."""

    async def test_copilot_page_served(self, client: AsyncClient) -> None:
        """The copilot.html page should be accessible at /demo/copilot.html."""
        resp = await client.get("/demo/copilot.html")
        assert resp.status_code == 200
        assert "ContractOS" in resp.text
        assert "Copilot" in resp.text

    async def test_copilot_page_has_pdf_js(self, client: AsyncClient) -> None:
        """Copilot page should include PDF.js for PDF rendering."""
        resp = await client.get("/demo/copilot.html")
        assert "pdf.min.mjs" in resp.text or "pdf.js" in resp.text

    async def test_copilot_page_has_docx_preview(self, client: AsyncClient) -> None:
        """Copilot page should include docx-preview for DOCX rendering."""
        resp = await client.get("/demo/copilot.html")
        assert "docx-preview" in resp.text


class TestCopilotWorkflow:
    """Test the full Copilot workflow: upload → extract → query."""

    async def test_upload_and_query_docx(self, client: AsyncClient) -> None:
        """Upload a DOCX and ask a question via the Copilot workflow."""
        path = FIXTURES_DIR / "simple_procurement.docx"
        if not path.exists():
            pytest.skip("simple_procurement.docx not found")

        # Step 1: Upload
        with open(path, "rb") as f:
            resp = await client.post(
                "/contracts/upload",
                files={"file": ("simple_procurement.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )
        assert resp.status_code == 201
        data = resp.json()
        doc_id = data["document_id"]
        assert data["fact_count"] > 0

        # Step 2: Query
        resp = await client.post(
            "/query/ask",
            json={"question": "Who are the parties?", "document_id": doc_id},
        )
        assert resp.status_code == 200
        result = resp.json()
        assert result["answer"]
        assert result["session_id"]

    async def test_upload_and_query_pdf(self, client: AsyncClient) -> None:
        """Upload a PDF and ask a question via the Copilot workflow."""
        path = FIXTURES_DIR / "simple_nda.pdf"
        if not path.exists():
            pytest.skip("simple_nda.pdf not found")

        with open(path, "rb") as f:
            resp = await client.post(
                "/contracts/upload",
                files={"file": ("simple_nda.pdf", f, "application/pdf")},
            )
        assert resp.status_code == 201
        doc_id = resp.json()["document_id"]

        resp = await client.post(
            "/query/ask",
            json={"question": "What is the effective date?", "document_id": doc_id},
        )
        assert resp.status_code == 200
        assert resp.json()["answer"]

    async def test_copilot_quick_actions_workflow(self, client: AsyncClient) -> None:
        """Simulate the quick action buttons in the Copilot sidebar."""
        path = FIXTURES_DIR / "simple_procurement.docx"
        if not path.exists():
            pytest.skip("simple_procurement.docx not found")

        with open(path, "rb") as f:
            resp = await client.post(
                "/contracts/upload",
                files={"file": ("simple_procurement.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )
        doc_id = resp.json()["document_id"]

        # Simulate quick action buttons
        quick_questions = [
            "Who are the parties to this agreement?",
            "What are the payment terms?",
            "What are the key dates?",
        ]
        for q in quick_questions:
            resp = await client.post(
                "/query/ask",
                json={"question": q, "document_id": doc_id},
            )
            assert resp.status_code == 200
            assert resp.json()["answer"]

        # Verify all appear in history
        resp = await client.get("/query/history")
        history = resp.json()
        assert len(history) >= 3

    async def test_extraction_summary_data(self, client: AsyncClient) -> None:
        """Upload response should contain all data needed for the extraction summary."""
        path = FIXTURES_DIR / "simple_procurement.docx"
        if not path.exists():
            pytest.skip("simple_procurement.docx not found")

        with open(path, "rb") as f:
            resp = await client.post(
                "/contracts/upload",
                files={"file": ("simple_procurement.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )
        data = resp.json()

        # All fields needed by the Copilot extraction summary
        assert "document_id" in data
        assert "title" in data
        assert "fact_count" in data
        assert "clause_count" in data
        assert "binding_count" in data
        assert "word_count" in data
        assert "status" in data
        assert data["status"] == "indexed"


class TestCopilotWithRealNDAs:
    """Test Copilot workflow with real ContractNLI documents."""

    async def test_copilot_with_bosch_nda(self, client: AsyncClient) -> None:
        """Copilot workflow with real Bosch NDA."""
        path = FIXTURES_DIR / "contractnli_docs" / "01_Bosch-Automotive-Service-Solutions-Mutual-Non-Disclosure-Agreement-7-12-17.docx"
        if not path.exists():
            pytest.skip("Bosch NDA not found")

        with open(path, "rb") as f:
            resp = await client.post(
                "/contracts/upload",
                files={"file": (path.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )
        assert resp.status_code == 201
        doc_id = resp.json()["document_id"]

        # Ask a confidentiality question
        resp = await client.post(
            "/query/ask",
            json={"question": "What types of information are considered confidential?", "document_id": doc_id},
        )
        assert resp.status_code == 200
        assert resp.json()["answer"]

    async def test_copilot_with_ceii_nda(self, client: AsyncClient) -> None:
        """Copilot workflow with real CEII NDA."""
        path = FIXTURES_DIR / "contractnli_docs" / "ceii-and-nda.docx"
        if not path.exists():
            pytest.skip("CEII NDA not found")

        with open(path, "rb") as f:
            resp = await client.post(
                "/contracts/upload",
                files={"file": (path.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )
        assert resp.status_code == 201
        doc_id = resp.json()["document_id"]

        resp = await client.post(
            "/query/ask",
            json={"question": "What must a party do if legally compelled to disclose?", "document_id": doc_id},
        )
        assert resp.status_code == 200
        assert resp.json()["answer"]
