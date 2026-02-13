"""Unit tests for playbook models — T200.

TDD Red: Write tests FIRST, verify they FAIL, then implement models.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestNegotiationTier:
    """Verify NegotiationTier enum values."""

    def test_tier_values(self):
        from contractos.models.playbook import NegotiationTier

        assert NegotiationTier.TIER_1 == "tier_1"
        assert NegotiationTier.TIER_2 == "tier_2"
        assert NegotiationTier.TIER_3 == "tier_3"

    def test_tier_count(self):
        from contractos.models.playbook import NegotiationTier

        assert len(NegotiationTier) == 3


class TestAcceptableRange:
    """Verify AcceptableRange model."""

    def test_valid_range(self):
        from contractos.models.playbook import AcceptableRange

        r = AcceptableRange(
            min_position="6 months of fees",
            max_position="24 months of fees",
            description="Standard liability cap range",
        )
        assert r.min_position == "6 months of fees"
        assert r.max_position == "24 months of fees"
        assert r.description == "Standard liability cap range"

    def test_range_without_description(self):
        from contractos.models.playbook import AcceptableRange

        r = AcceptableRange(min_position="min", max_position="max")
        assert r.description == ""


class TestPlaybookPosition:
    """Verify PlaybookPosition requires clause_type and standard_position."""

    def test_valid_position(self):
        from contractos.models.playbook import NegotiationTier, PlaybookPosition

        pos = PlaybookPosition(
            clause_type="limitation_of_liability",
            standard_position="Mutual cap at 12 months of fees",
            escalation_triggers=["Uncapped liability"],
            priority=NegotiationTier.TIER_1,
            required=True,
        )
        assert pos.clause_type == "limitation_of_liability"
        assert pos.standard_position == "Mutual cap at 12 months of fees"
        assert pos.escalation_triggers == ["Uncapped liability"]
        assert pos.priority == NegotiationTier.TIER_1
        assert pos.required is True

    def test_position_requires_clause_type(self):
        from contractos.models.playbook import PlaybookPosition

        with pytest.raises(ValidationError):
            PlaybookPosition(
                standard_position="Some position",
            )

    def test_position_requires_standard_position(self):
        from contractos.models.playbook import PlaybookPosition

        with pytest.raises(ValidationError):
            PlaybookPosition(
                clause_type="termination",
            )

    def test_position_defaults(self):
        from contractos.models.playbook import NegotiationTier, PlaybookPosition

        pos = PlaybookPosition(
            clause_type="termination",
            standard_position="Either party may terminate with 30 days notice",
        )
        assert pos.acceptable_range is None
        assert pos.escalation_triggers == []
        assert pos.review_guidance == ""
        assert pos.priority == NegotiationTier.TIER_2
        assert pos.required is False

    def test_position_with_acceptable_range(self):
        from contractos.models.playbook import AcceptableRange, PlaybookPosition

        pos = PlaybookPosition(
            clause_type="payment",
            standard_position="Net 30",
            acceptable_range=AcceptableRange(
                min_position="Net 15",
                max_position="Net 60",
            ),
        )
        assert pos.acceptable_range is not None
        assert pos.acceptable_range.min_position == "Net 15"


class TestPlaybookConfig:
    """Verify PlaybookConfig validates from dict."""

    def test_valid_config(self):
        from contractos.models.playbook import PlaybookConfig, PlaybookPosition

        config = PlaybookConfig(
            name="Standard Commercial Playbook",
            version="1.0",
            positions={
                "termination": PlaybookPosition(
                    clause_type="termination",
                    standard_position="30 days notice",
                ),
            },
        )
        assert config.name == "Standard Commercial Playbook"
        assert config.version == "1.0"
        assert "termination" in config.positions
        assert config.positions["termination"].clause_type == "termination"

    def test_config_requires_name(self):
        from contractos.models.playbook import PlaybookConfig

        with pytest.raises(ValidationError):
            PlaybookConfig(positions={})

    def test_config_default_version(self):
        from contractos.models.playbook import PlaybookConfig

        config = PlaybookConfig(name="Test", positions={})
        assert config.version == "1.0"

    def test_config_empty_positions_allowed(self):
        from contractos.models.playbook import PlaybookConfig

        config = PlaybookConfig(name="Empty Playbook", positions={})
        assert len(config.positions) == 0

    def test_config_multiple_positions(self):
        from contractos.models.playbook import PlaybookConfig, PlaybookPosition

        config = PlaybookConfig(
            name="Full Playbook",
            positions={
                "termination": PlaybookPosition(
                    clause_type="termination",
                    standard_position="30 days notice",
                ),
                "payment": PlaybookPosition(
                    clause_type="payment",
                    standard_position="Net 30",
                ),
                "liability": PlaybookPosition(
                    clause_type="liability",
                    standard_position="Mutual cap at 12 months",
                    required=True,
                ),
            },
        )
        assert len(config.positions) == 3


class TestReviewSeverity:
    """Verify ReviewSeverity enum."""

    def test_severity_values(self):
        from contractos.models.review import ReviewSeverity

        assert ReviewSeverity.GREEN == "green"
        assert ReviewSeverity.YELLOW == "yellow"
        assert ReviewSeverity.RED == "red"

    def test_severity_count(self):
        from contractos.models.review import ReviewSeverity

        assert len(ReviewSeverity) == 3
