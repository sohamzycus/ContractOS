"""Unit tests for clause classifier (T045)."""

from __future__ import annotations

import pytest

from contractos.models.clause import ClauseTypeEnum
from contractos.tools.clause_classifier import (
    classify_heading,
    classify_paragraphs,
    extract_section_number,
)
from contractos.tools.parsers import ParsedParagraph


class TestClassifyHeading:
    @pytest.mark.parametrize(
        "heading,expected_type",
        [
            ("4. Termination", ClauseTypeEnum.TERMINATION),
            ("3. Payment Terms", ClauseTypeEnum.PAYMENT),
            ("5. Confidentiality", ClauseTypeEnum.CONFIDENTIALITY),
            ("6. Indemnification", ClauseTypeEnum.INDEMNIFICATION),
            ("Limitation of Liability", ClauseTypeEnum.LIABILITY),
            ("7. Warranties and Representations", ClauseTypeEnum.WARRANTY),
            ("Intellectual Property Rights", ClauseTypeEnum.IP_RIGHTS),
            ("Force Majeure", ClauseTypeEnum.FORCE_MAJEURE),
            ("Dispute Resolution", ClauseTypeEnum.DISPUTE_RESOLUTION),
            ("Governing Law", ClauseTypeEnum.GOVERNING_LAW),
            ("8. Notices", ClauseTypeEnum.NOTICE),
            ("Assignment", ClauseTypeEnum.ASSIGNMENT),
            ("Insurance Requirements", ClauseTypeEnum.INSURANCE),
            ("Compliance with Laws", ClauseTypeEnum.COMPLIANCE),
            ("Data Protection", ClauseTypeEnum.DATA_PROTECTION),
            ("Non-Compete", ClauseTypeEnum.NON_COMPETE),
            ("2. Scope of Services", ClauseTypeEnum.SCOPE),
        ],
    )
    def test_known_headings(self, heading: str, expected_type: ClauseTypeEnum) -> None:
        clause_type, confidence = classify_heading(heading)
        assert clause_type == expected_type

    def test_pattern_match_confidence_is_none(self) -> None:
        _, confidence = classify_heading("4. Termination")
        assert confidence is None

    def test_unknown_heading_returns_general(self) -> None:
        clause_type, _ = classify_heading("Miscellaneous Provisions")
        assert clause_type == ClauseTypeEnum.GENERAL

    def test_case_insensitive(self) -> None:
        clause_type, _ = classify_heading("TERMINATION OF AGREEMENT")
        assert clause_type == ClauseTypeEnum.TERMINATION


class TestExtractSectionNumber:
    def test_simple_number(self) -> None:
        assert extract_section_number("4. Termination") == "4"

    def test_dotted_number(self) -> None:
        assert extract_section_number("3.2.1 Payment Schedule") == "3.2.1"

    def test_no_number(self) -> None:
        assert extract_section_number("Termination") is None

    def test_heading_level_number(self) -> None:
        assert extract_section_number("12.1 Limitation of Liability") == "12.1"


class TestClassifyParagraphs:
    def test_classifies_heading_paragraphs(self) -> None:
        paragraphs = [
            ParsedParagraph(text="1. Definitions", char_start=0, char_end=14, structural_path="body > p[0]", heading_level=1),
            ParsedParagraph(text="Some body text", char_start=15, char_end=29, structural_path="body > p[1]"),
            ParsedParagraph(text="2. Termination", char_start=30, char_end=44, structural_path="body > p[2]", heading_level=1),
        ]
        clauses = classify_paragraphs(paragraphs, "doc-001")
        assert len(clauses) == 2
        assert clauses[1].clause_type == ClauseTypeEnum.TERMINATION

    def test_skips_body_paragraphs(self) -> None:
        paragraphs = [
            ParsedParagraph(text="Just body text", char_start=0, char_end=14, structural_path="body > p[0]"),
        ]
        clauses = classify_paragraphs(paragraphs, "doc-001")
        assert len(clauses) == 0

    def test_clause_has_document_id(self) -> None:
        paragraphs = [
            ParsedParagraph(text="4. Termination", char_start=0, char_end=14, structural_path="body > p[0]", heading_level=1),
        ]
        clauses = classify_paragraphs(paragraphs, "doc-001")
        assert clauses[0].document_id == "doc-001"

    def test_clause_has_section_number(self) -> None:
        paragraphs = [
            ParsedParagraph(text="4. Termination", char_start=0, char_end=14, structural_path="body > p[0]", heading_level=1),
        ]
        clauses = classify_paragraphs(paragraphs, "doc-001")
        assert clauses[0].section_number == "4"

    def test_clause_id_unique(self) -> None:
        paragraphs = [
            ParsedParagraph(text="1. Payment", char_start=0, char_end=10, structural_path="body > p[0]", heading_level=1),
            ParsedParagraph(text="2. Termination", char_start=11, char_end=25, structural_path="body > p[1]", heading_level=1),
        ]
        clauses = classify_paragraphs(paragraphs, "doc-001")
        assert clauses[0].clause_id != clauses[1].clause_id
