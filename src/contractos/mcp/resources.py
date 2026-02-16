"""MCP resource definitions for ContractOS.

Resources are read-only data endpoints that MCP clients can access
to inspect contract data without invoking tools.
"""

from __future__ import annotations

import json
import logging

from mcp.server.fastmcp import FastMCP

from contractos.mcp.context import MCPContext

logger = logging.getLogger("contractos.mcp.resources")


def register_resources(mcp: FastMCP, ctx: MCPContext) -> None:
    """Register all 10 ContractOS MCP resources."""

    @mcp.resource("contractos://contracts")
    def list_contracts() -> str:
        """List all indexed contracts."""
        contracts = ctx.state.trust_graph.list_contracts()
        return json.dumps([c.model_dump(mode="json") for c in contracts], default=str)

    @mcp.resource("contractos://contracts/{document_id}")
    def get_contract(document_id: str) -> str:
        """Get metadata for a specific contract."""
        contract = ctx.state.trust_graph.get_contract(document_id)
        if contract is None:
            return json.dumps({"error": f"Document not found: {document_id}"})
        return json.dumps(contract.model_dump(mode="json"), default=str)

    @mcp.resource("contractos://contracts/{document_id}/facts")
    def get_facts(document_id: str) -> str:
        """Get all extracted facts for a contract."""
        facts = ctx.state.trust_graph.get_facts_by_document(document_id)
        return json.dumps(
            [
                {
                    "fact_id": f.fact_id,
                    "fact_type": f.fact_type.value if hasattr(f.fact_type, "value") else str(f.fact_type),
                    "value": f.value,
                    "evidence": {
                        "text_span": f.evidence.text_span,
                        "char_start": f.evidence.char_start,
                        "char_end": f.evidence.char_end,
                        "location_hint": f.evidence.location_hint,
                    },
                }
                for f in facts
            ],
            default=str,
        )

    @mcp.resource("contractos://contracts/{document_id}/clauses")
    def get_clauses(document_id: str) -> str:
        """Get all classified clauses for a contract."""
        clauses = ctx.state.trust_graph.get_clauses_by_document(document_id)
        return json.dumps(
            [
                {
                    "clause_id": c.clause_id,
                    "clause_type": c.clause_type,
                    "heading": c.heading,
                    "section_number": c.section_number,
                    "text": (c.text or "")[:500],
                }
                for c in clauses
            ],
            default=str,
        )

    @mcp.resource("contractos://contracts/{document_id}/bindings")
    def get_bindings(document_id: str) -> str:
        """Get all definitions and aliases for a contract."""
        bindings = ctx.state.trust_graph.get_bindings_by_document(document_id)
        return json.dumps(
            [
                {
                    "binding_id": b.binding_id,
                    "term": b.term,
                    "resolves_to": b.resolves_to,
                    "binding_type": b.binding_type.value if hasattr(b.binding_type, "value") else str(b.binding_type),
                    "scope": b.scope.value if hasattr(b.scope, "value") else str(b.scope),
                }
                for b in bindings
            ],
            default=str,
        )

    @mcp.resource("contractos://contracts/{document_id}/graph")
    def get_graph(document_id: str) -> str:
        """Get the TrustGraph view (nodes + edges) for a contract."""
        tg = ctx.state.trust_graph
        facts = tg.get_facts_by_document(document_id)
        clauses = tg.get_clauses_by_document(document_id)
        bindings = tg.get_bindings_by_document(document_id)

        nodes = []
        edges = []

        for f in facts:
            nodes.append({"id": f.fact_id, "type": "fact", "label": f.value[:80]})
        for c in clauses:
            nodes.append({"id": c.clause_id, "type": "clause", "label": c.heading or c.clause_type})
        for b in bindings:
            nodes.append({"id": b.binding_id, "type": "binding", "label": f"{b.term} → {b.resolves_to}"})
            edges.append({"source": b.binding_id, "target": b.term, "type": "resolves"})

        return json.dumps({"nodes": nodes, "edges": edges}, default=str)

    @mcp.resource("contractos://samples")
    def list_samples() -> str:
        """List available sample contracts for testing."""
        return json.dumps(ctx.list_samples(), default=str)

    @mcp.resource("contractos://chat/history")
    def get_chat_history() -> str:
        """Get Q&A chat history."""
        try:
            sessions = ctx.state.workspace_store.get_sessions_by_workspace("default")
            return json.dumps(
                [
                    {
                        "session_id": s.session_id,
                        "query": s.query,
                        "status": s.status.value if hasattr(s.status, "value") else str(s.status),
                    }
                    for s in sessions
                ],
                default=str,
            )
        except Exception:
            return json.dumps([])

    @mcp.resource("contractos://health")
    def get_health() -> str:
        """Get server health status and configuration."""
        contracts = ctx.state.trust_graph.list_contracts()
        return json.dumps({
            "status": "ok",
            "version": "0.1.0",
            "contracts_indexed": len(contracts),
            "embedding_model": "all-MiniLM-L6-v2",
            "llm_provider": ctx.state.config.llm.provider,
        })

    @mcp.resource("contractos://playbook")
    def get_playbook() -> str:
        """Get the active playbook configuration."""
        from contractos.tools.playbook_loader import load_default_playbook

        playbook = load_default_playbook()
        return json.dumps(
            {
                "positions": [
                    {
                        "clause_type": p.clause_type,
                        "preferred_position": p.preferred_position,
                        "fallback_position": p.fallback_position,
                        "walk_away": p.walk_away,
                        "negotiation_tier": p.negotiation_tier.value
                        if hasattr(p.negotiation_tier, "value")
                        else str(p.negotiation_tier),
                    }
                    for p in playbook.positions
                ],
            },
            default=str,
        )
