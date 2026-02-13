"""Unit tests for risk models — T201.

TDD Red: Write tests FIRST, verify they FAIL, then implement models.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestRiskLevel:
    """Verify RiskLevel enum values."""

    def test_level_values(self):
        from contractos.models.risk import RiskLevel

        assert RiskLevel.LOW == "low"
        assert RiskLevel.MEDIUM == "medium"
        assert RiskLevel.HIGH == "high"
        assert RiskLevel.CRITICAL == "critical"

    def test_level_count(self):
        from contractos.models.risk import RiskLevel

        assert len(RiskLevel) == 4


class TestRiskScore:
    """Verify RiskScore enforces severity/likelihood 1-5 and computes score."""

    def test_valid_risk_score(self):
        from contractos.models.risk import RiskLevel, RiskScore

        rs = RiskScore(
            severity=3,
            likelihood=4,
            severity_rationale="Moderate impact on operations",
            likelihood_rationale="Common in vendor contracts",
        )
        assert rs.severity == 3
        assert rs.likelihood == 4
        assert rs.score == 12
        assert rs.level == RiskLevel.HIGH

    def test_score_is_severity_times_likelihood(self):
        from contractos.models.risk import RiskScore

        rs = RiskScore(severity=2, likelihood=3)
        assert rs.score == 6  # 2 × 3

    def test_severity_min_1(self):
        from contractos.models.risk import RiskScore

        with pytest.raises(ValidationError):
            RiskScore(severity=0, likelihood=3)

    def test_severity_max_5(self):
        from contractos.models.risk import RiskScore

        with pytest.raises(ValidationError):
            RiskScore(severity=6, likelihood=3)

    def test_likelihood_min_1(self):
        from contractos.models.risk import RiskScore

        with pytest.raises(ValidationError):
            RiskScore(severity=3, likelihood=0)

    def test_likelihood_max_5(self):
        from contractos.models.risk import RiskScore

        with pytest.raises(ValidationError):
            RiskScore(severity=3, likelihood=6)

    # ── Risk Level derivation tests ──────────────────────────────

    def test_level_low_score_1(self):
        """Score 1 (1×1) → LOW."""
        from contractos.models.risk import RiskLevel, RiskScore

        rs = RiskScore(severity=1, likelihood=1)
        assert rs.score == 1
        assert rs.level == RiskLevel.LOW

    def test_level_low_score_4(self):
        """Score 4 (2×2) → LOW."""
        from contractos.models.risk import RiskLevel, RiskScore

        rs = RiskScore(severity=2, likelihood=2)
        assert rs.score == 4
        assert rs.level == RiskLevel.LOW

    def test_level_medium_score_5(self):
        """Score 5 (1×5) → MEDIUM."""
        from contractos.models.risk import RiskLevel, RiskScore

        rs = RiskScore(severity=1, likelihood=5)
        assert rs.score == 5
        assert rs.level == RiskLevel.MEDIUM

    def test_level_medium_score_9(self):
        """Score 9 (3×3) → MEDIUM."""
        from contractos.models.risk import RiskLevel, RiskScore

        rs = RiskScore(severity=3, likelihood=3)
        assert rs.score == 9
        assert rs.level == RiskLevel.MEDIUM

    def test_level_high_score_10(self):
        """Score 10 (2×5) → HIGH."""
        from contractos.models.risk import RiskLevel, RiskScore

        rs = RiskScore(severity=2, likelihood=5)
        assert rs.score == 10
        assert rs.level == RiskLevel.HIGH

    def test_level_high_score_15(self):
        """Score 15 (3×5) → HIGH."""
        from contractos.models.risk import RiskLevel, RiskScore

        rs = RiskScore(severity=3, likelihood=5)
        assert rs.score == 15
        assert rs.level == RiskLevel.HIGH

    def test_level_critical_score_16(self):
        """Score 16 (4×4) → CRITICAL."""
        from contractos.models.risk import RiskLevel, RiskScore

        rs = RiskScore(severity=4, likelihood=4)
        assert rs.score == 16
        assert rs.level == RiskLevel.CRITICAL

    def test_level_critical_score_25(self):
        """Score 25 (5×5) → CRITICAL."""
        from contractos.models.risk import RiskLevel, RiskScore

        rs = RiskScore(severity=5, likelihood=5)
        assert rs.score == 25
        assert rs.level == RiskLevel.CRITICAL


class TestRiskProfile:
    """Verify RiskProfile aggregation."""

    def test_valid_risk_profile(self):
        from contractos.models.risk import RiskLevel, RiskProfile

        rp = RiskProfile(
            overall_level=RiskLevel.HIGH,
            overall_score=12.5,
            highest_risk_finding="f-001",
            risk_distribution={"low": 3, "medium": 2, "high": 1, "critical": 0},
            tier_1_issues=1,
            tier_2_issues=2,
            tier_3_issues=3,
        )
        assert rp.overall_level == RiskLevel.HIGH
        assert rp.overall_score == 12.5
        assert rp.highest_risk_finding == "f-001"
        assert rp.risk_distribution["low"] == 3
        assert rp.tier_1_issues == 1

    def test_risk_profile_defaults(self):
        from contractos.models.risk import RiskLevel, RiskProfile

        rp = RiskProfile(
            overall_level=RiskLevel.LOW,
            overall_score=2.0,
            highest_risk_finding="",
            risk_distribution={},
            tier_1_issues=0,
            tier_2_issues=0,
            tier_3_issues=0,
        )
        assert rp.overall_level == RiskLevel.LOW
        assert rp.tier_1_issues == 0
