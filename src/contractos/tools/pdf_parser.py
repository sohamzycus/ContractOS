"""PDF document parser — extracts text, tables, and metadata with character offsets."""

from __future__ import annotations

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
    and pdfplumber for table extraction.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(str(file_path))
    paragraphs: list[ParsedParagraph] = []
    tables: list[ParsedTable] = []
    full_text_parts: list[str] = []
    offset = 0
    para_idx = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_number = page_num + 1  # 1-indexed

        # Extract text blocks (each block is roughly a paragraph)
        blocks = page.get_text("blocks")
        for block in blocks:
            # block: (x0, y0, x1, y1, text, block_no, block_type)
            if block[6] != 0:  # skip image blocks
                continue
            text = block[4].strip()
            if not text:
                continue

            char_start = offset
            char_end = offset + len(text)

            paragraphs.append(ParsedParagraph(
                text=text,
                char_start=char_start,
                char_end=char_end,
                structural_path=f"page[{page_number}] > block[{block[5]}]",
                page_number=page_number,
            ))

            full_text_parts.append(text)
            offset = char_end + 1  # +1 for newline separator
            para_idx += 1

    doc.close()

    # Extract tables using pdfplumber
    tables = _extract_tables_pdfplumber(file_path, offset)

    # Add table cell text to full_text
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
