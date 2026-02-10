"""Contract tests: LegalBench / CUAD documents through the full API.

Tests the complete workflow:
  1. Upload LegalBench NDA and CUAD License Agreement via API
  2. Verify extraction metadata (fact counts, clause counts)
  3. Query facts, clauses, bindings, gaps
  4. Verify TrustGraph visualization
  5. Run LegalBench-style Q&A queries

These tests require the server to be running (or use the TestClient).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from contractos.api.app import create_app
from contractos.api.deps import get_state, init_state, shutdown_state
from contractos.config import ContractOSConfig, StorageConfig

FIXTURES = Path(__file__).parent.parent / "fixtures"
LEGALBENCH_NDA = FIXTURES / "legalbench_nda.docx"
CUAD_LICENSE = FIXTURES / "cuad_license_agreement.docx"


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """Create a test client with isolated database."""
    db_path = tmp_path_factory.mktemp("legalbench_db") / "test.db"
    shutdown_state()
    config = ContractOSConfig(storage=StorageConfig(path=str(db_path)))
    init_state(config)
    app = create_app()
    with TestClient(app) as c:
        yield c
    shutdown_state()


@pytest.fixture(scope="module")
def nda_doc_id(client):
    """Upload the LegalBench NDA and return its document_id."""
    with open(LEGALBENCH_NDA, "rb") as f:
        resp = client.post("/contracts/upload", files={"file": ("legalbench_nda.docx", f)})
    assert resp.status_code == 201
    return resp.json()["document_id"]


@pytest.fixture(scope="module")
def cuad_doc_id(client):
    """Upload the CUAD License Agreement and return its document_id."""
    with open(CUAD_LICENSE, "rb") as f:
        resp = client.post("/contracts/upload", files={"file": ("cuad_license_agreement.docx", f)})
    assert resp.status_code == 201
    return resp.json()["document_id"]


# ─────────────────────────────────────────────────────────────────────
# LegalBench NDA — API Tests
# ─────────────────────────────────────────────────────────────────────

class TestLegalBenchNDAAPI:
    """API-level tests for the LegalBench NDA fixture."""

    def test_upload_returns_indexed(self, client, nda_doc_id):
        """Upload succeeds and returns indexed status."""
        resp = client.get(f"/contracts/{nda_doc_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "indexed"
        assert body["file_format"] == "docx"
        assert body["fact_count"] > 0
        assert body["clause_count"] > 0

    def test_facts_endpoint(self, client, nda_doc_id):
        """Facts endpoint returns extracted facts."""
        resp = client.get(f"/contracts/{nda_doc_id}/facts")
        assert resp.status_code == 200
        facts = resp.json()
        assert len(facts) > 0
        # Verify fact structure
        f = facts[0]
        assert "fact_id" in f
        assert "fact_type" in f
        assert "value" in f

    def test_entity_facts_filter(self, client, nda_doc_id):
        """Entity facts can be filtered by type."""
        resp = client.get(f"/contracts/{nda_doc_id}/facts?fact_type=entity")
        assert resp.status_code == 200
        facts = resp.json()
        for f in facts:
            assert f["fact_type"] == "entity"

    def test_clauses_endpoint(self, client, nda_doc_id):
        """Clauses endpoint returns classified clauses."""
        resp = client.get(f"/contracts/{nda_doc_id}/clauses")
        assert resp.status_code == 200
        clauses = resp.json()
        assert len(clauses) > 0
        clause_types = [c["clause_type"] for c in clauses]
        assert "confidentiality" in clause_types

    def test_bindings_endpoint(self, client, nda_doc_id):
        """Bindings endpoint returns resolved bindings."""
        resp = client.get(f"/contracts/{nda_doc_id}/bindings")
        assert resp.status_code == 200
        bindings = resp.json()
        assert isinstance(bindings, list)

    def test_gaps_endpoint(self, client, nda_doc_id):
        """Gaps endpoint returns missing mandatory facts."""
        resp = client.get(f"/contracts/{nda_doc_id}/clauses/gaps")
        assert resp.status_code == 200
        gaps = resp.json()
        assert isinstance(gaps, list)

    def test_graph_endpoint(self, client, nda_doc_id):
        """TrustGraph endpoint returns nodes and edges."""
        resp = client.get(f"/contracts/{nda_doc_id}/graph")
        assert resp.status_code == 200
        graph = resp.json()
        assert graph["document_id"] == nda_doc_id
        assert len(graph["nodes"]) > 0
        assert len(graph["edges"]) > 0
        # Contract node should be present
        node_types = {n["type"] for n in graph["nodes"]}
        assert "contract" in node_types
        assert "fact" in node_types

    def test_pagination(self, client, nda_doc_id):
        """Facts pagination works correctly."""
        resp1 = client.get(f"/contracts/{nda_doc_id}/facts?limit=3&offset=0")
        resp2 = client.get(f"/contracts/{nda_doc_id}/facts?limit=3&offset=3")
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        page1 = resp1.json()
        page2 = resp2.json()
        assert len(page1) <= 3
        if len(page1) == 3 and len(page2) > 0:
            # Pages should not overlap
            ids1 = {f["fact_id"] for f in page1}
            ids2 = {f["fact_id"] for f in page2}
            assert ids1.isdisjoint(ids2), "Paginated results should not overlap"


# ─────────────────────────────────────────────────────────────────────
# CUAD License Agreement — API Tests
# ─────────────────────────────────────────────────────────────────────

class TestCUADLicenseAPI:
    """API-level tests for the CUAD License Agreement fixture."""

    def test_upload_returns_indexed(self, client, cuad_doc_id):
        """Upload succeeds with rich extraction."""
        resp = client.get(f"/contracts/{cuad_doc_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "indexed"
        assert body["fact_count"] > 30, f"Expected >30 facts, got {body['fact_count']}"
        assert body["clause_count"] > 5, f"Expected >5 clauses, got {body['clause_count']}"

    def test_termination_clauses(self, client, cuad_doc_id):
        """Termination clauses are classified."""
        resp = client.get(f"/contracts/{cuad_doc_id}/clauses?clause_type=termination")
        assert resp.status_code == 200
        clauses = resp.json()
        assert len(clauses) > 0, "Should have termination clauses"

    def test_monetary_facts(self, client, cuad_doc_id):
        """Monetary facts extracted as text_span (EUR 2.4M, EUR 5M, etc.)."""
        resp = client.get(f"/contracts/{cuad_doc_id}/facts?fact_type=text_span")
        assert resp.status_code == 200
        facts = resp.json()
        monetary = [f for f in facts if "eur" in f["value"].lower() or "$" in f["value"]]
        assert len(monetary) >= 2, f"Expected ≥2 monetary text_span facts, got {len(monetary)}"

    def test_graph_richness(self, client, cuad_doc_id):
        """TrustGraph has rich structure for complex license agreement."""
        resp = client.get(f"/contracts/{cuad_doc_id}/graph")
        assert resp.status_code == 200
        graph = resp.json()
        assert len(graph["nodes"]) > 50, (
            f"Expected >50 nodes, got {len(graph['nodes'])}"
        )
        assert len(graph["edges"]) > 50, (
            f"Expected >50 edges, got {len(graph['edges'])}"
        )
        # Verify summary
        summary = graph["summary"]
        assert summary["total_facts"] > 0
        assert summary["total_clauses"] > 0

    def test_clause_type_diversity(self, client, cuad_doc_id):
        """Multiple clause types classified."""
        resp = client.get(f"/contracts/{cuad_doc_id}/clauses")
        assert resp.status_code == 200
        clauses = resp.json()
        clause_types = {c["clause_type"] for c in clauses}
        assert len(clause_types) >= 3, (
            f"Expected ≥3 distinct clause types, got {clause_types}"
        )


# ─────────────────────────────────────────────────────────────────────
# Workspace Integration with LegalBench Documents
# ─────────────────────────────────────────────────────────────────────

class TestLegalBenchWorkspaceIntegration:
    """Test workspace management with LegalBench documents."""

    def test_create_workspace_and_add_documents(self, client, nda_doc_id, cuad_doc_id):
        """Create workspace and associate both benchmark documents."""
        # Create workspace
        resp = client.post("/workspaces", json={
            "name": "LegalBench Review",
            "settings": {"benchmark": "legalbench_full"}
        })
        assert resp.status_code == 201
        ws_id = resp.json()["workspace_id"]

        # Add NDA
        resp = client.post(f"/workspaces/{ws_id}/documents", json={
            "document_id": nda_doc_id
        })
        assert resp.status_code == 204

        # Add CUAD license
        resp = client.post(f"/workspaces/{ws_id}/documents", json={
            "document_id": cuad_doc_id
        })
        assert resp.status_code == 204

        # Verify both documents are in workspace
        resp = client.get(f"/workspaces/{ws_id}")
        assert resp.status_code == 200
        ws = resp.json()
        assert nda_doc_id in ws["indexed_documents"]
        assert cuad_doc_id in ws["indexed_documents"]
        assert len(ws["indexed_documents"]) == 2
