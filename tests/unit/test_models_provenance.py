"""Unit tests for ProvenanceChain model (T013)."""

import pytest
from pydantic import ValidationError

from contractos.models.provenance import ProvenanceChain, ProvenanceNode


class TestProvenanceNode:
    def test_valid_fact_node(self):
        node = ProvenanceNode(
            node_type="fact",
            reference_id="f-001",
            summary="§5.2 states 'Net 90'",
            document_location="§5.2, chars 1203-1227",
        )
        assert node.node_type == "fact"
        assert node.document_location is not None

    def test_inference_node_no_location(self):
        node = ProvenanceNode(
            node_type="inference",
            reference_id="i-001",
            summary="Maintenance obligation inferred",
        )
        assert node.document_location is None

    def test_valid_node_types(self):
        for nt in ["fact", "binding", "inference", "external", "reasoning"]:
            node = ProvenanceNode(node_type=nt, reference_id="x", summary="test")
            assert node.node_type == nt

    def test_invalid_node_type_rejected(self):
        with pytest.raises(ValidationError):
            ProvenanceNode(node_type="opinion", reference_id="x", summary="test")


class TestProvenanceChain:
    def test_valid_chain(self, sample_provenance):
        assert len(sample_provenance.nodes) == 1
        assert sample_provenance.reasoning_summary != ""

    def test_empty_chain_rejected(self):
        with pytest.raises(ValidationError):
            ProvenanceChain(nodes=[], reasoning_summary="test")

    def test_empty_reasoning_rejected(self):
        with pytest.raises(ValidationError):
            ProvenanceChain(
                nodes=[ProvenanceNode(node_type="fact", reference_id="f-1", summary="test")],
                reasoning_summary="",
            )

    def test_multi_node_chain(self):
        chain = ProvenanceChain(
            nodes=[
                ProvenanceNode(node_type="fact", reference_id="f-1", summary="Fact 1"),
                ProvenanceNode(node_type="binding", reference_id="b-1", summary="Binding 1"),
                ProvenanceNode(node_type="inference", reference_id="i-1", summary="Inference 1"),
            ],
            reasoning_summary="Combined reasoning from fact, binding, and inference.",
        )
        assert len(chain.nodes) == 3

    def test_serialization_roundtrip(self, sample_provenance):
        data = sample_provenance.model_dump()
        restored = ProvenanceChain.model_validate(data)
        assert restored == sample_provenance
