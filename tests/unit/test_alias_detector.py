"""Unit tests for entity alias detector (T048)."""

from __future__ import annotations

import pytest

from contractos.models.binding import BindingType
from contractos.models.fact import FactType
from contractos.tools.alias_detector import detect_aliases


class TestAliasDetector:
    def test_hereinafter_referred_to_as(self) -> None:
        text = 'Alpha Corp, hereinafter referred to as "Buyer", and Beta Ltd, hereinafter referred to as "Vendor".'
        facts, bindings = detect_aliases(text, "doc-001")
        assert len(facts) == 2
        assert len(bindings) == 2

    def test_the_pattern(self) -> None:
        text = 'Gamma Inc (the "Discloser") and Delta LLC (the "Recipient").'
        facts, bindings = detect_aliases(text, "doc-001")
        assert len(facts) >= 2
        assert len(bindings) >= 2

    def test_hereafter_pattern(self) -> None:
        text = "Beta Services Ltd, hereafter 'Vendor'"
        facts, bindings = detect_aliases(text, "doc-001")
        assert len(facts) >= 1
        assert len(bindings) >= 1

    def test_binding_term_and_resolves_to(self) -> None:
        text = 'Alpha Corp, hereinafter referred to as "Buyer"'
        facts, bindings = detect_aliases(text, "doc-001")
        assert bindings[0].term == "Buyer"
        assert bindings[0].resolves_to == "Alpha Corp"

    def test_binding_type_is_definition(self) -> None:
        text = 'Alpha Corp, hereinafter referred to as "Buyer"'
        _, bindings = detect_aliases(text, "doc-001")
        assert bindings[0].binding_type == BindingType.DEFINITION

    def test_fact_type_is_entity(self) -> None:
        text = 'Alpha Corp, hereinafter referred to as "Buyer"'
        facts, _ = detect_aliases(text, "doc-001")
        assert facts[0].fact_type == FactType.ENTITY

    def test_fact_references_document(self) -> None:
        text = 'Alpha Corp, hereinafter referred to as "Buyer"'
        facts, _ = detect_aliases(text, "doc-001")
        assert facts[0].evidence.document_id == "doc-001"

    def test_binding_source_fact_id_matches(self) -> None:
        text = 'Alpha Corp, hereinafter referred to as "Buyer"'
        facts, bindings = detect_aliases(text, "doc-001")
        assert bindings[0].source_fact_id == facts[0].fact_id

    def test_no_aliases_returns_empty(self) -> None:
        text = "This is a plain paragraph with no aliases."
        facts, bindings = detect_aliases(text, "doc-001")
        assert facts == []
        assert bindings == []

    def test_char_offsets_valid(self) -> None:
        text = 'Alpha Corp, hereinafter referred to as "Buyer"'
        facts, _ = detect_aliases(text, "doc-001")
        for f in facts:
            assert f.evidence.char_start >= 0
            assert f.evidence.char_end > f.evidence.char_start
            assert f.evidence.text_span in text
