"""Unit tests for Fact model (T009)."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from contractos.models.fact import EntityType, Fact, FactEvidence, FactType


class TestFactType:
    def test_all_types_exist(self):
        expected = {
            "text_span", "entity", "clause", "table_cell",
            "heading", "metadata", "structural", "cross_reference",
            "clause_text",
        }
        assert {t.value for t in FactType} == expected

    def test_cross_reference_type_exists(self):
        assert FactType.CROSS_REFERENCE == "cross_reference"


class TestEntityType:
    def test_all_types_exist(self):
        expected = {"party", "date", "money", "product", "location", "duration", "section_ref"}
        assert {t.value for t in EntityType} == expected


class TestFactEvidence:
    def test_valid_evidence(self, sample_evidence):
        assert sample_evidence.char_start == 1203
        assert sample_evidence.char_end == 1227
        assert sample_evidence.page_number is None

    def test_char_end_must_be_greater_than_start(self):
        with pytest.raises(ValueError, match="char_end.*must be greater"):
            FactEvidence(
                document_id="doc-001",
                text_span="test",
                char_start=100,
                char_end=50,
                location_hint="§1",
                structural_path="body > para[1]",
            )

    def test_char_start_and_end_equal_is_invalid(self):
        with pytest.raises(ValueError, match="char_end.*must be greater"):
            FactEvidence(
                document_id="doc-001",
                text_span="test",
                char_start=100,
                char_end=100,
                location_hint="§1",
                structural_path="body > para[1]",
            )

    def test_negative_char_start_rejected(self):
        with pytest.raises(ValidationError):
            FactEvidence(
                document_id="doc-001",
                text_span="test",
                char_start=-1,
                char_end=10,
                location_hint="§1",
                structural_path="body > para[1]",
            )

    def test_empty_text_span_rejected(self):
        with pytest.raises(ValidationError):
            FactEvidence(
                document_id="doc-001",
                text_span="",
                char_start=0,
                char_end=10,
                location_hint="§1",
                structural_path="body > para[1]",
            )

    def test_page_number_optional(self):
        ev = FactEvidence(
            document_id="doc-001",
            text_span="test",
            char_start=0,
            char_end=4,
            location_hint="§1",
            structural_path="body",
            page_number=5,
        )
        assert ev.page_number == 5


class TestFact:
    def test_valid_text_span_fact(self, sample_fact):
        assert sample_fact.fact_type == FactType.TEXT_SPAN
        assert sample_fact.entity_type is None
        assert sample_fact.value == "Net 90 from invoice date"

    def test_valid_entity_fact(self, sample_entity_fact):
        assert sample_entity_fact.fact_type == FactType.ENTITY
        assert sample_entity_fact.entity_type == EntityType.PARTY

    def test_entity_fact_requires_entity_type(self):
        with pytest.raises(ValueError, match="entity_type is required"):
            Fact(
                fact_id="f-bad",
                fact_type=FactType.ENTITY,
                value="Dell",
                evidence=FactEvidence(
                    document_id="doc-001",
                    text_span="Dell",
                    char_start=0,
                    char_end=4,
                    location_hint="§1",
                    structural_path="body",
                ),
                extraction_method="test",
                extracted_at=datetime.now(),
            )

    def test_non_entity_fact_allows_none_entity_type(self, sample_fact):
        assert sample_fact.entity_type is None

    def test_empty_fact_id_rejected(self):
        with pytest.raises(ValidationError):
            Fact(
                fact_id="",
                fact_type=FactType.TEXT_SPAN,
                value="test",
                evidence=FactEvidence(
                    document_id="d", text_span="t", char_start=0, char_end=1,
                    location_hint="§1", structural_path="body",
                ),
                extraction_method="test",
                extracted_at=datetime.now(),
            )

    def test_serialization_roundtrip(self, sample_fact):
        data = sample_fact.model_dump()
        restored = Fact.model_validate(data)
        assert restored == sample_fact

    def test_json_roundtrip(self, sample_fact):
        json_str = sample_fact.model_dump_json()
        restored = Fact.model_validate_json(json_str)
        assert restored == sample_fact
