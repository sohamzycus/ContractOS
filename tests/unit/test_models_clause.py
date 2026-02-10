"""Unit tests for Clause and CrossReference models (T012)."""

import pytest
from pydantic import ValidationError

from contractos.models.clause import (
    Clause,
    ClauseTypeEnum,
    CrossReference,
    ReferenceEffect,
    ReferenceType,
)
from contractos.models.clause_type import ClauseFactSlot, ClauseTypeSpec, MandatoryFactSpec, SlotStatus
from contractos.models.fact import EntityType


class TestClauseTypeEnum:
    def test_has_all_standard_types_plus_general_and_custom(self):
        assert len(ClauseTypeEnum) == 26
        assert ClauseTypeEnum.TERMINATION == "termination"
        assert ClauseTypeEnum.GENERAL == "general"
        assert ClauseTypeEnum.CUSTOM == "custom"
        # Verify new types added for Phase 3
        assert ClauseTypeEnum.INDEMNIFICATION == "indemnification"
        assert ClauseTypeEnum.IP_RIGHTS == "ip_rights"
        assert ClauseTypeEnum.DISPUTE_RESOLUTION == "dispute_resolution"
        assert ClauseTypeEnum.NOTICE == "notice"
        assert ClauseTypeEnum.SCOPE == "scope"


class TestReferenceType:
    def test_all_types(self):
        expected = {"section_ref", "clause_ref", "appendix_ref", "schedule_ref", "exhibit_ref", "annex_ref", "external_doc_ref"}
        assert {t.value for t in ReferenceType} == expected


class TestReferenceEffect:
    def test_all_effects(self):
        expected = {"modifies", "overrides", "conditions", "incorporates", "exempts", "delegates", "references", "limits", "defines"}
        assert {e.value for e in ReferenceEffect} == expected


class TestCrossReference:
    def test_valid_cross_reference(self, sample_cross_reference):
        assert sample_cross_reference.target_reference == "section 3.2.1"
        assert sample_cross_reference.resolved is False
        assert sample_cross_reference.target_clause_id is None

    def test_resolved_cross_reference(self):
        xr = CrossReference(
            reference_id="xr-resolved",
            source_clause_id="c-001",
            target_reference="section 3.2.1",
            target_clause_id="c-005",
            reference_type=ReferenceType.SECTION_REF,
            effect=ReferenceEffect.CONDITIONS,
            context="as mentioned in section 3.2.1",
            resolved=True,
            source_fact_id="f-025",
        )
        assert xr.resolved is True
        assert xr.target_clause_id == "c-005"

    def test_serialization_roundtrip(self, sample_cross_reference):
        data = sample_cross_reference.model_dump()
        restored = CrossReference.model_validate(data)
        assert restored == sample_cross_reference


class TestClause:
    def test_valid_clause(self, sample_clause):
        assert sample_clause.clause_type == ClauseTypeEnum.TERMINATION
        assert sample_clause.classification_method == "pattern_match"
        assert sample_clause.classification_confidence is None

    def test_llm_classified_clause_has_confidence(self):
        c = Clause(
            clause_id="c-llm",
            document_id="doc-001",
            clause_type=ClauseTypeEnum.INDEMNITY,
            heading="12. Liability and Indemnification",
            fact_id="f-030",
            classification_method="llm_classification",
            classification_confidence=0.85,
        )
        assert c.classification_confidence == 0.85

    def test_serialization_roundtrip(self, sample_clause):
        data = sample_clause.model_dump()
        restored = Clause.model_validate(data)
        assert restored == sample_clause


class TestClauseTypeSpec:
    def test_valid_spec(self):
        spec = ClauseTypeSpec(
            type_id=ClauseTypeEnum.TERMINATION,
            display_name="Termination Clause",
            mandatory_facts=[
                MandatoryFactSpec(
                    fact_name="notice_period",
                    fact_description="Duration of notice required",
                    entity_type=EntityType.DURATION,
                ),
                MandatoryFactSpec(
                    fact_name="termination_reasons",
                    fact_description="Grounds for termination",
                    entity_type=EntityType.SECTION_REF,
                ),
            ],
            optional_facts=[
                MandatoryFactSpec(
                    fact_name="cure_period",
                    fact_description="Time to remedy breach",
                    entity_type=EntityType.DURATION,
                    required=False,
                ),
            ],
        )
        assert len(spec.mandatory_facts) == 2
        assert len(spec.optional_facts) == 1
        assert spec.mandatory_facts[0].required is True
        assert spec.optional_facts[0].required is False


class TestClauseFactSlot:
    def test_filled_slot_requires_fact_id(self):
        with pytest.raises(ValueError, match="filled_by_fact_id is required"):
            ClauseFactSlot(
                clause_id="c-001",
                fact_spec_name="notice_period",
                status=SlotStatus.FILLED,
                filled_by_fact_id=None,
            )

    def test_filled_slot_with_fact_id(self):
        slot = ClauseFactSlot(
            clause_id="c-001",
            fact_spec_name="notice_period",
            status=SlotStatus.FILLED,
            filled_by_fact_id="f-050",
        )
        assert slot.filled_by_fact_id == "f-050"

    def test_missing_slot_allows_none_fact_id(self):
        slot = ClauseFactSlot(
            clause_id="c-001",
            fact_spec_name="cure_period",
            status=SlotStatus.MISSING,
        )
        assert slot.filled_by_fact_id is None

    def test_status_transitions(self):
        assert SlotStatus.FILLED == "filled"
        assert SlotStatus.MISSING == "missing"
        assert SlotStatus.PARTIAL == "partial"
