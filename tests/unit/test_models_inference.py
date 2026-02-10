"""Unit tests for Inference model (T011)."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from contractos.models.inference import Inference, InferenceType


class TestInferenceType:
    def test_all_types_exist(self):
        expected = {
            "obligation", "coverage", "similarity", "compliance_gap",
            "risk_indicator", "entity_resolution", "scope_determination", "negation",
        }
        assert {t.value for t in InferenceType} == expected


class TestInference:
    def test_valid_inference(self, sample_inference):
        assert sample_inference.confidence == 0.92
        assert len(sample_inference.supporting_fact_ids) == 2
        assert not sample_inference.is_low_confidence

    def test_confidence_range_enforced(self):
        with pytest.raises(ValidationError):
            Inference(
                inference_id="i-bad",
                inference_type=InferenceType.OBLIGATION,
                claim="test",
                supporting_fact_ids=["f-1"],
                reasoning_chain="test",
                confidence=1.5,
                confidence_basis="test",
                generated_by="test",
                generated_at=datetime.now(),
                document_id="doc-1",
            )

    def test_negative_confidence_rejected(self):
        with pytest.raises(ValidationError):
            Inference(
                inference_id="i-bad",
                inference_type=InferenceType.OBLIGATION,
                claim="test",
                supporting_fact_ids=["f-1"],
                reasoning_chain="test",
                confidence=-0.1,
                confidence_basis="test",
                generated_by="test",
                generated_at=datetime.now(),
                document_id="doc-1",
            )

    def test_supporting_facts_required(self):
        with pytest.raises(ValidationError):
            Inference(
                inference_id="i-bad",
                inference_type=InferenceType.OBLIGATION,
                claim="test",
                supporting_fact_ids=[],
                reasoning_chain="test",
                confidence=0.5,
                confidence_basis="test",
                generated_by="test",
                generated_at=datetime.now(),
                document_id="doc-1",
            )

    def test_low_confidence_flag(self):
        inf = Inference(
            inference_id="i-low",
            inference_type=InferenceType.COVERAGE,
            claim="Possibly covers IT",
            supporting_fact_ids=["f-1"],
            reasoning_chain="Weak evidence",
            confidence=0.35,
            confidence_basis="Low support",
            generated_by="test",
            generated_at=datetime.now(),
            document_id="doc-1",
        )
        assert inf.is_low_confidence

    def test_boundary_confidence_not_low(self):
        inf = Inference(
            inference_id="i-boundary",
            inference_type=InferenceType.COVERAGE,
            claim="test",
            supporting_fact_ids=["f-1"],
            reasoning_chain="test",
            confidence=0.5,
            confidence_basis="test",
            generated_by="test",
            generated_at=datetime.now(),
            document_id="doc-1",
        )
        assert not inf.is_low_confidence

    def test_serialization_roundtrip(self, sample_inference):
        data = sample_inference.model_dump()
        restored = Inference.model_validate(data)
        assert restored == sample_inference
