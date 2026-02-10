"""Unit tests for the PDF document parser (T042)."""

from __future__ import annotations

from pathlib import Path

import pytest

from contractos.tools.pdf_parser import parse_pdf
from contractos.tools.parsers import ParsedDocument

FIXTURES = Path(__file__).parent.parent / "fixtures"
PDF_PATH = FIXTURES / "simple_nda.pdf"


@pytest.fixture
def parsed() -> ParsedDocument:
    assert PDF_PATH.exists(), f"Fixture not found: {PDF_PATH}"
    return parse_pdf(PDF_PATH)


class TestPdfParserBasics:
    def test_returns_parsed_document(self, parsed: ParsedDocument) -> None:
        assert isinstance(parsed, ParsedDocument)

    def test_has_paragraphs(self, parsed: ParsedDocument) -> None:
        assert len(parsed.paragraphs) > 0

    def test_full_text_not_empty(self, parsed: ParsedDocument) -> None:
        assert len(parsed.full_text) > 50

    def test_word_count_positive(self, parsed: ParsedDocument) -> None:
        assert parsed.word_count > 20

    def test_page_count(self, parsed: ParsedDocument) -> None:
        assert parsed.page_count >= 1


class TestPdfCharacterOffsets:
    def test_char_offsets_are_positive(self, parsed: ParsedDocument) -> None:
        for p in parsed.paragraphs:
            if p.text.strip():
                assert p.char_start >= 0
                assert p.char_end > p.char_start

    def test_char_offsets_match_full_text(self, parsed: ParsedDocument) -> None:
        for p in parsed.paragraphs:
            if p.text.strip():
                extracted = parsed.full_text[p.char_start : p.char_end]
                assert extracted == p.text


class TestPdfPageNumbers:
    def test_page_numbers_assigned(self, parsed: ParsedDocument) -> None:
        pages = {p.page_number for p in parsed.paragraphs if p.page_number is not None}
        assert len(pages) >= 1
        assert 1 in pages  # at least page 1


class TestPdfStructuralPaths:
    def test_structural_paths_present(self, parsed: ParsedDocument) -> None:
        for p in parsed.paragraphs:
            if p.text.strip():
                assert p.structural_path


class TestPdfTableExtraction:
    def test_has_tables(self, parsed: ParsedDocument) -> None:
        # Our NDA fixture has 1 table (Key Dates)
        assert len(parsed.tables) >= 1

    def test_table_contains_expected_data(self, parsed: ParsedDocument) -> None:
        all_cell_text = " ".join(
            cell.text for table in parsed.tables for cell in table.cells
        )
        assert "January" in all_cell_text or "2025" in all_cell_text


class TestPdfContentExtraction:
    def test_contains_party_names(self, parsed: ParsedDocument) -> None:
        assert "Gamma" in parsed.full_text or "Delta" in parsed.full_text

    def test_contains_nda_content(self, parsed: ParsedDocument) -> None:
        assert "Confidential" in parsed.full_text
