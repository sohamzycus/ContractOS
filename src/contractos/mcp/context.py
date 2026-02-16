"""Shared context for the ContractOS MCP server.

Wraps the existing AppState via composition — does NOT duplicate
TrustGraph, EmbeddingIndex, or LLM provider.  All LLM calls go
through ``self.state.llm`` (the provider abstraction).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from contractos.api.deps import AppState, init_state, shutdown_state
from contractos.config import ContractOSConfig
from contractos.models.document import Contract

logger = logging.getLogger("contractos.mcp")


class MCPContext:
    """Singleton holding shared resources for the MCP server lifetime.

    Composes ``AppState`` from the existing API layer so that both the
    FastAPI server and the MCP server share the same TrustGraph,
    EmbeddingIndex, and LLM provider instance.
    """

    def __init__(self, config: ContractOSConfig | None = None) -> None:
        self.state: AppState = init_state(config)
        logger.info("MCPContext initialised (TrustGraph + EmbeddingIndex + LLM ready)")

    # ── Convenience helpers ──────────────────────────────────

    def get_contract_or_error(self, document_id: str) -> Contract:
        """Return contract metadata or raise with an agent-friendly message."""
        contract = self.state.trust_graph.get_contract(document_id)
        if contract is None:
            msg = (
                f"Document not found: {document_id}. "
                "Upload a contract first with upload_contract or load_sample_contract."
            )
            raise ValueError(msg)
        return contract

    def get_document_text(self, document_id: str) -> str:
        """Return the full text of a document from the embedding index or facts."""
        self.get_contract_or_error(document_id)
        idx = self.state.embedding_index
        if idx.has_document(document_id) and document_id in idx._chunks:
            chunks = idx._chunks[document_id]
            if chunks:
                return "\n\n".join(c.text for c in chunks)
        facts = self.state.trust_graph.get_facts_by_document(document_id)
        return "\n".join(f.value for f in facts if f.value)

    def list_samples(self) -> list[dict]:
        """Return the sample contract manifest."""
        manifest_path = Path(__file__).parent.parent.parent.parent / "demo" / "samples" / "manifest.json"
        if manifest_path.exists():
            return json.loads(manifest_path.read_text())  # type: ignore[no-any-return]
        return []

    def get_sample_path(self, filename: str) -> Path:
        """Return absolute path to a sample contract file."""
        samples_dir = Path(__file__).parent.parent.parent.parent / "demo" / "samples"
        path = samples_dir / filename
        if not path.exists():
            available = [s["filename"] for s in self.list_samples()]
            msg = f"Sample not found: {filename}. Available: {', '.join(available)}"
            raise ValueError(msg)
        return path

    # ── Lifecycle ────────────────────────────────────────────

    def close(self) -> None:
        shutdown_state()
        logger.info("MCPContext shut down")
