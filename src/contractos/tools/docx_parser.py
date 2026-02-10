"""Word document (.docx) parser — extracts paragraphs, tables, headings with character offsets."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from contractos.tools.parsers import (
    ParsedDocument,
    ParsedParagraph,
    ParsedTable,
    ParsedTableCell,
)


def parse_docx(file_path: str | Path) -> ParsedDocument:
    """Parse a .docx file into a structured ParsedDocument.

    Extracts paragraphs with heading levels, tables with cell metadata,
    and computes character offsets into a concatenated full_text.
    """
    doc = Document(str(file_path))

    paragraphs: list[ParsedParagraph] = []
    tables: list[ParsedTable] = []
    full_text_parts: list[str] = []
    offset = 0
    para_idx = 0
    table_idx = 0

    # Walk the document body in order — paragraphs and tables interleaved
    for element in doc.element.body:
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

        if tag == "p":
            text = element.text or ""
            # Collect all runs
            runs = element.findall(qn("w:r"))
            text = ""
            for run in runs:
                t_elem = run.find(qn("w:t"))
                if t_elem is not None and t_elem.text:
                    text += t_elem.text
            if not text:
                # Try direct text content
                text = "".join(
                    t.text for t in element.iter(qn("w:t")) if t.text
                )

            heading_level = _get_heading_level(element)
            structural_path = f"body > p[{para_idx}]"
            if heading_level is not None:
                structural_path = f"body > heading[{heading_level}][{para_idx}]"

            char_start = offset
            char_end = offset + len(text)

            paragraphs.append(ParsedParagraph(
                text=text,
                char_start=char_start,
                char_end=char_end,
                structural_path=structural_path,
                heading_level=heading_level,
            ))

            if text:
                full_text_parts.append(text)
                offset = char_end + 1  # +1 for newline separator
            else:
                offset = char_end

            para_idx += 1

        elif tag == "tbl":
            table_cells: list[ParsedTableCell] = []
            rows = element.findall(qn("w:tr"))
            row_count = len(rows)
            col_count = 0
            table_char_start = offset

            for row_idx, row in enumerate(rows):
                cells = row.findall(qn("w:tc"))
                col_count = max(col_count, len(cells))
                for col_idx, cell in enumerate(cells):
                    cell_text = "".join(
                        t.text for t in cell.iter(qn("w:t")) if t.text
                    )
                    cell_char_start = offset
                    cell_char_end = offset + len(cell_text)

                    table_cells.append(ParsedTableCell(
                        text=cell_text,
                        row=row_idx,
                        col=col_idx,
                        char_start=cell_char_start,
                        char_end=cell_char_end,
                        structural_path=f"body > table[{table_idx}] > row[{row_idx}] > cell[{col_idx}]",
                    ))

                    if cell_text:
                        full_text_parts.append(cell_text)
                        offset = cell_char_end + 1
                    else:
                        offset = cell_char_end

            table_char_end = offset
            tables.append(ParsedTable(
                cells=table_cells,
                row_count=row_count,
                col_count=col_count,
                char_start=table_char_start,
                char_end=table_char_end,
                structural_path=f"body > table[{table_idx}]",
            ))
            table_idx += 1

    full_text = "\n".join(full_text_parts)
    word_count = len(full_text.split())

    return ParsedDocument(
        paragraphs=paragraphs,
        tables=tables,
        full_text=full_text,
        page_count=0,  # .docx doesn't have reliable page count without rendering
        word_count=word_count,
    )


def _get_heading_level(element) -> int | None:
    """Extract heading level from a paragraph element, or None if not a heading."""
    pPr = element.find(qn("w:pPr"))
    if pPr is None:
        return None
    pStyle = pPr.find(qn("w:pStyle"))
    if pStyle is None:
        return None
    style_val = pStyle.get(qn("w:val"), "")
    if style_val == "Title":
        return 0
    if style_val.startswith("Heading"):
        try:
            return int(style_val.replace("Heading", "").strip())
        except ValueError:
            return None
    return None
