"""Opinion model — contextual judgments, never persisted as truth."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class OpinionType(StrEnum):
    """Types of opinions ContractOS can generate."""

    RISK_ASSESSMENT = "risk_assessment"
    COMPLIANCE_CHECK = "compliance_check"
    BENCHMARK_COMPARISON = "benchmark_comparison"
    POLICY_ALIGNMENT = "policy_alignment"
    RECOMMENDATION = "recommendation"


class Severity(StrEnum):
    """Severity levels for opinions."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Opinion(BaseModel):
    """A contextual judgment — computed on demand, never persisted as truth.

    Opinions depend on policy, risk tolerance, role, and jurisdiction.
    They are never ground truth.
    """

    opinion_id: str = Field(min_length=1)
    opinion_type: OpinionType
    judgment: str = Field(min_length=1)
    supporting_inference_ids: list[str] = Field(default_factory=list)
    supporting_fact_ids: list[str] = Field(default_factory=list)
    policy_reference: str | None = None
    benchmark: str | None = None
    role_context: str = Field(min_length=1)
    jurisdiction: str | None = None
    severity: Severity
    generated_at: datetime
