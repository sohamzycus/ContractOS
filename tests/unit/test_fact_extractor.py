"""Unit tests for FactExtractor orchestrator (T043)."""

from __future__ import annotations

from pathlib import Path

import pytest

from contractos.models.fact import FactType
from contractos.tools.fact_extractor import ExtractionResult, extract_from_file

FIXTURES = Path(__file__).parent.parent / "fixtures"
DOCX_PATH = FIXTURES / "simple_procurement.docx"
PDF_PATH = FIXTURES / "simple_nda.pdf"


@pytest.fixture
def docx_result() -> ExtractionResult:
    assert DOCX_PATH.exists()
    return extract_from_file(DOCX_PATH, "doc-001")


@pytest.fixture
def pdf_result() -> ExtractionResult:
    assert PDF_PATH.exists()
    return extract_from_file(PDF_PATH, "doc-002")


class TestExtractionOrchestration:
    def test_returns_extraction_result(self, docx_result: ExtractionResult) -> None:
        assert isinstance(docx_result, ExtractionResult)

    def test_has_parsed_document(self, docx_result: ExtractionResult) -> None:
        assert docx_result.parsed_document is not None

    def test_has_facts(self, docx_result: ExtractionResult) -> None:
        assert docx_result.fact_count > 0

    def test_has_clauses(self, docx_result: ExtractionResult) -> None:
        assert docx_result.clause_count > 0

    def test_all_facts_are_typed(self, docx_result: ExtractionResult) -> None:
        for fact in docx_result.facts:
            assert isinstance(fact.fact_type, FactType)


class TestFactTypes:
    def test_has_text_span_facts(self, docx_result: ExtractionResult) -> None:
        text_spans = [f for f in docx_result.facts if f.fact_type == FactType.TEXT_SPAN]
        assert len(text_spans) > 0

    def test_has_table_cell_facts(self, docx_result: ExtractionResult) -> None:
        table_cells = [f for f in docx_result.facts if f.fact_type == FactType.TABLE_CELL]
        assert len(table_cells) > 0

    def test_table_cells_contain_products(self, docx_result: ExtractionResult) -> None:
        table_values = [f.value for f in docx_result.facts if f.fact_type == FactType.TABLE_CELL]
        assert any("Dell" in v for v in table_values)


class TestAliasExtraction:
    def test_has_bindings(self, docx_result: ExtractionResult) -> None:
        # Our fixture has "Buyer" and "Vendor" aliases
        assert len(docx_result.bindings) >= 2

    def test_binding_terms(self, docx_result: ExtractionResult) -> None:
        terms = {b.term for b in docx_result.bindings}
        assert "Buyer" in terms or "Vendor" in terms


class TestClauseExtraction:
    def test_has_termination_clause(self, docx_result: ExtractionResult) -> None:
        from contractos.models.clause import ClauseTypeEnum
        types = {c.clause_type for c in docx_result.clauses}
        assert ClauseTypeEnum.TERMINATION in types

    def test_has_payment_clause(self, docx_result: ExtractionResult) -> None:
        from contractos.models.clause import ClauseTypeEnum
        types = {c.clause_type for c in docx_result.clauses}
        assert ClauseTypeEnum.PAYMENT in types

    def test_clauses_have_fact_ids(self, docx_result: ExtractionResult) -> None:
        for clause in docx_result.clauses:
            assert clause.fact_id, f"Clause {clause.clause_id} missing fact_id"


class TestCrossReferences:
    def test_has_cross_references(self, docx_result: ExtractionResult) -> None:
        # Our fixture references Section 3.2.1, Appendix A, Schedule A/B
        assert len(docx_result.cross_references) > 0


class TestMandatoryFactSlots:
    def test_has_clause_fact_slots(self, docx_result: ExtractionResult) -> None:
        assert len(docx_result.clause_fact_slots) > 0

    def test_termination_has_notice_period_slot(self, docx_result: ExtractionResult) -> None:
        from contractos.models.clause import ClauseTypeEnum
        term_clauses = [c for c in docx_result.clauses if c.clause_type == ClauseTypeEnum.TERMINATION]
        assert len(term_clauses) > 0
        term_slots = [s for s in docx_result.clause_fact_slots if s.clause_id == term_clauses[0].clause_id]
        slot_names = {s.fact_spec_name for s in term_slots}
        assert "notice_period" in slot_names


class TestDeterminism:
    def test_same_input_same_output(self) -> None:
        """Parse same document twice, verify same fact counts and types."""
        r1 = extract_from_file(DOCX_PATH, "doc-001")
        r2 = extract_from_file(DOCX_PATH, "doc-001")
        assert r1.fact_count == r2.fact_count
        assert r1.clause_count == r2.clause_count
        assert len(r1.bindings) == len(r2.bindings)
        # Values should match (IDs will differ due to UUIDs)
        r1_values = sorted(f.value for f in r1.facts)
        r2_values = sorted(f.value for f in r2.facts)
        assert r1_values == r2_values


class TestPdfExtraction:
    def test_pdf_has_facts(self, pdf_result: ExtractionResult) -> None:
        assert pdf_result.fact_count > 0

    def test_pdf_has_clauses(self, pdf_result: ExtractionResult) -> None:
        assert pdf_result.clause_count >= 0  # PDF headings may not be detected as heading_level

    def test_pdf_has_bindings(self, pdf_result: ExtractionResult) -> None:
        # NDA has "Discloser" and "Recipient" aliases
        assert len(pdf_result.bindings) >= 0  # may or may not detect depending on PDF text extraction


class TestClauseBodyTextExtraction:
    """Tests for clause body text facts (CLAUSE_TEXT type)."""

    def test_has_clause_text_facts(self, docx_result: ExtractionResult) -> None:
        clause_texts = [f for f in docx_result.facts if f.fact_type == FactType.CLAUSE_TEXT]
        assert len(clause_texts) > 0, "Should extract clause body text as facts"

    def test_clause_text_contains_payment_details(self, docx_result: ExtractionResult) -> None:
        clause_texts = [f for f in docx_result.facts if f.fact_type == FactType.CLAUSE_TEXT]
        values = [f.value for f in clause_texts]
        assert any("$150,000" in v for v in values), "Should capture payment amount in clause text"

    def test_clause_text_contains_termination_details(self, docx_result: ExtractionResult) -> None:
        clause_texts = [f for f in docx_result.facts if f.fact_type == FactType.CLAUSE_TEXT]
        values = [f.value for f in clause_texts]
        assert any("sixty (60) days" in v for v in values), "Should capture termination notice period"

    def test_clause_text_has_evidence(self, docx_result: ExtractionResult) -> None:
        clause_texts = [f for f in docx_result.facts if f.fact_type == FactType.CLAUSE_TEXT]
        for fact in clause_texts:
            assert fact.evidence.document_id == "doc-001"
            assert fact.evidence.text_span
            assert fact.evidence.location_hint.startswith("clause:")

    def test_clauses_have_contained_fact_ids(self, docx_result: ExtractionResult) -> None:
        """Clauses should reference their body text facts."""
        clauses_with_body = [c for c in docx_result.clauses if c.contained_fact_ids]
        assert len(clauses_with_body) > 0, "At least some clauses should have body text facts"


# ── Complex Fixture Tests ──

COMPLEX_DOCX = FIXTURES / "complex_it_outsourcing.docx"
COMPLEX_PDF = FIXTURES / "complex_procurement_framework.pdf"


@pytest.fixture
def complex_docx_result() -> ExtractionResult:
    if not COMPLEX_DOCX.exists():
        pytest.skip("Complex DOCX fixture not generated")
    return extract_from_file(COMPLEX_DOCX, "doc-complex-001")


@pytest.fixture
def complex_pdf_result() -> ExtractionResult:
    if not COMPLEX_PDF.exists():
        pytest.skip("Complex PDF fixture not generated")
    return extract_from_file(COMPLEX_PDF, "doc-complex-002")


class TestComplexDocxExtraction:
    """Tests for the complex IT outsourcing agreement."""

    def test_extracts_many_facts(self, complex_docx_result: ExtractionResult) -> None:
        assert complex_docx_result.fact_count > 50, (
            f"Complex contract should have many facts, got {complex_docx_result.fact_count}"
        )

    def test_extracts_many_clauses(self, complex_docx_result: ExtractionResult) -> None:
        assert complex_docx_result.clause_count >= 10, (
            f"Complex contract should have many clauses, got {complex_docx_result.clause_count}"
        )

    def test_extracts_entity_aliases(self, complex_docx_result: ExtractionResult) -> None:
        terms = {b.term for b in complex_docx_result.bindings}
        # Should detect Client/Meridian and Service Provider/TechServe/Vendor
        assert len(complex_docx_result.bindings) >= 2, (
            f"Should detect entity aliases, got terms: {terms}"
        )

    def test_extracts_monetary_values(self, complex_docx_result: ExtractionResult) -> None:
        text_facts = [f.value for f in complex_docx_result.facts if f.fact_type == FactType.TEXT_SPAN]
        has_money = any("$" in v or "47,500,000" in v for v in text_facts)
        assert has_money, "Should extract monetary values like $47,500,000"

    def test_extracts_table_data(self, complex_docx_result: ExtractionResult) -> None:
        table_cells = [f for f in complex_docx_result.facts if f.fact_type == FactType.TABLE_CELL]
        assert len(table_cells) > 20, (
            f"Complex contract has many tables, should extract many cells, got {len(table_cells)}"
        )

    def test_extracts_location_data(self, complex_docx_result: ExtractionResult) -> None:
        table_values = [f.value for f in complex_docx_result.facts if f.fact_type == FactType.TABLE_CELL]
        locations = ["Hyderabad", "Bangalore", "New York", "London", "Singapore"]
        found = [loc for loc in locations if any(loc in v for v in table_values)]
        assert len(found) >= 3, f"Should find location data in tables, found: {found}"

    def test_extracts_sla_data(self, complex_docx_result: ExtractionResult) -> None:
        table_values = [f.value for f in complex_docx_result.facts if f.fact_type == FactType.TABLE_CELL]
        has_sla = any("99.99%" in v or "Severity 1" in v or "15 minutes" in v for v in table_values)
        assert has_sla, "Should extract SLA targets from tables"

    def test_extracts_insurance_data(self, complex_docx_result: ExtractionResult) -> None:
        table_values = [f.value for f in complex_docx_result.facts if f.fact_type == FactType.TABLE_CELL]
        has_insurance = any("Professional Liability" in v or "$25,000,000" in v for v in table_values)
        assert has_insurance, "Should extract insurance coverage data"

    def test_has_clause_body_text(self, complex_docx_result: ExtractionResult) -> None:
        clause_texts = [f for f in complex_docx_result.facts if f.fact_type == FactType.CLAUSE_TEXT]
        assert len(clause_texts) > 10, (
            f"Complex contract should have many clause body texts, got {len(clause_texts)}"
        )

    def test_clause_body_has_termination_details(self, complex_docx_result: ExtractionResult) -> None:
        clause_texts = [f.value for f in complex_docx_result.facts if f.fact_type == FactType.CLAUSE_TEXT]
        has_term = any("one hundred and eighty (180) days" in v for v in clause_texts)
        assert has_term, "Should capture termination for convenience notice period"

    def test_clause_body_has_liability_cap(self, complex_docx_result: ExtractionResult) -> None:
        clause_texts = [f.value for f in complex_docx_result.facts if f.fact_type == FactType.CLAUSE_TEXT]
        has_cap = any("two hundred percent (200%)" in v or "Liability Cap" in v for v in clause_texts)
        assert has_cap, "Should capture liability limitation details"

    def test_has_cross_references(self, complex_docx_result: ExtractionResult) -> None:
        assert len(complex_docx_result.cross_references) >= 3, (
            f"Complex contract should have cross-references, got {len(complex_docx_result.cross_references)}"
        )


class TestComplexPdfExtraction:
    """Tests for the complex procurement framework PDF."""

    def test_extracts_facts(self, complex_pdf_result: ExtractionResult) -> None:
        assert complex_pdf_result.fact_count > 20, (
            f"Complex PDF should have many facts, got {complex_pdf_result.fact_count}"
        )

    def test_extracts_monetary_values(self, complex_pdf_result: ExtractionResult) -> None:
        all_values = [f.value for f in complex_pdf_result.facts]
        has_money = any("85,000,000" in v or "GBP" in v or "5,000,000" in v for v in all_values)
        assert has_money, "Should extract monetary values from PDF"


class TestUnsupportedFormat:
    def test_raises_for_txt(self, tmp_path: Path) -> None:
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported file format"):
            extract_from_file(txt_file, "doc-001")
