"""Unit tests for the Word document parser (T041)."""

from __future__ import annotations

from pathlib import Path

import pytest

from contractos.tools.docx_parser import parse_docx
from contractos.tools.parsers import ParsedDocument

FIXTURES = Path(__file__).parent.parent / "fixtures"
DOCX_PATH = FIXTURES / "simple_procurement.docx"


@pytest.fixture
def parsed() -> ParsedDocument:
    assert DOCX_PATH.exists(), f"Fixture not found: {DOCX_PATH}"
    return parse_docx(DOCX_PATH)


class TestDocxParserBasics:
    def test_returns_parsed_document(self, parsed: ParsedDocument) -> None:
        assert isinstance(parsed, ParsedDocument)

    def test_has_paragraphs(self, parsed: ParsedDocument) -> None:
        assert len(parsed.paragraphs) > 0

    def test_has_tables(self, parsed: ParsedDocument) -> None:
        # Our fixture has 2 tables (Schedule A, Schedule B)
        assert len(parsed.tables) >= 2

    def test_full_text_not_empty(self, parsed: ParsedDocument) -> None:
        assert len(parsed.full_text) > 100

    def test_word_count_positive(self, parsed: ParsedDocument) -> None:
        assert parsed.word_count > 50


class TestDocxHeadings:
    def test_heading_paragraphs_detected(self, parsed: ParsedDocument) -> None:
        headings = [p for p in parsed.paragraphs if p.heading_level is not None]
        # Our fixture has: title + 5 section headings + 2 schedule headings
        assert len(headings) >= 5

    def test_heading_levels_correct(self, parsed: ParsedDocument) -> None:
        headings = {p.text: p.heading_level for p in parsed.paragraphs if p.heading_level is not None}
        # "1. Definitions" should be level 1
        defs = [v for k, v in headings.items() if "Definitions" in k]
        assert len(defs) >= 1
        assert defs[0] == 1


class TestDocxCharacterOffsets:
    def test_char_offsets_are_positive(self, parsed: ParsedDocument) -> None:
        for p in parsed.paragraphs:
            assert p.char_start >= 0
            assert p.char_end > p.char_start, f"Bad offsets for: {p.text[:50]}"

    def test_char_offsets_match_full_text(self, parsed: ParsedDocument) -> None:
        """The text_span at [char_start:char_end] should match paragraph text."""
        for p in parsed.paragraphs:
            if p.text.strip():
                extracted = parsed.full_text[p.char_start : p.char_end]
                assert extracted == p.text, (
                    f"Offset mismatch: expected '{p.text[:40]}...', "
                    f"got '{extracted[:40]}...'"
                )

    def test_offsets_are_monotonically_increasing(self, parsed: ParsedDocument) -> None:
        starts = [p.char_start for p in parsed.paragraphs if p.text.strip()]
        for i in range(1, len(starts)):
            assert starts[i] > starts[i - 1]


class TestDocxStructuralPaths:
    def test_structural_paths_present(self, parsed: ParsedDocument) -> None:
        for p in parsed.paragraphs:
            assert p.structural_path, f"Missing structural_path for: {p.text[:40]}"

    def test_structural_paths_contain_body(self, parsed: ParsedDocument) -> None:
        for p in parsed.paragraphs:
            assert "body" in p.structural_path


class TestDocxTableExtraction:
    def test_table_has_cells(self, parsed: ParsedDocument) -> None:
        for table in parsed.tables:
            assert len(table.cells) > 0

    def test_table_row_col_metadata(self, parsed: ParsedDocument) -> None:
        # Schedule A has 4 rows x 3 cols
        schedule_a = parsed.tables[0]
        assert schedule_a.row_count >= 4
        assert schedule_a.col_count >= 2

    def test_table_cell_offsets_valid(self, parsed: ParsedDocument) -> None:
        for table in parsed.tables:
            for cell in table.cells:
                assert cell.char_start >= 0
                assert cell.char_end > cell.char_start or cell.text == ""

    def test_table_contains_expected_data(self, parsed: ParsedDocument) -> None:
        """Schedule A should contain 'Dell Inspiron 15'."""
        all_cell_text = " ".join(
            cell.text for table in parsed.tables for cell in table.cells
        )
        assert "Dell Inspiron" in all_cell_text
        assert "Bangalore" in all_cell_text
