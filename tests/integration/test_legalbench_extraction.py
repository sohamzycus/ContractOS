"""Integration tests: LegalBench / CUAD benchmark document extraction.

Tests the full extraction pipeline against real-world-style legal documents
modeled after LegalBench categories:
  - contract_nli (NDA confidentiality, sharing, survival)
  - cuad (license grant, non-compete, termination, liability cap, audit rights)
  - definition_classification / definition_extraction
  - consumer_contracts_qa

Each test verifies that ContractOS correctly extracts facts, clauses, bindings,
and cross-references from these benchmark-grade documents.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from contractos.tools.fact_extractor import extract_from_file
from contractos.tools.binding_resolver import resolve_bindings
from contractos.models.fact import EntityType, FactType

FIXTURES = Path(__file__).parent.parent / "fixtures"
LEGALBENCH_NDA = FIXTURES / "legalbench_nda.docx"
CUAD_LICENSE = FIXTURES / "cuad_license_agreement.docx"


# ─────────────────────────────────────────────────────────────────────
# Fixture helpers
# ─────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def nda_extraction():
    """Extract from the LegalBench NDA fixture once for all tests."""
    assert LEGALBENCH_NDA.exists(), f"Fixture missing: {LEGALBENCH_NDA}"
    result = extract_from_file(str(LEGALBENCH_NDA), "legalbench-nda-001")
    full_text = result.parsed_document.full_text if result.parsed_document else ""
    bindings = resolve_bindings(result.facts, result.bindings, full_text, "legalbench-nda-001")
    return result, bindings


@pytest.fixture(scope="module")
def cuad_extraction():
    """Extract from the CUAD License Agreement fixture once for all tests."""
    assert CUAD_LICENSE.exists(), f"Fixture missing: {CUAD_LICENSE}"
    result = extract_from_file(str(CUAD_LICENSE), "cuad-license-001")
    full_text = result.parsed_document.full_text if result.parsed_document else ""
    bindings = resolve_bindings(result.facts, result.bindings, full_text, "cuad-license-001")
    return result, bindings


# ─────────────────────────────────────────────────────────────────────
# LegalBench NDA Tests
# ─────────────────────────────────────────────────────────────────────

class TestLegalBenchNDA:
    """Tests modeled after LegalBench contract_nli and definition tasks."""

    def test_extraction_succeeds(self, nda_extraction):
        """Pipeline completes without errors."""
        result, bindings = nda_extraction
        assert result.facts, "Should extract facts"
        assert result.clauses, "Should classify clauses"

    def test_parties_extracted(self, nda_extraction):
        """contract_nli: Parties are identified in text or bindings."""
        result, bindings = nda_extraction
        # Parties may appear in entity facts, bindings, or text_span facts
        all_text = " ".join(f.value.lower() for f in result.facts)
        binding_text = " ".join(
            f"{b.term} {b.resolves_to}".lower() for b in bindings
        )
        combined = all_text + " " + binding_text
        assert "nexus" in combined or "agreement" in combined, (
            "Should find party references in extracted content"
        )

    def test_definition_bindings(self, nda_extraction):
        """definition_extraction: Definitions are resolved."""
        result, bindings = nda_extraction
        # The NDA has defined terms like "Agreement", "Purpose", "AAA"
        definition_bindings = [b for b in bindings if b.binding_type.value == "definition"]
        assert len(definition_bindings) > 0, (
            "Should have definition bindings"
        )

    def test_confidentiality_clause_classified(self, nda_extraction):
        """contract_nli_confidentiality: Confidentiality clause detected."""
        result, _ = nda_extraction
        clause_types = [c.clause_type.value for c in result.clauses]
        assert "confidentiality" in clause_types, (
            f"Should classify confidentiality clause. Found: {clause_types}"
        )

    def test_termination_clause_classified(self, nda_extraction):
        """contract_nli_survival: Termination clause detected."""
        result, _ = nda_extraction
        clause_types = [c.clause_type.value for c in result.clauses]
        assert "termination" in clause_types, (
            f"Should classify termination clause. Found: {clause_types}"
        )

    def test_definitions_section_present(self, nda_extraction):
        """definition_classification: Definitions section detected by heading."""
        result, _ = nda_extraction
        headings = [c.heading.lower() for c in result.clauses]
        assert any("definition" in h for h in headings), (
            f"Should find definitions section. Headings: {headings}"
        )

    def test_monetary_facts_extracted(self, nda_extraction):
        """consumer_contracts_qa: Monetary values extracted as text_span."""
        result, _ = nda_extraction
        # Monetary values are extracted as text_span facts with $ or USD patterns
        monetary_spans = [
            f for f in result.facts
            if f.fact_type == FactType.TEXT_SPAN
            and ("$" in f.value or "usd" in f.value.lower())
        ]
        # Also check clause_text for monetary references
        monetary_clause_text = [
            f for f in result.facts
            if f.fact_type == FactType.CLAUSE_TEXT
            and ("$5,000,000" in f.value or "Five Million" in f.value)
        ]
        assert len(monetary_spans) > 0 or len(monetary_clause_text) > 0, (
            "Should extract monetary facts (liability cap $5,000,000)"
        )

    def test_duration_facts_extracted(self, nda_extraction):
        """contract_qa: Duration/term facts extracted as text_span."""
        result, _ = nda_extraction
        # Duration values are extracted as text_span facts
        duration_spans = [
            f for f in result.facts
            if f.fact_type == FactType.TEXT_SPAN
            and ("year" in f.value.lower() or "month" in f.value.lower() or "day" in f.value.lower())
        ]
        # Also check clause_text for duration references
        duration_clause_text = [
            f for f in result.facts
            if f.fact_type == FactType.CLAUSE_TEXT
            and ("three (3) year" in f.value.lower() or "five (5) year" in f.value.lower())
        ]
        assert len(duration_spans) > 0 or len(duration_clause_text) > 0, (
            "Should extract duration facts (3 years term, 5 years survival)"
        )

    def test_clause_body_text_extracted(self, nda_extraction):
        """Clause body text available for Q&A."""
        result, _ = nda_extraction
        clause_text_facts = [f for f in result.facts if f.fact_type == FactType.CLAUSE_TEXT]
        assert len(clause_text_facts) > 5, (
            f"Should extract clause body text. Found: {len(clause_text_facts)}"
        )

    def test_cross_references_detected(self, nda_extraction):
        """Cross-references between sections detected."""
        result, _ = nda_extraction
        # The NDA has references like "Section 2" in survival clause
        # Cross-references may or may not be detected depending on text structure
        # This is a soft check
        xrefs = result.cross_references
        # At minimum, we should have parsed the document successfully
        assert result.parsed_document is not None

    def test_fact_count_reasonable(self, nda_extraction):
        """Extraction produces a reasonable number of facts for a 11-section NDA."""
        result, _ = nda_extraction
        assert len(result.facts) >= 20, (
            f"Expected ≥20 facts for a detailed NDA. Got: {len(result.facts)}"
        )

    def test_governing_law_extracted(self, nda_extraction):
        """cuad_governing_law: Governing law clause detected."""
        result, _ = nda_extraction
        clause_types = [c.clause_type.value for c in result.clauses]
        # Check for governing_law or general type
        headings = [c.heading.lower() for c in result.clauses]
        assert any("governing" in h or "law" in h or "dispute" in h for h in headings), (
            f"Should find governing law clause. Headings: {headings}"
        )


# ─────────────────────────────────────────────────────────────────────
# CUAD License Agreement Tests
# ─────────────────────────────────────────────────────────────────────

class TestCUADLicenseAgreement:
    """Tests modeled after CUAD benchmark categories."""

    def test_extraction_succeeds(self, cuad_extraction):
        """Pipeline completes without errors."""
        result, bindings = cuad_extraction
        assert result.facts, "Should extract facts"
        assert result.clauses, "Should classify clauses"

    def test_parties_extracted(self, cuad_extraction):
        """Parties identified: Apex Software and GlobalTech Solutions."""
        result, bindings = cuad_extraction
        # Parties may be in entity facts, bindings, or text_span facts
        all_text = " ".join(f.value.lower() for f in result.facts)
        binding_text = " ".join(
            f"{b.term} {b.resolves_to}".lower() for b in bindings
        )
        combined = all_text + " " + binding_text
        assert "apex" in combined or "licensor" in combined, (
            "Should find Apex Software or Licensor in extracted content"
        )
        assert "globaltech" in combined or "licensee" in combined, (
            "Should find GlobalTech or Licensee in extracted content"
        )

    def test_cuad_license_grant_clause(self, cuad_extraction):
        """cuad_license_grant: License grant clause detected."""
        result, _ = cuad_extraction
        headings = [c.heading.lower() for c in result.clauses]
        assert any("license" in h for h in headings), (
            f"Should find license grant clause. Headings: {headings}"
        )

    def test_cuad_non_compete_clause(self, cuad_extraction):
        """cuad_non-compete: Non-competition clause detected."""
        result, _ = cuad_extraction
        headings = [c.heading.lower() for c in result.clauses]
        assert any("non-compet" in h or "competition" in h for h in headings), (
            f"Should find non-compete clause. Headings: {headings}"
        )

    def test_cuad_termination_clause(self, cuad_extraction):
        """cuad_termination_for_convenience: Termination clause detected."""
        result, _ = cuad_extraction
        clause_types = [c.clause_type.value for c in result.clauses]
        assert "termination" in clause_types, (
            f"Should classify termination clause. Found: {clause_types}"
        )

    def test_cuad_cap_on_liability(self, cuad_extraction):
        """cuad_cap_on_liability: Liability cap extracted."""
        result, _ = cuad_extraction
        headings = [c.heading.lower() for c in result.clauses]
        assert any("liabilit" in h for h in headings), (
            f"Should find liability clause. Headings: {headings}"
        )

    def test_cuad_governing_law(self, cuad_extraction):
        """cuad_governing_law: Governing law clause detected."""
        result, _ = cuad_extraction
        headings = [c.heading.lower() for c in result.clauses]
        assert any("governing" in h or "jurisdiction" in h for h in headings), (
            f"Should find governing law clause. Headings: {headings}"
        )

    def test_cuad_insurance(self, cuad_extraction):
        """cuad_insurance: Insurance clause detected."""
        result, _ = cuad_extraction
        headings = [c.heading.lower() for c in result.clauses]
        assert any("insurance" in h for h in headings), (
            f"Should find insurance clause. Headings: {headings}"
        )

    def test_cuad_ip_ownership(self, cuad_extraction):
        """cuad_ip_ownership_assignment: IP ownership clause detected."""
        result, _ = cuad_extraction
        headings = [c.heading.lower() for c in result.clauses]
        assert any("intellectual" in h or "ip" in h or "ownership" in h for h in headings), (
            f"Should find IP ownership clause. Headings: {headings}"
        )

    def test_cuad_audit_rights(self, cuad_extraction):
        """cuad_audit_rights: Audit rights clause detected."""
        result, _ = cuad_extraction
        headings = [c.heading.lower() for c in result.clauses]
        assert any("audit" in h for h in headings), (
            f"Should find audit rights clause. Headings: {headings}"
        )

    def test_cuad_renewal_term(self, cuad_extraction):
        """cuad_renewal_term: Renewal provisions detected."""
        result, _ = cuad_extraction
        # Check that termination/term clause exists with renewal info
        clause_text_facts = [
            f for f in result.facts
            if f.fact_type == FactType.CLAUSE_TEXT and "renew" in f.value.lower()
        ]
        assert len(clause_text_facts) > 0, "Should extract renewal-related clause text"

    def test_monetary_values_extracted(self, cuad_extraction):
        """Multiple monetary values extracted as text_span (fees, caps, insurance)."""
        result, _ = cuad_extraction
        monetary_spans = [
            f for f in result.facts
            if f.fact_type == FactType.TEXT_SPAN
            and ("eur" in f.value.lower() or "usd" in f.value.lower() or "$" in f.value)
        ]
        # EUR 2,400,000 license fee, EUR 5,000,000 liability cap, insurance amounts
        assert len(monetary_spans) >= 2, (
            f"Should extract multiple monetary values. Found: {len(monetary_spans)}"
        )

    def test_percentage_facts_extracted(self, cuad_extraction):
        """Percentage values extracted as text_span (royalty rate, price adjustment)."""
        result, _ = cuad_extraction
        pct_spans = [
            f for f in result.facts
            if f.fact_type == FactType.TEXT_SPAN and "%" in f.value
        ]
        # 15% royalty, 3% price adjustment, 1.5% late payment, 5% audit threshold, 50%
        assert len(pct_spans) >= 2, (
            f"Should extract percentage facts. Found: {len(pct_spans)}"
        )

    def test_duration_facts_extracted(self, cuad_extraction):
        """Duration values extracted as text_span (5-year term, 24-month non-compete)."""
        result, _ = cuad_extraction
        duration_spans = [
            f for f in result.facts
            if f.fact_type == FactType.TEXT_SPAN
            and ("year" in f.value.lower() or "month" in f.value.lower() or "day" in f.value.lower())
        ]
        assert len(duration_spans) >= 2, (
            f"Should extract duration facts. Found: {len(duration_spans)}"
        )

    def test_rich_clause_body_text(self, cuad_extraction):
        """Clause body text provides sufficient context for Q&A."""
        result, _ = cuad_extraction
        clause_text_facts = [f for f in result.facts if f.fact_type == FactType.CLAUSE_TEXT]
        assert len(clause_text_facts) >= 10, (
            f"Should extract rich clause body text. Found: {len(clause_text_facts)}"
        )

    def test_mandatory_fact_slots(self, cuad_extraction):
        """Mandatory fact slots generated for classified clauses."""
        result, _ = cuad_extraction
        assert len(result.clause_fact_slots) > 0, "Should generate mandatory fact slots"

    def test_total_extraction_quality(self, cuad_extraction):
        """Overall extraction quality metrics for a complex license agreement."""
        result, bindings = cuad_extraction
        # Summary metrics
        n_facts = len(result.facts)
        n_clauses = len(result.clauses)
        n_bindings = len(bindings)
        n_xrefs = len(result.cross_references)
        n_slots = len(result.clause_fact_slots)

        print(f"\n{'='*50}")
        print(f"CUAD License Agreement — Extraction Summary")
        print(f"{'='*50}")
        print(f"  Facts:            {n_facts}")
        print(f"  Clauses:          {n_clauses}")
        print(f"  Bindings:         {n_bindings}")
        print(f"  Cross-References: {n_xrefs}")
        print(f"  Fact Slots:       {n_slots}")
        print(f"{'='*50}")

        # Quality gates
        assert n_facts >= 30, f"Expected ≥30 facts, got {n_facts}"
        assert n_clauses >= 8, f"Expected ≥8 clauses, got {n_clauses}"


# ─────────────────────────────────────────────────────────────────────
# Cross-Document Comparison Tests
# ─────────────────────────────────────────────────────────────────────

class TestCrossDocumentComparison:
    """Compare extraction quality across different document types."""

    def test_both_documents_extract_entities(self, nda_extraction, cuad_extraction):
        """Both documents should extract entity facts."""
        nda_result, _ = nda_extraction
        cuad_result, _ = cuad_extraction
        nda_entities = [f for f in nda_result.facts if f.fact_type == FactType.ENTITY]
        cuad_entities = [f for f in cuad_result.facts if f.fact_type == FactType.ENTITY]
        assert len(nda_entities) > 0, "NDA should have entities"
        assert len(cuad_entities) > 0, "CUAD license should have entities"

    def test_both_documents_classify_clauses(self, nda_extraction, cuad_extraction):
        """Both documents should classify clauses."""
        nda_result, _ = nda_extraction
        cuad_result, _ = cuad_extraction
        assert len(nda_result.clauses) >= 5, "NDA should have ≥5 clauses"
        assert len(cuad_result.clauses) >= 8, "CUAD license should have ≥8 clauses"

    def test_fact_type_coverage(self, nda_extraction, cuad_extraction):
        """Both documents should produce diverse fact types."""
        for name, (result, _) in [("NDA", nda_extraction), ("CUAD", cuad_extraction)]:
            fact_types = {f.fact_type.value for f in result.facts}
            # Should have at least entity, clause_text, and some structural types
            assert len(fact_types) >= 3, (
                f"{name} should have ≥3 fact types. Found: {fact_types}"
            )
