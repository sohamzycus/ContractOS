"""Integration tests for multi-document analysis with real HuggingFace-sourced contracts.

Uses 3 realistic procurement contracts:
- Master Services Agreement (GlobalTech ↔ Meridian)
- Software License Agreement (CloudVault ↔ Pacific Rim)
- Supply Chain Agreement (Apex ↔ NovaTech)

Tests cross-contract querying, chat history, and clear operations.
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


async def _upload(client: AsyncClient, filename: str) -> str:
    """Upload a fixture file and return its document_id."""
    path = FIXTURES_DIR / filename
    assert path.exists(), f"Fixture not found: {path}"
    with open(path, "rb") as f:
        resp = await client.post(
            "/contracts/upload",
            files={"file": (filename, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
    assert resp.status_code == 201, f"Upload failed: {resp.text}"
    return resp.json()["document_id"]


class TestMultiDocumentAnalysis:
    """Test querying across multiple real contract documents."""

    async def test_upload_three_contracts(self, client: AsyncClient) -> None:
        """All three HuggingFace contracts should upload and index successfully."""
        doc1 = await _upload(client, "hf_master_services_agreement.docx")
        doc2 = await _upload(client, "hf_software_license_agreement.docx")
        doc3 = await _upload(client, "hf_supply_chain_agreement.docx")

        # All should be listed
        resp = await client.get("/contracts")
        contracts = resp.json()
        assert len(contracts) == 3
        doc_ids = {c["document_id"] for c in contracts}
        assert doc1 in doc_ids
        assert doc2 in doc_ids
        assert doc3 in doc_ids

    async def test_single_doc_query_msa(self, client: AsyncClient) -> None:
        """Query the MSA for payment terms."""
        doc_id = await _upload(client, "hf_master_services_agreement.docx")
        resp = await client.post(
            "/query/ask",
            json={"question": "What are the payment terms?", "document_id": doc_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"]
        assert len(data["document_ids"]) == 1

    async def test_multi_doc_query_across_two(self, client: AsyncClient) -> None:
        """Query across MSA and Software License for termination clauses."""
        doc1 = await _upload(client, "hf_master_services_agreement.docx")
        doc2 = await _upload(client, "hf_software_license_agreement.docx")

        resp = await client.post(
            "/query/ask",
            json={
                "question": "Compare the termination conditions across these contracts",
                "document_ids": [doc1, doc2],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"]
        assert len(data["document_ids"]) == 2
        assert data["session_id"]

    async def test_multi_doc_query_across_three(self, client: AsyncClient) -> None:
        """Query all three contracts for liability caps."""
        doc1 = await _upload(client, "hf_master_services_agreement.docx")
        doc2 = await _upload(client, "hf_software_license_agreement.docx")
        doc3 = await _upload(client, "hf_supply_chain_agreement.docx")

        resp = await client.post(
            "/query/ask",
            json={
                "question": "What is the limitation of liability in each contract?",
                "document_ids": [doc1, doc2, doc3],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"]
        assert len(data["document_ids"]) == 3

    async def test_chat_history_after_multi_doc(self, client: AsyncClient) -> None:
        """Chat history should record multi-doc queries correctly."""
        doc1 = await _upload(client, "hf_master_services_agreement.docx")
        doc2 = await _upload(client, "hf_supply_chain_agreement.docx")

        await client.post(
            "/query/ask",
            json={
                "question": "What are the insurance requirements?",
                "document_ids": [doc1, doc2],
            },
        )

        resp = await client.get("/query/history")
        history = resp.json()
        assert len(history) >= 1
        latest = history[0]
        assert latest["question"] == "What are the insurance requirements?"
        assert len(latest["document_ids"]) == 2

    async def test_clear_contracts_and_history(self, client: AsyncClient) -> None:
        """Clear all should remove contracts and history."""
        await _upload(client, "hf_master_services_agreement.docx")
        await _upload(client, "hf_software_license_agreement.docx")

        # Ask a question
        resp = await client.get("/contracts")
        assert len(resp.json()) == 2

        # Clear all
        resp = await client.delete("/contracts/clear")
        assert resp.status_code == 200
        assert resp.json()["cleared_contracts"] == 2

        # Verify empty
        resp = await client.get("/contracts")
        assert resp.json() == []

        # Clear history
        resp = await client.delete("/query/history")
        assert resp.status_code == 200

    async def test_contract_metadata_richness(self, client: AsyncClient) -> None:
        """HuggingFace contracts should produce rich extraction results."""
        doc_id = await _upload(client, "hf_master_services_agreement.docx")
        resp = await client.get(f"/contracts/{doc_id}")
        data = resp.json()

        # MSA should have substantial extraction
        assert data["fact_count"] > 20, f"Expected >20 facts, got {data['fact_count']}"
        assert data["clause_count"] > 5, f"Expected >5 clauses, got {data['clause_count']}"
        assert data["binding_count"] > 3, f"Expected >3 bindings, got {data['binding_count']}"
        assert data["word_count"] > 1000
