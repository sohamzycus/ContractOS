"""Clause and CrossReference models — structured units of legal meaning."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ClauseTypeEnum(StrEnum):
    """Types of clauses recognized in contracts."""

    TERMINATION = "termination"
    PAYMENT = "payment"
    INDEMNITY = "indemnity"
    INDEMNIFICATION = "indemnification"
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
    IP_RIGHTS = "ip_rights"
    SCHEDULE_ADHERENCE = "schedule_adherence"
    DEFINITIONS = "definitions"
    DISPUTE_RESOLUTION = "dispute_resolution"
    NOTICE = "notice"
    INSURANCE = "insurance"
    COMPLIANCE = "compliance"
    DATA_PROTECTION = "data_protection"
    NON_COMPETE = "non_compete"
    SCOPE = "scope"
    GENERAL = "general"
    CUSTOM = "custom"


class ReferenceType(StrEnum):
    """Types of cross-references within clauses."""

    SECTION_REF = "section_ref"
    CLAUSE_REF = "clause_ref"
    APPENDIX_REF = "appendix_ref"
    SCHEDULE_REF = "schedule_ref"
    EXHIBIT_REF = "exhibit_ref"
    ANNEX_REF = "annex_ref"
    EXTERNAL_DOC_REF = "external_doc_ref"


class ReferenceEffect(StrEnum):
    """The effect a cross-reference has on the target."""

    MODIFIES = "modifies"
    OVERRIDES = "overrides"
    CONDITIONS = "conditions"
    INCORPORATES = "incorporates"
    EXEMPTS = "exempts"
    DELEGATES = "delegates"
    REFERENCES = "references"
    LIMITS = "limits"
    DEFINES = "defines"


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
    source_fact_id: str = ""


class Clause(BaseModel):
    """A structured unit of legal meaning within a contract."""

    clause_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    clause_type: ClauseTypeEnum
    heading: str = Field(min_length=1)
    section_number: str | None = None
    fact_id: str = ""
    contained_fact_ids: list[str] = Field(default_factory=list)
    cross_reference_ids: list[str] = Field(default_factory=list)
    classification_method: str = Field(min_length=1)
    classification_confidence: float | None = None
