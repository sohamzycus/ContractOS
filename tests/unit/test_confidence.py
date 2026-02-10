"""Unit tests for confidence display utilities."""

from __future__ import annotations

import pytest

from contractos.tools.confidence import ConfidenceDisplay, confidence_label


class TestConfidenceLabel:
    """Test confidence → label mapping."""

    def test_speculative_low_end(self) -> None:
        result = confidence_label(0.0)
        assert result.label == "speculative"
        assert result.color == "red"

    def test_speculative_high_end(self) -> None:
        result = confidence_label(0.39)
        assert result.label == "speculative"
        assert result.color == "red"

    def test_low_boundary(self) -> None:
        result = confidence_label(0.40)
        assert result.label == "low"
        assert result.color == "orange"

    def test_low_mid(self) -> None:
        result = confidence_label(0.50)
        assert result.label == "low"
        assert result.color == "orange"

    def test_moderate_boundary(self) -> None:
        result = confidence_label(0.60)
        assert result.label == "moderate"
        assert result.color == "yellow"

    def test_moderate_mid(self) -> None:
        result = confidence_label(0.75)
        assert result.label == "moderate"
        assert result.color == "yellow"

    def test_high_boundary(self) -> None:
        result = confidence_label(0.80)
        assert result.label == "high"
        assert result.color == "green"

    def test_high_mid(self) -> None:
        result = confidence_label(0.90)
        assert result.label == "high"
        assert result.color == "green"

    def test_very_high_boundary(self) -> None:
        result = confidence_label(0.95)
        assert result.label == "very_high"
        assert result.color == "blue"

    def test_very_high_max(self) -> None:
        result = confidence_label(1.0)
        assert result.label == "very_high"
        assert result.color == "blue"

    def test_none_confidence(self) -> None:
        result = confidence_label(None)
        assert result.label == "unknown"
        assert result.color == "gray"
        assert result.value == 0.0

    def test_out_of_range_negative(self) -> None:
        with pytest.raises(ValueError, match="Confidence must be"):
            confidence_label(-0.1)

    def test_out_of_range_above(self) -> None:
        with pytest.raises(ValueError, match="Confidence must be"):
            confidence_label(1.1)

    def test_description_present(self) -> None:
        result = confidence_label(0.85)
        assert len(result.description) > 0

    def test_returns_confidence_display(self) -> None:
        result = confidence_label(0.5)
        assert isinstance(result, ConfidenceDisplay)
        assert result.value == 0.5
