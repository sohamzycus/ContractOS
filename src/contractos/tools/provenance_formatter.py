"""Provenance formatting — human-readable summaries for provenance nodes."""

from __future__ import annotations

from contractos.models.provenance import ProvenanceChain, ProvenanceNode


def format_provenance_node(node: ProvenanceNode) -> dict:
    """Format a single provenance node for display.

    Returns a dict with:
        - node_type: str
        - reference_id: str
        - summary: str (human-readable)
        - document_location: str | None (navigable location for facts)
        - display_label: str (e.g. "Fact", "Binding", "Inference")
        - icon: str (emoji for UI rendering)
    """
    display_labels = {
        "fact": "Fact",
        "binding": "Binding",
        "inference": "Inference",
        "external": "External Source",
        "reasoning": "Reasoning",
    }
    icons = {
        "fact": "📄",
        "binding": "🔗",
        "inference": "💡",
        "external": "🌐",
        "reasoning": "🧠",
    }

    return {
        "node_type": node.node_type,
        "reference_id": node.reference_id,
        "summary": node.summary,
        "document_location": node.document_location,
        "display_label": display_labels.get(node.node_type, "Unknown"),
        "icon": icons.get(node.node_type, "❓"),
    }


def format_provenance_chain(chain: ProvenanceChain) -> dict:
    """Format a full provenance chain for API display.

    Returns a dict with:
        - nodes: list of formatted nodes
        - reasoning_summary: str
        - node_count: int
        - has_facts: bool
        - has_inferences: bool
    """
    formatted_nodes = [format_provenance_node(n) for n in chain.nodes]

    return {
        "nodes": formatted_nodes,
        "reasoning_summary": chain.reasoning_summary,
        "node_count": len(chain.nodes),
        "has_facts": any(n.node_type == "fact" for n in chain.nodes),
        "has_inferences": any(n.node_type == "inference" for n in chain.nodes),
    }
