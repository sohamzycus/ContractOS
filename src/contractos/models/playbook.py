"""Playbook models — configurable organizational positions for contract review.

Part of the Truth Model: PlaybookConfig is Configuration (organization-defined),
not extracted from documents.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class NegotiationTier(StrEnum):
    """Priority tiers for negotiation strategy."""

    TIER_1 = "tier_1"  # Must-have (deal breakers)
    TIER_2 = "tier_2"  # Should-have (strong preferences)
    TIER_3 = "tier_3"  # Nice-to-have (concession candidates)


class AcceptableRange(BaseModel):
    """Defines the acceptable range for a clause position."""

    min_position: str
    max_position: str
    description: str = ""


class PlaybookPosition(BaseModel):
    """An organization's standard position for a specific clause type."""

    clause_type: str = Field(min_length=1)
    standard_position: str = Field(min_length=1)
    acceptable_range: AcceptableRange | None = None
    escalation_triggers: list[str] = Field(default_factory=list)
    review_guidance: str = ""
    priority: NegotiationTier = NegotiationTier.TIER_2
    required: bool = False


class PlaybookConfig(BaseModel):
    """Root configuration for an organization's contract review playbook."""

    name: str = Field(min_length=1)
    version: str = "1.0"
    positions: dict[str, PlaybookPosition]
