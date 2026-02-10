"""Fact model — immutable, source-addressable claims extracted from document text."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class FactType(StrEnum):
    """Types of facts that can be extracted from a document."""

    TEXT_SPAN = "text_span"
    ENTITY = "entity"
    CLAUSE = "clause"
    TABLE_CELL = "table_cell"
    HEADING = "heading"
    METADATA = "metadata"
    STRUCTURAL = "structural"
    CROSS_REFERENCE = "cross_reference"
    CLAUSE_TEXT = "clause_text"


class EntityType(StrEnum):
    """Types of named entities recognized in contracts."""

    PARTY = "party"
    DATE = "date"
    MONEY = "money"
    PRODUCT = "product"
    LOCATION = "location"
    DURATION = "duration"
    SECTION_REF = "section_ref"


class FactEvidence(BaseModel):
    """Precise location of a fact in a document."""

    document_id: str
    text_span: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    location_hint: str = Field(min_length=1)
    structural_path: str = Field(min_length=1)
    page_number: int | None = None

    def model_post_init(self, __context: object) -> None:
        if self.char_end <= self.char_start:
            msg = f"char_end ({self.char_end}) must be greater than char_start ({self.char_start})"
            raise ValueError(msg)


class Fact(BaseModel):
    """An immutable, source-addressable claim extracted from document text.

    Facts are the ground truth layer of ContractOS. They do not require
    interpretation — they are what the document says, not what it means.
    """

    fact_id: str = Field(min_length=1)
    fact_type: FactType
    entity_type: EntityType | None = None
    value: str = Field(min_length=1)
    evidence: FactEvidence
    extraction_method: str = Field(min_length=1)
    extracted_at: datetime

    def model_post_init(self, __context: object) -> None:
        if self.fact_type == FactType.ENTITY and self.entity_type is None:
            msg = "entity_type is required when fact_type is ENTITY"
            raise ValueError(msg)
