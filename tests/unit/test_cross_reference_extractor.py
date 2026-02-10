"""Unit tests for cross-reference extractor (T046)."""

from __future__ import annotations

import pytest

from contractos.models.clause import (
    Clause,
    ClauseTypeEnum,
    ReferenceEffect,
    ReferenceType,
)
from contractos.tools.cross_reference_extractor import extract_cross_references


def _make_clause(clause_id: str, section_number: str) -> Clause:
    return Clause(
        clause_id=clause_id,
        document_id="doc-001",
        clause_type=ClauseTypeEnum.GENERAL,
        heading=f"Section {section_number}",
        section_number=section_number,
        fact_id="",
        contained_fact_ids=[],
        cross_reference_ids=[],
        classification_method="test",
    )


class TestCrossReferenceExtraction:
    def test_section_reference(self) -> None:
        text = "as mentioned in Section 3.2.1, the notice period applies."
        refs = extract_cross_references(text, "c-001")
        assert len(refs) >= 1
        assert any("3.2.1" in r.target_reference for r in refs)

    def test_section_symbol(self) -> None:
        text = "Subject to §12.1, the following applies."
        refs = extract_cross_references(text, "c-001")
        assert len(refs) >= 1

    def test_appendix_reference(self) -> None:
        text = "as detailed in Appendix A"
        refs = extract_cross_references(text, "c-001")
        assert len(refs) >= 1
        assert refs[0].reference_type == ReferenceType.APPENDIX_REF

    def test_schedule_reference(self) -> None:
        text = "listed in Schedule B"
        refs = extract_cross_references(text, "c-001")
        assert len(refs) >= 1
        assert refs[0].reference_type == ReferenceType.SCHEDULE_REF

    def test_clause_reference(self) -> None:
        text = "per Clause 4"
        refs = extract_cross_references(text, "c-001")
        assert len(refs) >= 1
        assert refs[0].reference_type == ReferenceType.CLAUSE_REF


class TestReferenceEffectClassification:
    def test_conditions_effect(self) -> None:
        text = "Subject to the terms in Section 5.1, the buyer may terminate."
        refs = extract_cross_references(text, "c-001")
        assert any(r.effect == ReferenceEffect.CONDITIONS for r in refs)

    def test_incorporates_effect(self) -> None:
        text = "in accordance with Section 3.2"
        refs = extract_cross_references(text, "c-001")
        assert any(r.effect == ReferenceEffect.INCORPORATES for r in refs)

    def test_overrides_effect(self) -> None:
        text = "Notwithstanding Section 7.1, the vendor is exempt."
        refs = extract_cross_references(text, "c-001")
        assert any(r.effect == ReferenceEffect.OVERRIDES for r in refs)

    def test_default_references_effect(self) -> None:
        text = "See Section 2 for more information."
        refs = extract_cross_references(text, "c-001")
        assert any(r.effect == ReferenceEffect.REFERENCES for r in refs)


class TestCrossReferenceResolution:
    def test_resolved_when_clause_exists(self) -> None:
        clauses = [_make_clause("c-005", "5.1")]
        text = "Subject to Section 5.1, the following applies."
        refs = extract_cross_references(text, "c-001", clauses)
        resolved = [r for r in refs if "5.1" in r.target_reference]
        assert len(resolved) >= 1
        assert resolved[0].resolved is True
        assert resolved[0].target_clause_id == "c-005"

    def test_unresolved_when_clause_missing(self) -> None:
        text = "Subject to Section 99.9, the following applies."
        refs = extract_cross_references(text, "c-001", clauses=[])
        assert len(refs) >= 1
        assert refs[0].resolved is False
        assert refs[0].target_clause_id is None

    def test_context_captured(self) -> None:
        text = "Subject to the terms in Section 5.1, the buyer may terminate."
        refs = extract_cross_references(text, "c-001")
        assert len(refs) >= 1
        assert "Subject to" in refs[0].context or "Section 5.1" in refs[0].context

    def test_unique_reference_ids(self) -> None:
        text = "See Section 1 and Section 2."
        refs = extract_cross_references(text, "c-001")
        ids = [r.reference_id for r in refs]
        assert len(ids) == len(set(ids))
