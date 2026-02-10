"""Unit tests for provenance formatting utilities."""

from __future__ import annotations

from contractos.models.provenance import ProvenanceChain, ProvenanceNode
from contractos.tools.provenance_formatter import (
    format_provenance_chain,
    format_provenance_node,
)


class TestFormatProvenanceNode:
    """Test individual node formatting."""

    def test_fact_node(self) -> None:
        node = ProvenanceNode(
            node_type="fact",
            reference_id="f-001",
            summary='Payment term: "Net 90"',
            document_location="paragraph 5",
        )
        result = format_provenance_node(node)
        assert result["node_type"] == "fact"
        assert result["display_label"] == "Fact"
        assert result["icon"] == "📄"
        assert result["document_location"] == "paragraph 5"

    def test_binding_node(self) -> None:
        node = ProvenanceNode(
            node_type="binding",
            reference_id="b-001",
            summary='"Buyer" → "Alpha Corp"',
        )
        result = format_provenance_node(node)
        assert result["display_label"] == "Binding"
        assert result["icon"] == "🔗"
        assert result["document_location"] is None

    def test_inference_node(self) -> None:
        node = ProvenanceNode(
            node_type="inference",
            reference_id="i-001",
            summary="Contract covers maintenance obligations",
        )
        result = format_provenance_node(node)
        assert result["display_label"] == "Inference"
        assert result["icon"] == "💡"

    def test_external_node(self) -> None:
        node = ProvenanceNode(
            node_type="external",
            reference_id="ext-001",
            summary="Domain knowledge: Dell Inspiron is IT equipment",
        )
        result = format_provenance_node(node)
        assert result["display_label"] == "External Source"
        assert result["icon"] == "🌐"

    def test_reasoning_node(self) -> None:
        node = ProvenanceNode(
            node_type="reasoning",
            reference_id="r-001",
            summary="Step-by-step reasoning about obligations",
        )
        result = format_provenance_node(node)
        assert result["display_label"] == "Reasoning"
        assert result["icon"] == "🧠"


class TestFormatProvenanceChain:
    """Test full chain formatting."""

    def test_chain_with_facts_and_inference(self) -> None:
        chain = ProvenanceChain(
            nodes=[
                ProvenanceNode(
                    node_type="fact",
                    reference_id="f-001",
                    summary='Found "Net 90" in payment section',
                    document_location="paragraph 5",
                ),
                ProvenanceNode(
                    node_type="inference",
                    reference_id="i-001",
                    summary="Payment terms are Net 90 days",
                ),
            ],
            reasoning_summary="Payment terms identified from clause text",
        )
        result = format_provenance_chain(chain)
        assert result["node_count"] == 2
        assert result["has_facts"] is True
        assert result["has_inferences"] is True
        assert len(result["nodes"]) == 2
        assert result["reasoning_summary"] == "Payment terms identified from clause text"

    def test_chain_without_inferences(self) -> None:
        chain = ProvenanceChain(
            nodes=[
                ProvenanceNode(
                    node_type="fact",
                    reference_id="f-001",
                    summary="Direct fact answer",
                    document_location="section 3",
                ),
            ],
            reasoning_summary="Direct answer from facts",
        )
        result = format_provenance_chain(chain)
        assert result["has_facts"] is True
        assert result["has_inferences"] is False

    def test_chain_with_only_reasoning(self) -> None:
        chain = ProvenanceChain(
            nodes=[
                ProvenanceNode(
                    node_type="reasoning",
                    reference_id="not_found",
                    summary="No relevant facts found",
                ),
            ],
            reasoning_summary="No relevant facts found",
        )
        result = format_provenance_chain(chain)
        assert result["has_facts"] is False
        assert result["has_inferences"] is False
        assert result["node_count"] == 1
