"""Unit tests for the ContractOS MCP server — startup, tools, resources, prompts."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


class TestMCPServerCreation:
    """Test that the MCP server creates with correct registrations."""

    @patch("contractos.mcp.context.init_state")
    def test_create_server_registers_13_tools(self, mock_init):
        mock_state = MagicMock()
        mock_state.config.llm.provider = "mock"
        mock_init.return_value = mock_state

        from contractos.mcp.server import create_server

        mcp, ctx = create_server()
        tools = list(mcp._tool_manager._tools.keys())
        assert len(tools) == 13, f"Expected 13 tools, got {len(tools)}: {tools}"

    @patch("contractos.mcp.context.init_state")
    def test_create_server_tool_names(self, mock_init):
        mock_state = MagicMock()
        mock_state.config.llm.provider = "mock"
        mock_init.return_value = mock_state

        from contractos.mcp.server import create_server

        mcp, _ = create_server()
        tools = set(mcp._tool_manager._tools.keys())
        expected = {
            "upload_contract",
            "load_sample_contract",
            "ask_question",
            "review_against_playbook",
            "triage_nda",
            "discover_hidden_facts",
            "extract_obligations",
            "generate_risk_memo",
            "get_clause_gaps",
            "search_contracts",
            "compare_clauses",
            "generate_report",
            "clear_workspace",
        }
        assert tools == expected

    @patch("contractos.mcp.context.init_state")
    def test_create_server_name(self, mock_init):
        mock_state = MagicMock()
        mock_state.config.llm.provider = "mock"
        mock_init.return_value = mock_state

        from contractos.mcp.server import create_server

        mcp, _ = create_server()
        assert mcp.name == "ContractOS"


class TestMCPContext:
    """Test MCPContext wraps AppState correctly."""

    @patch("contractos.mcp.context.init_state")
    def test_context_wraps_appstate(self, mock_init):
        mock_state = MagicMock()
        mock_init.return_value = mock_state

        from contractos.mcp.context import MCPContext

        ctx = MCPContext()
        assert ctx.state is mock_state

    @patch("contractos.mcp.context.init_state")
    def test_get_contract_or_error_found(self, mock_init):
        mock_state = MagicMock()
        mock_contract = MagicMock()
        mock_contract.document_id = "abc"
        mock_contract.title = "test"
        mock_state.trust_graph.get_contract.return_value = mock_contract
        mock_init.return_value = mock_state

        from contractos.mcp.context import MCPContext

        ctx = MCPContext()
        result = ctx.get_contract_or_error("abc")
        assert result.document_id == "abc"

    @patch("contractos.mcp.context.init_state")
    def test_get_contract_or_error_not_found(self, mock_init):
        mock_state = MagicMock()
        mock_state.trust_graph.get_contract.return_value = None
        mock_init.return_value = mock_state

        from contractos.mcp.context import MCPContext

        ctx = MCPContext()
        with pytest.raises(ValueError, match="Document not found"):
            ctx.get_contract_or_error("missing")

    @patch("contractos.mcp.context.init_state")
    @patch("contractos.mcp.context.shutdown_state")
    def test_close_calls_shutdown(self, mock_shutdown, mock_init):
        mock_init.return_value = MagicMock()

        from contractos.mcp.context import MCPContext

        ctx = MCPContext()
        ctx.close()
        mock_shutdown.assert_called_once()


class TestMCPTools:
    """Test individual MCP tool functions."""

    @patch("contractos.mcp.context.init_state")
    @pytest.mark.asyncio
    async def test_clear_workspace(self, mock_init):
        mock_state = MagicMock()
        mock_contract_a = MagicMock()
        mock_contract_a.document_id = "a"
        mock_contract_b = MagicMock()
        mock_contract_b.document_id = "b"
        mock_state.trust_graph.list_contracts.return_value = [
            mock_contract_a,
            mock_contract_b,
        ]
        mock_state.embedding_index.has_document.return_value = True
        mock_init.return_value = mock_state

        from contractos.mcp.server import create_server

        mcp, ctx = create_server()
        tool_fn = mcp._tool_manager._tools["clear_workspace"].fn
        result = await tool_fn()
        parsed = json.loads(result) if isinstance(result, str) else result
        assert parsed["contracts_removed"] == 2

    @patch("contractos.mcp.context.init_state")
    @pytest.mark.asyncio
    async def test_upload_contract_file_not_found(self, mock_init):
        mock_init.return_value = MagicMock()

        from contractos.mcp.server import create_server

        mcp, ctx = create_server()
        tool_fn = mcp._tool_manager._tools["upload_contract"].fn
        result = await tool_fn("/nonexistent/file.pdf")
        parsed = json.loads(result) if isinstance(result, str) else result
        assert "error" in parsed
        assert "File not found" in parsed["error"]

    @patch("contractos.mcp.context.init_state")
    @pytest.mark.asyncio
    async def test_upload_contract_unsupported_format(self, mock_init):
        mock_init.return_value = MagicMock()
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test")
            tmp_path = f.name

        from contractos.mcp.server import create_server

        mcp, ctx = create_server()
        tool_fn = mcp._tool_manager._tools["upload_contract"].fn
        result = await tool_fn(tmp_path)
        parsed = json.loads(result) if isinstance(result, str) else result
        assert "error" in parsed
        assert "Unsupported format" in parsed["error"]

        Path(tmp_path).unlink(missing_ok=True)

    @patch("contractos.mcp.context.init_state")
    @pytest.mark.asyncio
    async def test_search_contracts_empty_index(self, mock_init):
        mock_state = MagicMock()
        mock_state.trust_graph.list_contracts.return_value = []
        mock_init.return_value = mock_state

        from contractos.mcp.server import create_server

        mcp, ctx = create_server()
        tool_fn = mcp._tool_manager._tools["search_contracts"].fn
        result = await tool_fn("test query")
        parsed = json.loads(result) if isinstance(result, str) else result
        assert "error" in parsed

    @patch("contractos.mcp.context.init_state")
    @pytest.mark.asyncio
    async def test_generate_report_invalid_type(self, mock_init):
        mock_state = MagicMock()
        mock_init.return_value = mock_state

        from contractos.mcp.server import create_server

        mcp, ctx = create_server()
        tool_fn = mcp._tool_manager._tools["generate_report"].fn
        result = await tool_fn("doc1", "invalid_type")
        parsed = json.loads(result) if isinstance(result, str) else result
        assert "error" in parsed
        assert "Invalid report_type" in parsed["error"]


class TestMCPResources:
    """Test MCP resource functions."""

    @patch("contractos.mcp.context.init_state")
    def test_health_resource(self, mock_init):
        mock_state = MagicMock()
        mock_contract = MagicMock()
        mock_contract.document_id = "a"
        mock_state.trust_graph.list_contracts.return_value = [mock_contract]
        mock_state.config.llm.provider = "mock"
        mock_init.return_value = mock_state

        from contractos.mcp.server import create_server

        mcp, ctx = create_server()
        resource_fns = {r.uri: r for r in mcp._resource_manager._resources.values()}
        assert any("health" in str(uri) for uri in resource_fns)

    @patch("contractos.mcp.context.init_state")
    def test_contracts_resource(self, mock_init):
        mock_state = MagicMock()
        mock_contract = MagicMock()
        mock_contract.document_id = "abc"
        mock_contract.title = "test"
        mock_state.trust_graph.list_contracts.return_value = [mock_contract]
        mock_state.config.llm.provider = "mock"
        mock_init.return_value = mock_state

        from contractos.mcp.server import create_server

        mcp, ctx = create_server()
        resource_fns = {str(r.uri): r for r in mcp._resource_manager._resources.values()}
        assert any("contracts" in uri for uri in resource_fns)


class TestMCPPrompts:
    """Test MCP prompt functions."""

    @patch("contractos.mcp.context.init_state")
    def test_prompts_registered(self, mock_init):
        mock_state = MagicMock()
        mock_state.config.llm.provider = "mock"
        mock_init.return_value = mock_state

        from contractos.mcp.server import create_server

        mcp, ctx = create_server()
        prompts = list(mcp._prompt_manager._prompts.keys())
        assert len(prompts) == 5
        expected = {
            "full_contract_analysis",
            "due_diligence_checklist",
            "negotiation_prep",
            "risk_summary",
            "clause_comparison",
        }
        assert set(prompts) == expected
