"""Unit tests for Phase 14 — Deep Extraction improvements (T336).

Tests smart quote normalization, broadened patterns, heading detection
fallbacks, and structural clause classification.
"""

from __future__ import annotations

import pytest

from contractos.tools.contract_patterns import (
    ALIAS_PATTERN,
    DEFINITION_PATTERN,
    PARENTHETICAL_DEF_PATTERN,
    PARTY_ALIAS_PATTERN,
    extract_patterns,
    normalize_quotes,
)
from contractos.tools.clause_classifier import (
    classify_paragraphs,
    classify_paragraphs_with_fallback,
    _has_meaningful_clauses,
    _promote_structural_headings,
)
from contractos.tools.parsers import ParsedParagraph
from contractos.models.clause import ClauseTypeEnum


# ── T330: Smart Quote Normalization ─────────────────────────────────


class TestNormalizeQuotes:
    def test_left_double_curly(self) -> None:
        assert normalize_quotes("\u201c") == '"'

    def test_right_double_curly(self) -> None:
        assert normalize_quotes("\u201d") == '"'

    def test_left_single_curly(self) -> None:
        assert normalize_quotes("\u2018") == "'"

    def test_right_single_curly(self) -> None:
        assert normalize_quotes("\u2019") == "'"

    def test_en_dash(self) -> None:
        assert normalize_quotes("\u2013") == "-"

    def test_em_dash(self) -> None:
        assert normalize_quotes("\u2014") == "-"

    def test_guillemets(self) -> None:
        assert normalize_quotes("\u00ab\u00bb") == '""'

    def test_mixed_text(self) -> None:
        text = '\u201cAgreement\u201d shall mean this contract'
        result = normalize_quotes(text)
        assert result == '"Agreement" shall mean this contract'

    def test_no_change_for_straight_quotes(self) -> None:
        text = '"Agreement" shall mean this contract'
        assert normalize_quotes(text) == text

    def test_preserves_non_quote_characters(self) -> None:
        text = "Hello world 123 !@#"
        assert normalize_quotes(text) == text


class TestDefinitionPatternWithSmartQuotes:
    def test_smart_quotes_definition(self) -> None:
        text = normalize_quotes('\u201cEffective Date\u201d shall mean January 1, 2025.')
        matches = DEFINITION_PATTERN.findall(text)
        assert len(matches) >= 1
        assert matches[0][0] == "Effective Date"

    def test_designates_verb(self) -> None:
        text = '"Service Area" designates the geographic region.'
        matches = DEFINITION_PATTERN.findall(text)
        assert len(matches) >= 1
        assert matches[0][0] == "Service Area"

    def test_constitutes_verb(self) -> None:
        text = '"Material Breach" constitutes a failure to perform.'
        matches = DEFINITION_PATTERN.findall(text)
        assert len(matches) >= 1

    def test_includes_verb(self) -> None:
        text = '"Deliverables" includes all work product.'
        matches = DEFINITION_PATTERN.findall(text)
        assert len(matches) >= 1


# ── T333: Parenthetical Definitions ─────────────────────────────────


class TestParentheticalDefinitions:
    def test_the_agreement(self) -> None:
        text = 'This Master Services Agreement (the "Agreement") is entered into.'
        matches = PARENTHETICAL_DEF_PATTERN.findall(text)
        assert any("Agreement" in m[0] for m in matches)

    def test_bare_parenthetical(self) -> None:
        text = 'Acme Corp ("Service Provider") agrees to provide services.'
        matches = PARENTHETICAL_DEF_PATTERN.findall(text)
        assert any("Service Provider" in m[0] for m in matches)

    def test_or_alternative(self) -> None:
        text = 'This Non-Disclosure Agreement (the "NDA" or "Agreement") governs.'
        matches = PARENTHETICAL_DEF_PATTERN.findall(text)
        terms = [m[0] for m in matches]
        assert any("NDA" in t for t in terms)

    def test_extracted_via_extract_patterns(self) -> None:
        text = 'This Master Agreement (the "Agreement") is dated January 1, 2025.'
        matches = extract_patterns(text)
        defs = [m for m in matches if m.pattern_name == "definition"]
        assert any("Agreement" in d.value for d in defs)


# ── T334: Broader Alias/Entity Patterns ─────────────────────────────


class TestPartyAliasPattern:
    def test_corporation_alias(self) -> None:
        text = 'Acme Corporation, a Delaware corporation ("Vendor")'
        matches = PARTY_ALIAS_PATTERN.findall(text)
        assert len(matches) >= 1

    def test_llc_alias(self) -> None:
        text = 'Beta Services LLC, a California limited liability company ("Provider")'
        matches = PARTY_ALIAS_PATTERN.findall(text)
        assert len(matches) >= 1

    def test_pvt_ltd_alias(self) -> None:
        text = 'Zycus Pvt Ltd, a Michigan corporation ("Service Provider")'
        matches = PARTY_ALIAS_PATTERN.findall(text)
        assert len(matches) >= 1

    def test_inc_alias(self) -> None:
        text = 'Global Tech Inc., a New York corporation ("Client")'
        matches = PARTY_ALIAS_PATTERN.findall(text)
        assert len(matches) >= 1

    def test_smart_quotes_alias(self) -> None:
        text = normalize_quotes('Acme Corp, a Delaware corporation (\u201cVendor\u201d)')
        matches = PARTY_ALIAS_PATTERN.findall(text)
        assert len(matches) >= 1


class TestAliasDetectorBroadened:
    def test_detect_aliases_with_smart_quotes(self) -> None:
        from contractos.tools.alias_detector import detect_aliases
        text = normalize_quotes('Alpha Corp, hereinafter referred to as \u201cBuyer\u201d')
        facts, bindings = detect_aliases(text, "doc-001")
        assert len(bindings) >= 1
        assert any(b.term == "Buyer" for b in bindings)


# ── T335: Clause Classifier Fallback ────────────────────────────────


class TestClassifyParagraphsWithFallback:
    def test_standard_headings_work(self) -> None:
        paragraphs = [
            ParsedParagraph(text="1. Definitions", char_start=0, char_end=14, structural_path="p[0]", heading_level=1),
            ParsedParagraph(text="Body text here.", char_start=15, char_end=30, structural_path="p[1]"),
            ParsedParagraph(text="2. Termination", char_start=31, char_end=45, structural_path="p[2]", heading_level=1),
        ]
        clauses = classify_paragraphs_with_fallback(paragraphs, "doc-001")
        assert len(clauses) == 2
        assert clauses[1].clause_type == ClauseTypeEnum.TERMINATION

    def test_numbered_heading_fallback(self) -> None:
        paragraphs = [
            ParsedParagraph(text="1. DEFINITIONS", char_start=0, char_end=14, structural_path="p[0]"),
            ParsedParagraph(text="Some body text.", char_start=15, char_end=30, structural_path="p[1]"),
            ParsedParagraph(text="2. TERMINATION", char_start=31, char_end=45, structural_path="p[2]"),
            ParsedParagraph(text="More body text.", char_start=46, char_end=61, structural_path="p[3]"),
        ]
        clauses = classify_paragraphs_with_fallback(paragraphs, "doc-001")
        assert len(clauses) >= 2
        types = {c.clause_type for c in clauses}
        assert ClauseTypeEnum.TERMINATION in types

    def test_allcaps_heading_fallback(self) -> None:
        paragraphs = [
            ParsedParagraph(text="CONFIDENTIALITY", char_start=0, char_end=15, structural_path="p[0]"),
            ParsedParagraph(text="All information is confidential.", char_start=16, char_end=47, structural_path="p[1]"),
            ParsedParagraph(text="INDEMNIFICATION", char_start=48, char_end=63, structural_path="p[2]"),
        ]
        clauses = classify_paragraphs_with_fallback(paragraphs, "doc-001")
        assert len(clauses) >= 2
        types = {c.clause_type for c in clauses}
        assert ClauseTypeEnum.CONFIDENTIALITY in types
        assert ClauseTypeEnum.INDEMNIFICATION in types

    def test_no_false_positives_on_body_text(self) -> None:
        paragraphs = [
            ParsedParagraph(text="This is a long paragraph of body text that should not be treated as a heading.", char_start=0, char_end=78, structural_path="p[0]"),
        ]
        clauses = classify_paragraphs_with_fallback(paragraphs, "doc-001")
        assert len(clauses) == 0


class TestHasMeaningfulClauses:
    def test_all_general_is_not_meaningful(self) -> None:
        from contractos.models.clause import Clause
        clauses = [
            Clause(clause_id="c1", document_id="d1", clause_type=ClauseTypeEnum.GENERAL, heading="BETWEEN", section_number=None, fact_id="", contained_fact_ids=[], cross_reference_ids=[], classification_method="pattern_match"),
            Clause(clause_id="c2", document_id="d1", clause_type=ClauseTypeEnum.GENERAL, heading="AND", section_number=None, fact_id="", contained_fact_ids=[], cross_reference_ids=[], classification_method="pattern_match"),
        ]
        assert not _has_meaningful_clauses(clauses)

    def test_one_specific_is_meaningful(self) -> None:
        from contractos.models.clause import Clause
        clauses = [
            Clause(clause_id="c1", document_id="d1", clause_type=ClauseTypeEnum.GENERAL, heading="BETWEEN", section_number=None, fact_id="", contained_fact_ids=[], cross_reference_ids=[], classification_method="pattern_match"),
            Clause(clause_id="c2", document_id="d1", clause_type=ClauseTypeEnum.TERMINATION, heading="Termination", section_number=None, fact_id="", contained_fact_ids=[], cross_reference_ids=[], classification_method="pattern_match"),
        ]
        assert _has_meaningful_clauses(clauses)


class TestPromoteStructuralHeadings:
    def test_numbered_heading_promoted(self) -> None:
        paragraphs = [
            ParsedParagraph(text="1. DEFINITIONS", char_start=0, char_end=14, structural_path="p[0]"),
        ]
        promoted = _promote_structural_headings(paragraphs)
        assert promoted[0].heading_level == 1

    def test_allcaps_heading_promoted(self) -> None:
        paragraphs = [
            ParsedParagraph(text="CONFIDENTIALITY", char_start=0, char_end=15, structural_path="p[0]"),
        ]
        promoted = _promote_structural_headings(paragraphs)
        assert promoted[0].heading_level == 1

    def test_body_text_not_promoted(self) -> None:
        paragraphs = [
            ParsedParagraph(text="This is regular body text.", char_start=0, char_end=26, structural_path="p[0]"),
        ]
        promoted = _promote_structural_headings(paragraphs)
        assert promoted[0].heading_level is None

    def test_long_allcaps_not_promoted(self) -> None:
        paragraphs = [
            ParsedParagraph(text="THIS IS A VERY LONG ALL CAPS LINE THAT SHOULD NOT BE A HEADING BECAUSE IT IS TOO LONG", char_start=0, char_end=85, structural_path="p[0]"),
        ]
        promoted = _promote_structural_headings(paragraphs)
        assert promoted[0].heading_level is None


# ── T331/T332: Parser Heading Detection ─────────────────────────────


class TestPdfHeadingDetection:
    def test_pdf_parser_detects_headings(self) -> None:
        """PDF parser should detect headings via font-size heuristics."""
        from contractos.tools.pdf_parser import _detect_heading_level
        # Large font = heading
        level = _detect_heading_level("DEFINITIONS", [16.0], True, 11.0, [16.0, 14.0, 12.5])
        assert level is not None
        assert level <= 2

    def test_bold_short_text_is_heading(self) -> None:
        from contractos.tools.pdf_parser import _detect_heading_level
        level = _detect_heading_level("Payment Terms", [11.0], True, 11.0, [16.0, 14.0])
        assert level == 2

    def test_allcaps_short_text_is_heading(self) -> None:
        from contractos.tools.pdf_parser import _detect_heading_level
        level = _detect_heading_level("TERMINATION", [11.0], False, 11.0, [16.0, 14.0])
        assert level == 2

    def test_body_text_not_heading(self) -> None:
        from contractos.tools.pdf_parser import _detect_heading_level
        level = _detect_heading_level(
            "This is a normal paragraph of body text that should not be detected as a heading.",
            [11.0], False, 11.0, [16.0, 14.0],
        )
        assert level is None


class TestDocxBoldFallback:
    def test_looks_like_heading(self) -> None:
        from contractos.tools.docx_parser import _looks_like_heading
        assert _looks_like_heading("Confidentiality") is True
        assert _looks_like_heading("Term and Termination") is True

    def test_long_text_not_heading(self) -> None:
        from contractos.tools.docx_parser import _looks_like_heading
        assert _looks_like_heading("This is a very long paragraph that should not be treated as a heading because it exceeds the length limit.") is False

    def test_allcaps_heading(self) -> None:
        from contractos.tools.docx_parser import _is_allcaps_heading
        assert _is_allcaps_heading("WARRANTIES") is True
        assert _is_allcaps_heading("NON-SOLICITATION") is True

    def test_mixed_case_not_allcaps(self) -> None:
        from contractos.tools.docx_parser import _is_allcaps_heading
        assert _is_allcaps_heading("Payment Terms") is False

    def test_numbered_heading(self) -> None:
        from contractos.tools.docx_parser import _is_numbered_heading
        assert _is_numbered_heading("1. DEFINITIONS") is True
        assert _is_numbered_heading("12.1 Payment Schedule") is True

    def test_body_text_not_numbered_heading(self) -> None:
        from contractos.tools.docx_parser import _is_numbered_heading
        assert _is_numbered_heading("This is body text.") is False


# ── Binding Resolver with Parenthetical Definitions ─────────────────


class TestBindingResolverBroadened:
    def test_parenthetical_definition_binding(self) -> None:
        from contractos.tools.binding_resolver import resolve_bindings
        text = 'This Master Services Agreement (the "Agreement") is entered into by the parties.'
        bindings = resolve_bindings([], [], text, "doc-001")
        assert any(b.term == "Agreement" for b in bindings)

    def test_smart_quote_definition_binding(self) -> None:
        from contractos.tools.binding_resolver import resolve_bindings
        text = normalize_quotes('\u201cEffective Date\u201d shall mean January 1, 2025.')
        bindings = resolve_bindings([], [], text, "doc-001")
        assert any(b.term == "Effective Date" for b in bindings)

    def test_deduplication(self) -> None:
        from contractos.tools.binding_resolver import resolve_bindings
        from contractos.models.binding import Binding, BindingScope, BindingType
        existing = [
            Binding(binding_id="b1", binding_type=BindingType.DEFINITION, term="Agreement",
                    resolves_to="this contract", source_fact_id="f1", document_id="doc-001",
                    scope=BindingScope.CONTRACT),
        ]
        text = 'This Master Services Agreement (the "Agreement") is entered into.'
        bindings = resolve_bindings([], existing, text, "doc-001")
        agreement_bindings = [b for b in bindings if b.term.lower() == "agreement"]
        assert len(agreement_bindings) == 1
