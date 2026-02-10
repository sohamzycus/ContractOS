"""Unit tests for Binding model (T010)."""

import pytest
from pydantic import ValidationError

from contractos.models.binding import Binding, BindingScope, BindingType


class TestBindingType:
    def test_all_types_exist(self):
        expected = {"definition", "assignment", "incorporation", "delegation", "scope_limitation"}
        assert {t.value for t in BindingType} == expected


class TestBindingScope:
    def test_all_scopes_exist(self):
        expected = {"contract", "contract_family", "repository"}
        assert {s.value for s in BindingScope} == expected


class TestBinding:
    def test_valid_binding(self, sample_binding):
        assert sample_binding.term == "Supplier"
        assert sample_binding.resolves_to == "Dell Technologies Inc and its affiliates"
        assert sample_binding.scope == BindingScope.CONTRACT
        assert sample_binding.is_overridden_by is None

    def test_default_scope_is_contract(self):
        b = Binding(
            binding_id="b-test",
            binding_type=BindingType.DEFINITION,
            term="X",
            resolves_to="Y",
            source_fact_id="f-1",
            document_id="doc-1",
        )
        assert b.scope == BindingScope.CONTRACT

    def test_override_chain(self):
        original = Binding(
            binding_id="b-1",
            binding_type=BindingType.DEFINITION,
            term="Payment Terms",
            resolves_to="Net 90",
            source_fact_id="f-1",
            document_id="doc-1",
            is_overridden_by="b-2",
        )
        override = Binding(
            binding_id="b-2",
            binding_type=BindingType.ASSIGNMENT,
            term="Payment Terms",
            resolves_to="Net 60",
            source_fact_id="f-2",
            document_id="doc-2",
        )
        assert original.is_overridden_by == override.binding_id

    def test_empty_term_rejected(self):
        with pytest.raises(ValidationError):
            Binding(
                binding_id="b-bad",
                binding_type=BindingType.DEFINITION,
                term="",
                resolves_to="Y",
                source_fact_id="f-1",
                document_id="doc-1",
            )

    def test_serialization_roundtrip(self, sample_binding):
        data = sample_binding.model_dump()
        restored = Binding.model_validate(data)
        assert restored == sample_binding
