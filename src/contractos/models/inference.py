"""Inference model — probabilistic derived claims combining facts and domain knowledge."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class InferenceType(StrEnum):
    """Types of inferences ContractOS can generate."""

    OBLIGATION = "obligation"
    COVERAGE = "coverage"
    SIMILARITY = "similarity"
    COMPLIANCE_GAP = "compliance_gap"
    RISK_INDICATOR = "risk_indicator"
    ENTITY_RESOLUTION = "entity_resolution"
    SCOPE_DETERMINATION = "scope_determination"
    NEGATION = "negation"


class Inference(BaseModel):
    """A probabilistic derived claim combining facts, bindings, and domain knowledge.

    Inferences must always reference supporting facts. They carry confidence
    scores calibrated against expert judgment.
    """

    inference_id: str = Field(min_length=1)
    inference_type: InferenceType
    claim: str = Field(min_length=1)
    supporting_fact_ids: list[str] = Field(min_length=1)
    supporting_binding_ids: list[str] = Field(default_factory=list)
    domain_sources: list[str] = Field(default_factory=list)
    reasoning_chain: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_basis: str = Field(min_length=1)
    generated_by: str = Field(min_length=1)
    generated_at: datetime
    document_id: str = Field(min_length=1)
    query_id: str | None = None
    invalidated_by: str | None = None

    @property
    def is_low_confidence(self) -> bool:
        """Inferences below 0.5 require human review."""
        return self.confidence < 0.5
