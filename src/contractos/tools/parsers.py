"""Document parser models — shared data structures for parsed content."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ParsedParagraph(BaseModel):
    """A single paragraph extracted from a document."""

    text: str
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    structural_path: str
    heading_level: int | None = None  # None = body text, 0-9 = heading level
    page_number: int | None = None


class ParsedTableCell(BaseModel):
    """A single cell extracted from a table."""

    text: str
    row: int = Field(ge=0)
    col: int = Field(ge=0)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    structural_path: str
    page_number: int | None = None


class ParsedTable(BaseModel):
    """A table extracted from a document."""

    cells: list[ParsedTableCell]
    row_count: int = Field(ge=0)
    col_count: int = Field(ge=0)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    structural_path: str
    page_number: int | None = None


class ParsedDocument(BaseModel):
    """Complete parsed representation of a document."""

    paragraphs: list[ParsedParagraph] = Field(default_factory=list)
    tables: list[ParsedTable] = Field(default_factory=list)
    full_text: str = ""
    page_count: int = Field(ge=0, default=0)
    word_count: int = Field(ge=0, default=0)
