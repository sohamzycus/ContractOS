"""Contract document metadata model."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class Contract(BaseModel):
    """Metadata for an indexed contract document."""

    document_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    file_path: str = Field(min_length=1)
    file_format: Literal["docx", "pdf"]
    file_hash: str = Field(min_length=1)
    parties: list[str] = Field(default_factory=list)
    effective_date: date | None = None
    page_count: int = Field(ge=0)
    word_count: int = Field(ge=0)
    indexed_at: datetime
    last_parsed_at: datetime
    extraction_version: str = Field(min_length=1)
