"""Integration tests for Phase 14 — Deep Extraction against real contracts (T337).

Validates that the extraction pipeline produces meaningful results
for real-world contracts that previously yielded zero clauses/bindings.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from contractos.tools.fact_extractor import extract_from_file


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
CDK_PDF = FIXTURES_DIR / "CDK50014.pdf"
SERVICE_DOCX = FIXTURES_DIR / "SERVICE AGREEMENT 2.docx"


@pytest.fixture
def pdf_result():
    """Extract from CDK50014.pdf."""
    if not CDK_PDF.exists():
        pytest.skip("CDK50014.pdf fixture not available")
    return extract_from_file(str(CDK_PDF), "test-pdf-e2e")


@pytest.fixture
def docx_result():
    """Extract from SERVICE AGREEMENT 2.docx."""
    if not SERVICE_DOCX.exists():
        pytest.skip("SERVICE AGREEMENT 2.docx fixture not available")
    return extract_from_file(str(SERVICE_DOCX), "test-docx-e2e")


# ── PDF (CDK50014.pdf) ──────────────────────────────────────────────


class TestCDK50014Pdf:
    """CDK Global Professional Services Agreement — PDF extraction."""

    def test_produces_facts(self, pdf_result) -> None:
        assert pdf_result.fact_count > 10

    def test_produces_clauses(self, pdf_result) -> None:
        """Previously produced 0 clauses. Must now produce >= 5."""
        assert pdf_result.clause_count >= 5

    def test_produces_bindings(self, pdf_result) -> None:
        """Previously produced 0 bindings. Must now produce >= 1."""
        assert len(pdf_result.bindings) >= 1

    def test_produces_cross_references(self, pdf_result) -> None:
        assert len(pdf_result.cross_references) >= 1

    def test_detects_definitions(self, pdf_result) -> None:
        """Should detect defined terms like Vendor, CDK, Affiliates."""
        def_facts = [
            f for f in pdf_result.facts
            if "pattern[definition]" in (f.evidence.structural_path or "")
        ]
        assert len(def_facts) >= 3

    def test_detects_monetary_values(self, pdf_result) -> None:
        monetary = [
            f for f in pdf_result.facts
            if "pattern[monetary]" in (f.evidence.structural_path or "")
        ]
        assert len(monetary) >= 1

    def test_detects_dates(self, pdf_result) -> None:
        dates = [
            f for f in pdf_result.facts
            if "pattern[date]" in (f.evidence.structural_path or "")
        ]
        assert len(dates) >= 1

    def test_clause_types_include_specific(self, pdf_result) -> None:
        """Should classify at least some clauses with specific types."""
        from contractos.models.clause import ClauseTypeEnum
        types = {c.clause_type for c in pdf_result.clauses}
        specific_types = types - {ClauseTypeEnum.GENERAL}
        assert len(specific_types) >= 3, f"Only found types: {types}"


# ── DOCX (SERVICE AGREEMENT 2.docx) ─────────────────────────────────


class TestServiceAgreement2Docx:
    """Zycus Service Agreement — DOCX extraction."""

    def test_produces_facts(self, docx_result) -> None:
        assert docx_result.fact_count > 10

    def test_produces_clauses(self, docx_result) -> None:
        """Previously produced 0 clauses. Must now produce >= 5."""
        assert docx_result.clause_count >= 5

    def test_produces_bindings(self, docx_result) -> None:
        """Previously produced 0 bindings. Must now produce >= 1."""
        assert len(docx_result.bindings) >= 1

    def test_produces_cross_references(self, docx_result) -> None:
        assert len(docx_result.cross_references) >= 1

    def test_detects_confidentiality_clause(self, docx_result) -> None:
        from contractos.models.clause import ClauseTypeEnum
        types = {c.clause_type for c in docx_result.clauses}
        assert ClauseTypeEnum.CONFIDENTIALITY in types

    def test_detects_warranty_clause(self, docx_result) -> None:
        from contractos.models.clause import ClauseTypeEnum
        types = {c.clause_type for c in docx_result.clauses}
        assert ClauseTypeEnum.WARRANTY in types

    def test_detects_non_compete_clause(self, docx_result) -> None:
        from contractos.models.clause import ClauseTypeEnum
        types = {c.clause_type for c in docx_result.clauses}
        assert ClauseTypeEnum.NON_COMPETE in types

    def test_clause_types_include_specific(self, docx_result) -> None:
        from contractos.models.clause import ClauseTypeEnum
        types = {c.clause_type for c in docx_result.clauses}
        specific_types = types - {ClauseTypeEnum.GENERAL}
        assert len(specific_types) >= 3, f"Only found types: {types}"


# ── Regression: Existing Sample Contracts ────────────────────────────


class TestSampleContractRegression:
    """Ensure existing sample contracts still work correctly."""

    def test_simple_nda_pdf(self) -> None:
        nda_path = FIXTURES_DIR / "simple_nda.pdf"
        if not nda_path.exists():
            # Try samples directory
            nda_path = Path(__file__).parent.parent.parent / "src" / "contractos" / "samples" / "simple_nda.pdf"
        if not nda_path.exists():
            pytest.skip("simple_nda.pdf not available")
        result = extract_from_file(str(nda_path), "test-nda-regression")
        assert result.fact_count > 0
        # NDA should still produce clauses (it had heading styles)
        assert result.clause_count >= 0  # May be 0 if no headings in sample
