"""PDF document parser — extracts text, tables, and metadata with character offsets.

Uses font-size and bold heuristics to detect headings in PDFs, since PDFs
have no native heading styles like DOCX.
"""

from __future__ import annotations

import statistics
from pathlib import Path

from contractos.tools.parsers import (
    ParsedDocument,
    ParsedParagraph,
    ParsedTable,
    ParsedTableCell,
)


def parse_pdf(file_path: str | Path) -> ParsedDocument:
    """Parse a .pdf file into a structured ParsedDocument.

    Uses PyMuPDF (fitz) for text extraction with character offsets,
    font-size heuristics for heading detection, and pdfplumber for
    table extraction.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(str(file_path))
    paragraphs: list[ParsedParagraph] = []
    tables: list[ParsedTable] = []
    full_text_parts: list[str] = []
    offset = 0

    # First pass: collect font metrics for heading detection
    font_sizes: list[float] = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if text and len(text) > 1:
                        font_sizes.append(span.get("size", 12.0))

    # Compute font-size thresholds for heading detection
    median_size = statistics.median(font_sizes) if font_sizes else 12.0
    heading_thresholds = _compute_heading_thresholds(font_sizes, median_size)

    # Second pass: extract paragraphs with heading detection
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_number = page_num + 1

        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for block in blocks:
            if block.get("type") != 0:
                continue

            block_text_parts: list[str] = []
            block_font_sizes: list[float] = []
            block_is_bold = False

            for line in block.get("lines", []):
                line_texts: list[str] = []
                for span in line.get("spans", []):
                    span_text = span.get("text", "")
                    if span_text:
                        line_texts.append(span_text)
                        block_font_sizes.append(span.get("size", 12.0))
                        flags = span.get("flags", 0)
                        if flags & 2 ** 4:  # bold flag in PyMuPDF
                            block_is_bold = True
                line_text = "".join(line_texts).strip()
                if line_text:
                    block_text_parts.append(line_text)

            text = " ".join(block_text_parts).strip()
            if not text:
                continue

            char_start = offset
            char_end = offset + len(text)

            heading_level = _detect_heading_level(
                text,
                block_font_sizes,
                block_is_bold,
                median_size,
                heading_thresholds,
            )

            paragraphs.append(ParsedParagraph(
                text=text,
                char_start=char_start,
                char_end=char_end,
                structural_path=f"page[{page_number}] > block[{block.get('number', 0)}]",
                page_number=page_number,
                heading_level=heading_level,
            ))

            full_text_parts.append(text)
            offset = char_end + 1
    doc.close()

    # Extract tables using pdfplumber
    tables = _extract_tables_pdfplumber(file_path, offset)

    for table in tables:
        for cell in table.cells:
            if cell.text.strip():
                full_text_parts.append(cell.text)

    full_text = "\n".join(full_text_parts)
    word_count = len(full_text.split())

    return ParsedDocument(
        paragraphs=paragraphs,
        tables=tables,
        full_text=full_text,
        page_count=_get_page_count(file_path),
        word_count=word_count,
    )


def _compute_heading_thresholds(
    font_sizes: list[float], median_size: float
) -> list[float]:
    """Compute font-size tiers for heading level assignment.

    Returns a sorted-descending list of unique sizes that are larger
    than the median body text size by at least 1pt.
    """
    if not font_sizes:
        return []
    unique_large = sorted(
        {s for s in font_sizes if s > median_size + 0.5},
        reverse=True,
    )
    return unique_large[:4]


def _detect_heading_level(
    text: str,
    block_font_sizes: list[float],
    is_bold: bool,
    median_size: float,
    heading_thresholds: list[float],
) -> int | None:
    """Detect heading level from font metrics and text characteristics.

    Heuristics (in priority order):
    1. Font size significantly larger than median → heading level by tier
    2. Bold + short text (< 80 chars) → heading level 2
    3. ALL-CAPS short text (4-60 chars, no lowercase) → heading level 2
    """
    if not text.strip():
        return None

    avg_size = statistics.mean(block_font_sizes) if block_font_sizes else median_size

    # Heuristic 1: Font size tiers
    if heading_thresholds and avg_size > median_size + 0.5:
        for level, threshold in enumerate(heading_thresholds, start=1):
            if avg_size >= threshold - 0.3:
                return level

    clean = text.strip()
    word_count = len(clean.split())

    # Heuristic 2: Bold + short text
    if is_bold and len(clean) < 80 and word_count <= 10:
        return 2

    # Heuristic 3: ALL-CAPS short text (likely a section heading)
    if (
        4 <= len(clean) <= 60
        and clean == clean.upper()
        and any(c.isalpha() for c in clean)
        and word_count <= 8
    ):
        return 2

    return None


def _extract_tables_pdfplumber(
    file_path: str | Path, start_offset: int
) -> list[ParsedTable]:
    """Extract tables from PDF using pdfplumber."""
    import pdfplumber

    tables: list[ParsedTable] = []
    offset = start_offset
    table_idx = 0

    with pdfplumber.open(str(file_path)) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_number = page_num + 1
            page_tables = page.extract_tables() or []

            for raw_table in page_tables:
                if not raw_table:
                    continue

                cells: list[ParsedTableCell] = []
                table_char_start = offset
                row_count = len(raw_table)
                col_count = max(len(row) for row in raw_table) if raw_table else 0

                for row_idx, row in enumerate(raw_table):
                    for col_idx, cell_text in enumerate(row):
                        cell_text = (cell_text or "").strip()
                        cell_char_start = offset
                        cell_char_end = offset + len(cell_text)

                        cells.append(ParsedTableCell(
                            text=cell_text,
                            row=row_idx,
                            col=col_idx,
                            char_start=cell_char_start,
                            char_end=cell_char_end,
                            structural_path=f"page[{page_number}] > table[{table_idx}] > row[{row_idx}] > cell[{col_idx}]",
                            page_number=page_number,
                        ))

                        if cell_text:
                            offset = cell_char_end + 1
                        else:
                            offset = cell_char_end

                tables.append(ParsedTable(
                    cells=cells,
                    row_count=row_count,
                    col_count=col_count,
                    char_start=table_char_start,
                    char_end=offset,
                    structural_path=f"page[{page_number}] > table[{table_idx}]",
                    page_number=page_number,
                ))
                table_idx += 1

    return tables


def _get_page_count(file_path: str | Path) -> int:
    """Get the page count of a PDF."""
    import fitz
    doc = fitz.open(str(file_path))
    count = len(doc)
    doc.close()
    return count
