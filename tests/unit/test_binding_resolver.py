"""Unit tests for binding resolver (T067–T069)."""

from __future__ import annotations

from datetime import datetime

import pytest

from contractos.models.binding import Binding, BindingScope, BindingType
from contractos.models.fact import Fact, FactEvidence, FactType
from contractos.tools.binding_resolver import resolve_bindings, resolve_term

NOW = datetime(2025, 2, 9, 12, 0, 0)
DOC_ID = "doc-001"


def _make_fact(fact_id: str, value: str, char_start: int = 0) -> Fact:
    return Fact(
        fact_id=fact_id,
        fact_type=FactType.TEXT_SPAN,
        value=value,
        evidence=FactEvidence(
            document_id=DOC_ID,
            text_span=value,
            char_start=char_start,
            char_end=char_start + len(value),
            location_hint="test",
            structural_path="body > p[0]",
        ),
        extraction_method="test",
        extracted_at=NOW,
    )


def _make_binding(term: str, resolves_to: str, binding_id: str = "b-001") -> Binding:
    return Binding(
        binding_id=binding_id,
        binding_type=BindingType.DEFINITION,
        term=term,
        resolves_to=resolves_to,
        source_fact_id="f-001",
        document_id=DOC_ID,
        scope=BindingScope.CONTRACT,
    )


class TestResolveBindings:
    def test_extracts_definitions_from_text(self) -> None:
        text = '"Effective Date" shall mean January 1, 2025. "Service Period" means thirty days.'
        facts = [_make_fact("f-001", "Effective Date", 1)]
        bindings = resolve_bindings(facts, [], text, DOC_ID)
        terms = {b.term for b in bindings}
        assert "Effective Date" in terms
        assert "Service Period" in terms

    def test_merges_with_existing_alias_bindings(self) -> None:
        text = '"Effective Date" shall mean January 1, 2025.'
        existing = [_make_binding("Buyer", "Alpha Corp")]
        facts = [_make_fact("f-001", "Effective Date", 1)]
        bindings = resolve_bindings(facts, existing, text, DOC_ID)
        terms = {b.term for b in bindings}
        assert "Buyer" in terms
        assert "Effective Date" in terms

    def test_existing_bindings_take_precedence(self) -> None:
        text = '"Buyer" shall mean the purchasing entity.'
        existing = [_make_binding("Buyer", "Alpha Corp")]
        facts = [_make_fact("f-001", "Buyer", 1)]
        bindings = resolve_bindings(facts, existing, text, DOC_ID)
        buyer_bindings = [b for b in bindings if b.term == "Buyer"]
        assert len(buyer_bindings) == 1
        assert buyer_bindings[0].resolves_to == "Alpha Corp"

    def test_no_definitions_returns_existing_only(self) -> None:
        text = "This is plain text with no definitions."
        existing = [_make_binding("Buyer", "Alpha Corp")]
        bindings = resolve_bindings([], existing, text, DOC_ID)
        assert len(bindings) == 1

    def test_empty_text_returns_existing(self) -> None:
        bindings = resolve_bindings([], [_make_binding("X", "Y")], "", DOC_ID)
        assert len(bindings) == 1

    def test_binding_has_document_id(self) -> None:
        text = '"Term" shall mean something.'
        facts = [_make_fact("f-001", "Term", 1)]
        bindings = resolve_bindings(facts, [], text, DOC_ID)
        for b in bindings:
            assert b.document_id == DOC_ID

    def test_binding_type_is_definition(self) -> None:
        text = '"Term" shall mean something.'
        facts = [_make_fact("f-001", "Term", 1)]
        bindings = resolve_bindings(facts, [], text, DOC_ID)
        for b in bindings:
            assert b.binding_type == BindingType.DEFINITION


class TestResolveTerm:
    def test_resolves_single_hop(self) -> None:
        bindings = [_make_binding("Buyer", "Alpha Corp")]
        assert resolve_term("Buyer", bindings) == "Alpha Corp"

    def test_resolves_chain(self) -> None:
        bindings = [
            _make_binding("Buyer", "Alpha Corp", "b-001"),
            _make_binding("Alpha Corp", "Alpha Corporation Inc", "b-002"),
        ]
        assert resolve_term("Buyer", bindings) == "Alpha Corporation Inc"

    def test_case_insensitive(self) -> None:
        bindings = [_make_binding("Buyer", "Alpha Corp")]
        assert resolve_term("buyer", bindings) == "Alpha Corp"
        assert resolve_term("BUYER", bindings) == "Alpha Corp"

    def test_unknown_term_returns_itself(self) -> None:
        bindings = [_make_binding("Buyer", "Alpha Corp")]
        assert resolve_term("Vendor", bindings) == "Vendor"

    def test_cycle_detection(self) -> None:
        bindings = [
            _make_binding("A", "B", "b-001"),
            _make_binding("B", "A", "b-002"),
        ]
        # Should not loop forever
        result = resolve_term("A", bindings)
        assert result in ("A", "B")

    def test_max_depth_respected(self) -> None:
        bindings = [
            _make_binding("A", "B", "b-001"),
            _make_binding("B", "C", "b-002"),
            _make_binding("C", "D", "b-003"),
        ]
        result = resolve_term("A", bindings, max_depth=2)
        assert result == "C"  # stops after 2 hops
