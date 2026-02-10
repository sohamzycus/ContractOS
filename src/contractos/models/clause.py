"""Clause and CrossReference models — structured units of legal meaning."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ClauseTypeEnum(StrEnum):
    """Types of clauses recognized in contracts."""

    TERMINATION = "termination"
    PAYMENT = "payment"
    INDEMNITY = "indemnity"
    LIABILITY = "liability"
    CONFIDENTIALITY = "confidentiality"
    SLA = "sla"
    PRICE_ESCALATION = "price_escalation"
    PENALTY = "penalty"
    FORCE_MAJEURE = "force_majeure"
    ASSIGNMENT = "assignment"
    GOVERNING_LAW = "governing_law"
    WARRANTY = "warranty"
    IP = "ip"
    SCHEDULE_ADHERENCE = "schedule_adherence"
    DEFINITIONS = "definitions"
    GENERAL = "general"
    CUSTOM = "custom"


class ReferenceType(StrEnum):
    """Types of cross-references within clauses."""

    SECTION_REF = "section_ref"
    CLAUSE_REF = "clause_ref"
    APPENDIX_REF = "appendix_ref"
    SCHEDULE_REF = "schedule_ref"
    EXTERNAL_DOC_REF = "external_doc_ref"


class ReferenceEffect(StrEnum):
    """The effect a cross-reference has on the target."""

    MODIFIES = "modifies"
    OVERRIDES = "overrides"
    CONDITIONS = "conditions"
    INCORPORATES = "incorporates"
    EXEMPTS = "exempts"
    DELEGATES = "delegates"


class CrossReference(BaseModel):
    """A reference from one clause to another clause, section, or appendix."""

    reference_id: str = Field(min_length=1)
    source_clause_id: str = Field(min_length=1)
    target_reference: str = Field(min_length=1)
    target_clause_id: str | None = None
    reference_type: ReferenceType
    effect: ReferenceEffect
    context: str = Field(min_length=1)
    resolved: bool = False
    source_fact_id: str = Field(min_length=1)


class Clause(BaseModel):
    """A structured unit of legal meaning within a contract."""

    clause_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    clause_type: ClauseTypeEnum
    heading: str = Field(min_length=1)
    section_number: str | None = None
    fact_id: str = Field(min_length=1)
    contained_fact_ids: list[str] = Field(default_factory=list)
    cross_reference_ids: list[str] = Field(default_factory=list)
    classification_method: str = Field(min_length=1)
    classification_confidence: float | None = None
