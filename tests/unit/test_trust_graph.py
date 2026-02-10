"""Unit tests for TrustGraph — SQLite-backed truth model storage."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from contractos.fabric.trust_graph import TrustGraph
from contractos.models.binding import Binding, BindingScope, BindingType
from contractos.models.clause import (
    Clause,
    ClauseTypeEnum,
    CrossReference,
    ReferenceEffect,
    ReferenceType,
)
from contractos.models.clause_type import ClauseFactSlot, SlotStatus
from contractos.models.document import Contract
from contractos.models.fact import EntityType, Fact, FactEvidence, FactType
from contractos.models.inference import Inference, InferenceType

NOW = datetime(2025, 2, 9, 12, 0, 0)
DOC_ID = "doc-001"


# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def graph() -> TrustGraph:
    g = TrustGraph(":memory:")
    yield g
    g.close()


@pytest.fixture
def contract() -> Contract:
    return Contract(
        document_id=DOC_ID,
        title="Dell Master Services Agreement",
        file_path="/contracts/dell_msa.docx",
        file_format="docx",
        file_hash="abc123",
        parties=["Dell Technologies", "Acme Corp"],
        effective_date=date(2024, 1, 1),
        page_count=42,
        word_count=15000,
        indexed_at=NOW,
        last_parsed_at=NOW,
        extraction_version="1.0.0",
    )


@pytest.fixture
def seeded_graph(graph: TrustGraph, contract: Contract) -> TrustGraph:
    """Graph with a contract already inserted."""
    graph.insert_contract(contract)
    return graph


def _make_fact(
    fact_id: str = "f-001",
    fact_type: FactType = FactType.TEXT_SPAN,
    entity_type: EntityType | None = None,
    value: str = "Net 90 from invoice date",
    doc_id: str = DOC_ID,
) -> Fact:
    return Fact(
        fact_id=fact_id,
        fact_type=fact_type,
        entity_type=entity_type,
        value=value,
        evidence=FactEvidence(
            document_id=doc_id,
            text_span=value,
            char_start=100,
            char_end=100 + len(value),
            location_hint="§5.2",
            structural_path="body > section[5]",
        ),
        extraction_method="docx_parser_v1",
        extracted_at=NOW,
    )


def _make_binding(
    binding_id: str = "b-001",
    term: str = "Supplier",
    resolves_to: str = "Dell Technologies",
    source_fact_id: str = "f-001",
    doc_id: str = DOC_ID,
) -> Binding:
    return Binding(
        binding_id=binding_id,
        binding_type=BindingType.DEFINITION,
        term=term,
        resolves_to=resolves_to,
        source_fact_id=source_fact_id,
        document_id=doc_id,
        scope=BindingScope.CONTRACT,
    )


def _make_inference(
    inference_id: str = "i-001",
    doc_id: str = DOC_ID,
) -> Inference:
    return Inference(
        inference_id=inference_id,
        inference_type=InferenceType.OBLIGATION,
        claim="Maintenance obligation for IT equipment",
        supporting_fact_ids=["f-001", "f-002"],
        reasoning_chain="§7.3 + Schedule A",
        confidence=0.92,
        confidence_basis="Direct clause + product listing",
        generated_by="document_agent_v1",
        generated_at=NOW,
        document_id=doc_id,
    )


def _make_clause(
    clause_id: str = "c-001",
    fact_id: str = "f-010",
    doc_id: str = DOC_ID,
    clause_type: ClauseTypeEnum = ClauseTypeEnum.TERMINATION,
) -> Clause:
    return Clause(
        clause_id=clause_id,
        document_id=doc_id,
        clause_type=clause_type,
        heading="12.1 Termination",
        section_number="12.1",
        fact_id=fact_id,
        contained_fact_ids=["f-011", "f-012"],
        cross_reference_ids=[],
        classification_method="pattern_match",
        classification_confidence=0.95,
    )


def _make_cross_reference(
    reference_id: str = "xr-001",
    source_clause_id: str = "c-001",
    source_fact_id: str = "f-025",
) -> CrossReference:
    return CrossReference(
        reference_id=reference_id,
        source_clause_id=source_clause_id,
        target_reference="section 3.2.1",
        reference_type=ReferenceType.SECTION_REF,
        effect=ReferenceEffect.CONDITIONS,
        context="the notice period as mentioned in section 3.2.1",
        source_fact_id=source_fact_id,
    )


# ── Contract CRUD ──────────────────────────────────────────────────


class TestContractCRUD:
    def test_insert_and_get(self, seeded_graph: TrustGraph, contract: Contract) -> None:
        result = seeded_graph.get_contract(DOC_ID)
        assert result is not None
        assert result.document_id == DOC_ID
        assert result.title == contract.title
        assert result.parties == ["Dell Technologies", "Acme Corp"]
        assert result.page_count == 42

    def test_get_nonexistent(self, graph: TrustGraph) -> None:
        assert graph.get_contract("no-such-doc") is None

    def test_upsert_replaces(self, seeded_graph: TrustGraph, contract: Contract) -> None:
        updated = contract.model_copy(update={"title": "Updated Title"})
        seeded_graph.insert_contract(updated)
        result = seeded_graph.get_contract(DOC_ID)
        assert result is not None
        assert result.title == "Updated Title"


# ── Fact CRUD ──────────────────────────────────────────────────────


class TestFactCRUD:
    def test_insert_and_get_by_id(self, seeded_graph: TrustGraph) -> None:
        fact = _make_fact()
        seeded_graph.insert_fact(fact)
        result = seeded_graph.get_fact("f-001")
        assert result is not None
        assert result.fact_id == "f-001"
        assert result.fact_type == FactType.TEXT_SPAN
        assert result.value == "Net 90 from invoice date"
        assert result.evidence.document_id == DOC_ID

    def test_get_nonexistent(self, seeded_graph: TrustGraph) -> None:
        assert seeded_graph.get_fact("no-such-fact") is None

    def test_get_by_document(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(_make_fact("f-001"))
        seeded_graph.insert_fact(_make_fact("f-002", value="Another fact"))
        facts = seeded_graph.get_facts_by_document(DOC_ID)
        assert len(facts) == 2

    def test_get_by_document_empty(self, seeded_graph: TrustGraph) -> None:
        facts = seeded_graph.get_facts_by_document(DOC_ID)
        assert facts == []

    def test_filter_by_fact_type(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(_make_fact("f-001", fact_type=FactType.TEXT_SPAN))
        seeded_graph.insert_fact(
            _make_fact("f-002", fact_type=FactType.ENTITY, entity_type=EntityType.PARTY, value="Dell")
        )
        text_facts = seeded_graph.get_facts_by_document(DOC_ID, fact_type=FactType.TEXT_SPAN)
        assert len(text_facts) == 1
        assert text_facts[0].fact_type == FactType.TEXT_SPAN

    def test_filter_by_entity_type(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(
            _make_fact("f-001", fact_type=FactType.ENTITY, entity_type=EntityType.PARTY, value="Dell")
        )
        seeded_graph.insert_fact(
            _make_fact("f-002", fact_type=FactType.ENTITY, entity_type=EntityType.LOCATION, value="Bangalore")
        )
        party_facts = seeded_graph.get_facts_by_document(DOC_ID, entity_type=EntityType.PARTY)
        assert len(party_facts) == 1
        assert party_facts[0].entity_type == EntityType.PARTY

    def test_count_facts(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(_make_fact("f-001"))
        seeded_graph.insert_fact(_make_fact("f-002", value="Another"))
        assert seeded_graph.count_facts(DOC_ID) == 2

    def test_count_facts_empty(self, seeded_graph: TrustGraph) -> None:
        assert seeded_graph.count_facts(DOC_ID) == 0

    def test_idempotent_reinsert(self, seeded_graph: TrustGraph) -> None:
        fact = _make_fact()
        seeded_graph.insert_fact(fact)
        seeded_graph.insert_fact(fact)  # same id — should replace
        assert seeded_graph.count_facts(DOC_ID) == 1

    def test_insert_facts_batch(self, seeded_graph: TrustGraph) -> None:
        facts = [_make_fact("f-001"), _make_fact("f-002", value="Other")]
        seeded_graph.insert_facts(facts)
        assert seeded_graph.count_facts(DOC_ID) == 2

    def test_delete_by_document(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(_make_fact("f-001"))
        seeded_graph.insert_fact(_make_fact("f-002", value="Other"))
        deleted = seeded_graph.delete_facts_by_document(DOC_ID)
        assert deleted == 2
        assert seeded_graph.count_facts(DOC_ID) == 0

    def test_delete_by_document_returns_zero(self, seeded_graph: TrustGraph) -> None:
        assert seeded_graph.delete_facts_by_document("no-doc") == 0

    def test_entity_type_preserved(self, seeded_graph: TrustGraph) -> None:
        fact = _make_fact("f-001", fact_type=FactType.ENTITY, entity_type=EntityType.PRODUCT, value="Dell Inspiron")
        seeded_graph.insert_fact(fact)
        result = seeded_graph.get_fact("f-001")
        assert result is not None
        assert result.entity_type == EntityType.PRODUCT

    def test_null_entity_type_for_non_entity(self, seeded_graph: TrustGraph) -> None:
        fact = _make_fact("f-001", fact_type=FactType.TEXT_SPAN)
        seeded_graph.insert_fact(fact)
        result = seeded_graph.get_fact("f-001")
        assert result is not None
        assert result.entity_type is None


# ── Binding CRUD ───────────────────────────────────────────────────


class TestBindingCRUD:
    def test_insert_and_get(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(_make_fact("f-001"))
        binding = _make_binding()
        seeded_graph.insert_binding(binding)
        result = seeded_graph.get_binding("b-001")
        assert result is not None
        assert result.term == "Supplier"
        assert result.resolves_to == "Dell Technologies"

    def test_get_nonexistent(self, seeded_graph: TrustGraph) -> None:
        assert seeded_graph.get_binding("no-such") is None

    def test_get_by_document(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(_make_fact("f-001"))
        seeded_graph.insert_fact(_make_fact("f-002", value="Other"))
        seeded_graph.insert_binding(_make_binding("b-001", source_fact_id="f-001"))
        seeded_graph.insert_binding(_make_binding("b-002", term="Buyer", resolves_to="Acme", source_fact_id="f-002"))
        bindings = seeded_graph.get_bindings_by_document(DOC_ID)
        assert len(bindings) == 2

    def test_get_by_term_case_insensitive(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(_make_fact("f-001"))
        seeded_graph.insert_binding(_make_binding())
        result = seeded_graph.get_binding_by_term(DOC_ID, "supplier")
        assert result is not None
        assert result.term == "Supplier"

    def test_get_by_term_no_match(self, seeded_graph: TrustGraph) -> None:
        assert seeded_graph.get_binding_by_term(DOC_ID, "nonexistent") is None


# ── Inference CRUD ─────────────────────────────────────────────────


class TestInferenceCRUD:
    def test_insert_and_get_by_document(self, seeded_graph: TrustGraph) -> None:
        inference = _make_inference()
        seeded_graph.insert_inference(inference)
        results = seeded_graph.get_inferences_by_document(DOC_ID)
        assert len(results) == 1
        assert results[0].inference_id == "i-001"
        assert results[0].confidence == 0.92
        assert results[0].supporting_fact_ids == ["f-001", "f-002"]

    def test_empty_inferences(self, seeded_graph: TrustGraph) -> None:
        assert seeded_graph.get_inferences_by_document(DOC_ID) == []

    def test_json_roundtrip_for_lists(self, seeded_graph: TrustGraph) -> None:
        inf = _make_inference()
        seeded_graph.insert_inference(inf)
        result = seeded_graph.get_inferences_by_document(DOC_ID)[0]
        assert result.supporting_fact_ids == ["f-001", "f-002"]
        assert result.supporting_binding_ids == []
        assert result.domain_sources == []


# ── Clause CRUD ────────────────────────────────────────────────────


class TestClauseCRUD:
    def test_insert_and_get_by_document(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(_make_fact("f-010", value="Termination clause text"))
        clause = _make_clause()
        seeded_graph.insert_clause(clause)
        results = seeded_graph.get_clauses_by_document(DOC_ID)
        assert len(results) == 1
        assert results[0].clause_id == "c-001"
        assert results[0].clause_type == ClauseTypeEnum.TERMINATION

    def test_filter_by_clause_type(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(_make_fact("f-010", value="Termination text"))
        seeded_graph.insert_fact(_make_fact("f-020", value="Payment text"))
        seeded_graph.insert_clause(_make_clause("c-001", fact_id="f-010", clause_type=ClauseTypeEnum.TERMINATION))
        seeded_graph.insert_clause(_make_clause("c-002", fact_id="f-020", clause_type=ClauseTypeEnum.PAYMENT))
        term_clauses = seeded_graph.get_clauses_by_document(DOC_ID, clause_type=ClauseTypeEnum.TERMINATION)
        assert len(term_clauses) == 1
        assert term_clauses[0].clause_type == ClauseTypeEnum.TERMINATION

    def test_empty_clauses(self, seeded_graph: TrustGraph) -> None:
        assert seeded_graph.get_clauses_by_document(DOC_ID) == []

    def test_json_roundtrip_contained_facts(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(_make_fact("f-010", value="Clause text"))
        seeded_graph.insert_clause(_make_clause())
        result = seeded_graph.get_clauses_by_document(DOC_ID)[0]
        assert result.contained_fact_ids == ["f-011", "f-012"]


# ── CrossReference CRUD ────────────────────────────────────────────


class TestCrossReferenceCRUD:
    def test_insert_and_get_by_clause(self, seeded_graph: TrustGraph) -> None:
        # Set up required parent records
        seeded_graph.insert_fact(_make_fact("f-010", value="Clause text"))
        seeded_graph.insert_fact(_make_fact("f-025", value="Reference text"))
        seeded_graph.insert_clause(_make_clause("c-001", fact_id="f-010"))
        xref = _make_cross_reference()
        seeded_graph.insert_cross_reference(xref)
        results = seeded_graph.get_cross_references_by_clause("c-001")
        assert len(results) == 1
        assert results[0].reference_id == "xr-001"
        assert results[0].reference_type == ReferenceType.SECTION_REF
        assert results[0].effect == ReferenceEffect.CONDITIONS
        assert results[0].resolved is False

    def test_empty_cross_references(self, seeded_graph: TrustGraph) -> None:
        assert seeded_graph.get_cross_references_by_clause("c-999") == []


# ── ClauseFactSlot CRUD ────────────────────────────────────────────


class TestClauseFactSlotCRUD:
    def test_insert_and_get(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(_make_fact("f-010", value="Clause text"))
        seeded_graph.insert_clause(_make_clause("c-001", fact_id="f-010"))
        slot = ClauseFactSlot(
            clause_id="c-001",
            fact_spec_name="notice_period",
            status=SlotStatus.FILLED,
            filled_by_fact_id="f-010",
            required=True,
        )
        seeded_graph.insert_clause_fact_slot(slot)
        results = seeded_graph.get_clause_fact_slots("c-001")
        assert len(results) == 1
        assert results[0].fact_spec_name == "notice_period"
        assert results[0].status == SlotStatus.FILLED

    def test_missing_slot(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(_make_fact("f-010", value="Clause text"))
        seeded_graph.insert_clause(_make_clause("c-001", fact_id="f-010"))
        slot = ClauseFactSlot(
            clause_id="c-001",
            fact_spec_name="termination_reasons",
            status=SlotStatus.MISSING,
            required=True,
        )
        seeded_graph.insert_clause_fact_slot(slot)
        results = seeded_graph.get_clause_fact_slots("c-001")
        assert len(results) == 1
        assert results[0].status == SlotStatus.MISSING
        assert results[0].filled_by_fact_id is None

    def test_get_missing_slots_by_document(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(_make_fact("f-010", value="Clause text"))
        seeded_graph.insert_clause(_make_clause("c-001", fact_id="f-010"))
        # One filled, one missing (required), one missing (optional)
        seeded_graph.insert_clause_fact_slot(ClauseFactSlot(
            clause_id="c-001", fact_spec_name="notice_period",
            status=SlotStatus.FILLED, filled_by_fact_id="f-010", required=True,
        ))
        seeded_graph.insert_clause_fact_slot(ClauseFactSlot(
            clause_id="c-001", fact_spec_name="termination_reasons",
            status=SlotStatus.MISSING, required=True,
        ))
        seeded_graph.insert_clause_fact_slot(ClauseFactSlot(
            clause_id="c-001", fact_spec_name="optional_note",
            status=SlotStatus.MISSING, required=False,
        ))
        missing = seeded_graph.get_missing_slots_by_document(DOC_ID)
        # Only required missing slots
        assert len(missing) == 1
        assert missing[0].fact_spec_name == "termination_reasons"

    def test_empty_slots(self, seeded_graph: TrustGraph) -> None:
        assert seeded_graph.get_clause_fact_slots("c-999") == []


# ── Cascade / Integrity ───────────────────────────────────────────


class TestCascadeAndIntegrity:
    def test_facts_cascade_on_contract_delete(self, seeded_graph: TrustGraph) -> None:
        """Deleting a contract should cascade-delete its facts."""
        seeded_graph.insert_fact(_make_fact("f-001"))
        # Delete the contract
        seeded_graph._conn.execute("DELETE FROM contracts WHERE document_id = ?", (DOC_ID,))
        seeded_graph._conn.commit()
        assert seeded_graph.get_fact("f-001") is None

    def test_clauses_cascade_on_contract_delete(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(_make_fact("f-010", value="Clause text"))
        seeded_graph.insert_clause(_make_clause("c-001", fact_id="f-010"))
        seeded_graph._conn.execute("DELETE FROM contracts WHERE document_id = ?", (DOC_ID,))
        seeded_graph._conn.commit()
        assert seeded_graph.get_clauses_by_document(DOC_ID) == []

    def test_cross_refs_cascade_on_clause_delete(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(_make_fact("f-010", value="Clause text"))
        seeded_graph.insert_fact(_make_fact("f-025", value="Ref text"))
        seeded_graph.insert_clause(_make_clause("c-001", fact_id="f-010"))
        seeded_graph.insert_cross_reference(_make_cross_reference())
        # Delete the clause
        seeded_graph._conn.execute("DELETE FROM clauses WHERE clause_id = ?", ("c-001",))
        seeded_graph._conn.commit()
        assert seeded_graph.get_cross_references_by_clause("c-001") == []

    def test_clause_fact_slots_cascade_on_clause_delete(self, seeded_graph: TrustGraph) -> None:
        seeded_graph.insert_fact(_make_fact("f-010", value="Clause text"))
        seeded_graph.insert_clause(_make_clause("c-001", fact_id="f-010"))
        seeded_graph.insert_clause_fact_slot(ClauseFactSlot(
            clause_id="c-001", fact_spec_name="notice_period",
            status=SlotStatus.MISSING, required=True,
        ))
        seeded_graph._conn.execute("DELETE FROM clauses WHERE clause_id = ?", ("c-001",))
        seeded_graph._conn.commit()
        assert seeded_graph.get_clause_fact_slots("c-001") == []
