"""Unit tests for mandatory fact extractor (T047)."""

from __future__ import annotations

import pytest

from contractos.models.clause import Clause, ClauseTypeEnum
from contractos.models.clause_type import SlotStatus
from contractos.tools.mandatory_fact_extractor import extract_mandatory_facts


def _make_clause(
    clause_type: ClauseTypeEnum,
    clause_id: str = "c-001",
) -> Clause:
    return Clause(
        clause_id=clause_id,
        document_id="doc-001",
        clause_type=clause_type,
        heading=f"Test {clause_type.value}",
        fact_id="",
        contained_fact_ids=[],
        cross_reference_ids=[],
        classification_method="test",
    )


class TestTerminationSlots:
    def test_partial_when_text_has_notice_and_reasons_but_no_linked_facts(self) -> None:
        clause = _make_clause(ClauseTypeEnum.TERMINATION)
        text = (
            "Either party may terminate by providing sixty (60) days written notice. "
            "Termination may occur for material breach, insolvency, or mutual agreement."
        )
        slots = extract_mandatory_facts(clause, text)
        slot_map = {s.fact_spec_name: s for s in slots}
        # PARTIAL because text evidence found but no linked fact
        assert slot_map["notice_period"].status == SlotStatus.PARTIAL
        assert slot_map["termination_reasons"].status == SlotStatus.PARTIAL

    def test_missing_when_text_lacks_notice(self) -> None:
        clause = _make_clause(ClauseTypeEnum.TERMINATION)
        text = "This agreement may be terminated."
        slots = extract_mandatory_facts(clause, text)
        slot_map = {s.fact_spec_name: s for s in slots}
        assert slot_map["notice_period"].status == SlotStatus.MISSING
        assert slot_map["notice_period"].required is True

    def test_optional_slots_can_be_missing(self) -> None:
        clause = _make_clause(ClauseTypeEnum.TERMINATION)
        text = "Terminate with 30 days notice for breach."
        slots = extract_mandatory_facts(clause, text)
        slot_map = {s.fact_spec_name: s for s in slots}
        # cure_period is optional
        assert slot_map["cure_period"].required is False


class TestPaymentSlots:
    def test_partial_when_amount_and_schedule_present(self) -> None:
        clause = _make_clause(ClauseTypeEnum.PAYMENT)
        text = "The Buyer shall pay $150,000.00. Payment due Net 90 from invoice date."
        slots = extract_mandatory_facts(clause, text)
        slot_map = {s.fact_spec_name: s for s in slots}
        assert slot_map["payment_amount"].status == SlotStatus.PARTIAL
        assert slot_map["payment_schedule"].status == SlotStatus.PARTIAL

    def test_missing_when_no_amount(self) -> None:
        clause = _make_clause(ClauseTypeEnum.PAYMENT)
        text = "Payment shall be made monthly."
        slots = extract_mandatory_facts(clause, text)
        slot_map = {s.fact_spec_name: s for s in slots}
        assert slot_map["payment_amount"].status == SlotStatus.MISSING


class TestConfidentialitySlots:
    def test_partial_when_duration_and_definition_present(self) -> None:
        clause = _make_clause(ClauseTypeEnum.CONFIDENTIALITY)
        text = (
            "Confidential Information includes all trade secrets. "
            "Obligations last for twenty-four (24) months."
        )
        slots = extract_mandatory_facts(clause, text)
        slot_map = {s.fact_spec_name: s for s in slots}
        assert slot_map["confidentiality_duration"].status == SlotStatus.PARTIAL
        assert slot_map["confidential_information_definition"].status == SlotStatus.PARTIAL


class TestUnregisteredClauseType:
    def test_returns_empty_for_general(self) -> None:
        clause = _make_clause(ClauseTypeEnum.GENERAL)
        slots = extract_mandatory_facts(clause, "Some general text.")
        assert slots == []

    def test_returns_empty_for_scope(self) -> None:
        clause = _make_clause(ClauseTypeEnum.SCOPE)
        slots = extract_mandatory_facts(clause, "Scope of services.")
        assert slots == []


class TestSlotProperties:
    def test_all_slots_have_clause_id(self) -> None:
        clause = _make_clause(ClauseTypeEnum.TERMINATION, clause_id="c-test")
        text = "Terminate with 30 days notice for breach."
        slots = extract_mandatory_facts(clause, text)
        for slot in slots:
            assert slot.clause_id == "c-test"

    def test_filled_by_fact_id_is_none_when_no_existing_facts(self) -> None:
        clause = _make_clause(ClauseTypeEnum.TERMINATION)
        text = "Terminate with 30 days notice for breach."
        slots = extract_mandatory_facts(clause, text)
        for slot in slots:
            # Without existing facts, slots are PARTIAL or MISSING, never FILLED
            assert slot.filled_by_fact_id is None
            assert slot.status in (SlotStatus.PARTIAL, SlotStatus.MISSING)
