"""Review models — playbook review findings and results.

Part of the Truth Model:
- ReviewFinding severity is an Opinion (role-dependent, policy-dependent judgment)
- RedlineSuggestion is an Opinion (generated alternative, not grounded in document)
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from contractos.models.playbook import NegotiationTier
from contractos.models.risk import RiskLevel, RiskProfile, RiskScore


class ReviewSeverity(StrEnum):
    """Severity classification for a playbook review finding."""

    GREEN = "green"    # Acceptable — aligns with or better than standard
    YELLOW = "yellow"  # Negotiate — outside standard but within range
    RED = "red"        # Escalate — outside acceptable range or triggers escalation


class RedlineSuggestion(BaseModel):
    """Specific alternative language for a YELLOW/RED finding."""

    proposed_language: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    priority: NegotiationTier
    fallback_language: str | None = None


class ReviewFinding(BaseModel):
    """A single clause-level finding from a playbook review."""

    finding_id: str = Field(min_length=1)
    clause_id: str = ""
    clause_type: str = Field(min_length=1)
    clause_heading: str = ""
    severity: ReviewSeverity
    current_language: str = ""
    playbook_position: str = ""
    deviation_description: str = ""
    business_impact: str = ""
    risk_score: RiskScore | None = None
    redline: RedlineSuggestion | None = None
    provenance_facts: list[str] = Field(default_factory=list)
    char_start: int = 0
    char_end: int = 0


class ReviewResult(BaseModel):
    """Complete playbook review result for a contract."""

    document_id: str = Field(min_length=1)
    playbook_name: str = ""
    findings: list[ReviewFinding] = Field(default_factory=list)
    summary: str = ""
    risk_profile: RiskProfile | None = None
    negotiation_strategy: str = ""
    review_time_ms: int = 0
    green_count: int = 0
    yellow_count: int = 0
    red_count: int = 0
    missing_clauses: list[str] = Field(default_factory=list)
