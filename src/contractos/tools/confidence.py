"""Confidence display utilities — map numeric confidence to human-readable labels."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConfidenceDisplay(BaseModel):
    """Human-readable confidence metadata for API responses."""

    value: float = Field(ge=0.0, le=1.0)
    label: str
    color: str
    description: str


def confidence_label(confidence: float | None) -> ConfidenceDisplay:
    """Map a confidence score to a human-readable label with color coding.

    Ranges:
        0.00–0.39 → speculative (red)
        0.40–0.59 → low (orange)
        0.60–0.79 → moderate (yellow)
        0.80–0.94 → high (green)
        0.95–1.00 → very_high (blue)
        None       → unknown (gray)
    """
    if confidence is None:
        return ConfidenceDisplay(
            value=0.0,
            label="unknown",
            color="gray",
            description="Confidence could not be determined",
        )

    if confidence < 0.0 or confidence > 1.0:
        msg = f"Confidence must be in [0.0, 1.0], got {confidence}"
        raise ValueError(msg)

    if confidence < 0.40:
        return ConfidenceDisplay(
            value=confidence,
            label="speculative",
            color="red",
            description="Very low confidence — answer is speculative",
        )
    if confidence < 0.60:
        return ConfidenceDisplay(
            value=confidence,
            label="low",
            color="orange",
            description="Low confidence — limited evidence supports this answer",
        )
    if confidence < 0.80:
        return ConfidenceDisplay(
            value=confidence,
            label="moderate",
            color="yellow",
            description="Moderate confidence — reasonable evidence supports this answer",
        )
    if confidence < 0.95:
        return ConfidenceDisplay(
            value=confidence,
            label="high",
            color="green",
            description="High confidence — strong evidence supports this answer",
        )
    return ConfidenceDisplay(
        value=confidence,
        label="very_high",
        color="blue",
        description="Very high confidence — answer is fully grounded in evidence",
    )
