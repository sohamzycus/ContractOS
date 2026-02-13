"""Risk models — 5×5 Severity × Likelihood risk assessment framework.

Part of the Truth Model: RiskScore is an Inference (derived from facts + playbook).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class RiskLevel(StrEnum):
    """Risk levels derived from score thresholds."""

    LOW = "low"          # Score 1-4
    MEDIUM = "medium"    # Score 5-9
    HIGH = "high"        # Score 10-15
    CRITICAL = "critical"  # Score 16-25


def _derive_level(score: int) -> RiskLevel:
    """Derive risk level from a numeric score (1-25)."""
    if score <= 4:
        return RiskLevel.LOW
    if score <= 9:
        return RiskLevel.MEDIUM
    if score <= 15:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


class RiskScore(BaseModel):
    """5×5 Severity × Likelihood risk assessment.

    Score is computed as severity × likelihood (1-25).
    Level is derived from score thresholds.
    """

    severity: int = Field(ge=1, le=5)
    likelihood: int = Field(ge=1, le=5)
    score: int = 0
    level: RiskLevel = RiskLevel.LOW
    severity_rationale: str = ""
    likelihood_rationale: str = ""

    @model_validator(mode="after")
    def _compute_score_and_level(self) -> RiskScore:
        self.score = self.severity * self.likelihood
        self.level = _derive_level(self.score)
        return self


class RiskProfile(BaseModel):
    """Aggregate risk profile for a contract."""

    overall_level: RiskLevel
    overall_score: float
    highest_risk_finding: str
    risk_distribution: dict[str, int]
    tier_1_issues: int
    tier_2_issues: int
    tier_3_issues: int
