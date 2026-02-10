"""Contract tests for workspace API (T106).

Tests the workspace API endpoints against the API contract:
- POST /workspaces creates workspace
- GET /workspaces/{id} returns workspace with indexed_documents and recent_sessions
- POST /workspaces/{id}/documents adds document to workspace
- DELETE /workspaces/{id}/documents/{doc_id} removes document
- GET /workspaces/{id}/sessions returns session history
- Error cases: workspace not found (404), document not found (404)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from contractos.api.app import create_app
from contractos.api.deps import init_state, shutdown_state
from contractos.config import ContractOSConfig, LLMConfig, StorageConfig

FIXTURES = Path(__file__).parent.parent / "fixtures"
DOCX_PATH = FIXTURES / "simple_procurement.docx"


@pytest.fixture
async def client(tmp_path: Path):
    """Create a test client with a fresh database per test."""
    shutdown_state()
    db_path = str(tmp_path / "test.db")
    config = ContractOSConfig(
        llm=LLMConfig(provider="mock"),
        storage=StorageConfig(path=db_path),
    )
    init_state(config)
    app = create_app(config)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    shutdown_state()


class TestCreateWorkspace:
    @pytest.mark.asyncio
    async def test_creates_workspace(self, client: AsyncClient) -> None:
        resp = await client.post("/workspaces", json={"name": "Test Workspace"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Workspace"
        assert data["workspace_id"].startswith("w-")
        assert data["indexed_documents"] == []
        assert data["recent_sessions"] == []
        assert "created_at" in data
        assert "last_accessed_at" in data

    @pytest.mark.asyncio
    async def test_creates_workspace_with_settings(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/workspaces",
            json={"name": "Custom", "settings": {"theme": "dark"}},
        )
        assert resp.status_code == 201
        assert resp.json()["settings"] == {"theme": "dark"}

    @pytest.mark.asyncio
    async def test_empty_name_rejected(self, client: AsyncClient) -> None:
        resp = await client.post("/workspaces", json={"name": ""})
        assert resp.status_code == 422


class TestGetWorkspace:
    @pytest.mark.asyncio
    async def test_get_workspace(self, client: AsyncClient) -> None:
        # Create
        create_resp = await client.post("/workspaces", json={"name": "My Workspace"})
        ws_id = create_resp.json()["workspace_id"]

        # Get
        resp = await client.get(f"/workspaces/{ws_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["workspace_id"] == ws_id
        assert data["name"] == "My Workspace"
        assert "recent_sessions" in data

    @pytest.mark.asyncio
    async def test_workspace_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/workspaces/nonexistent")
        assert resp.status_code == 404


class TestListWorkspaces:
    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/workspaces")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_multiple(self, client: AsyncClient) -> None:
        await client.post("/workspaces", json={"name": "WS 1"})
        await client.post("/workspaces", json={"name": "WS 2"})
        resp = await client.get("/workspaces")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestDocumentAssociation:
    @pytest.mark.asyncio
    async def test_add_document_to_workspace(self, client: AsyncClient) -> None:
        # Create workspace
        ws_resp = await client.post("/workspaces", json={"name": "Doc Test"})
        ws_id = ws_resp.json()["workspace_id"]

        # Upload a document first
        with open(DOCX_PATH, "rb") as f:
            upload_resp = await client.post(
                "/contracts/upload",
                files={"file": ("test.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )
        doc_id = upload_resp.json()["document_id"]

        # Add document to workspace
        resp = await client.post(
            f"/workspaces/{ws_id}/documents",
            json={"document_id": doc_id},
        )
        assert resp.status_code == 204

        # Verify document is in workspace
        ws = await client.get(f"/workspaces/{ws_id}")
        assert doc_id in ws.json()["indexed_documents"]

    @pytest.mark.asyncio
    async def test_add_nonexistent_document_returns_404(self, client: AsyncClient) -> None:
        ws_resp = await client.post("/workspaces", json={"name": "Test"})
        ws_id = ws_resp.json()["workspace_id"]

        resp = await client.post(
            f"/workspaces/{ws_id}/documents",
            json={"document_id": "nonexistent-doc"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_add_document_to_nonexistent_workspace(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/workspaces/nonexistent/documents",
            json={"document_id": "doc-001"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_document_from_workspace(self, client: AsyncClient) -> None:
        # Create workspace and upload document
        ws_resp = await client.post("/workspaces", json={"name": "Remove Test"})
        ws_id = ws_resp.json()["workspace_id"]

        with open(DOCX_PATH, "rb") as f:
            upload_resp = await client.post(
                "/contracts/upload",
                files={"file": ("test.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )
        doc_id = upload_resp.json()["document_id"]

        # Add then remove
        await client.post(f"/workspaces/{ws_id}/documents", json={"document_id": doc_id})
        resp = await client.delete(f"/workspaces/{ws_id}/documents/{doc_id}")
        assert resp.status_code == 204

        # Verify removed
        ws = await client.get(f"/workspaces/{ws_id}")
        assert doc_id not in ws.json()["indexed_documents"]


class TestSessionHistory:
    @pytest.mark.asyncio
    async def test_sessions_endpoint(self, client: AsyncClient) -> None:
        ws_resp = await client.post("/workspaces", json={"name": "Session Test"})
        ws_id = ws_resp.json()["workspace_id"]

        resp = await client.get(f"/workspaces/{ws_id}/sessions")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_sessions_for_nonexistent_workspace(self, client: AsyncClient) -> None:
        resp = await client.get("/workspaces/nonexistent/sessions")
        assert resp.status_code == 404
