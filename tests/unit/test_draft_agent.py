"""Unit tests for DraftAgent — T217.

TDD Red: Write tests FIRST, verify they FAIL, then implement agent.
"""

from __future__ import annotations

import json

import pytest

from contractos.llm.provider import MockLLMProvider
from contractos.models.playbook import NegotiationTier, PlaybookPosition
from contractos.models.review import ReviewFinding, ReviewSeverity
from contractos.models.risk import RiskScore


@pytest.fixture
def mock_llm():
    return MockLLMProvider()


@pytest.fixture
def sample_finding():
    return ReviewFinding(
        finding_id="rf-001",
        clause_id="c-liab-001",
        clause_type="liability",
        clause_heading="8.1 Limitation of Liability",
        severity=ReviewSeverity.RED,
        current_language="The Supplier shall have uncapped liability for all claims.",
        playbook_position="Mutual cap at 12 months of fees",
        deviation_description="Uncapped liability — no cap on supplier's exposure",
        business_impact="Unlimited financial exposure for the supplier",
        risk_score=RiskScore(severity=5, likelihood=4),
        provenance_facts=["f-liab-001"],
    )


@pytest.fixture
def sample_position():
    return PlaybookPosition(
        clause_type="liability",
        standard_position="Mutual cap at 12 months of fees",
        priority=NegotiationTier.TIER_1,
        required=True,
    )


class TestDraftAgentRedline:
    """Test DraftAgent.generate_redline()."""

    @pytest.mark.asyncio
    async def test_generates_redline_suggestion(self, mock_llm, sample_finding, sample_position):
        from contractos.agents.draft_agent import DraftAgent
        from contractos.models.review import RedlineSuggestion

        mock_llm.add_response(json.dumps({
            "proposed_language": "The total aggregate liability of each party shall not exceed the fees paid or payable in the 12 months preceding the claim.",
            "rationale": "Establishes a mutual, proportional liability cap tied to contract value.",
            "priority": "tier_1",
            "fallback_language": "The total aggregate liability of each party shall not exceed the greater of (a) fees paid in the prior 12 months or (b) $1,000,000.",
        }))

        agent = DraftAgent(mock_llm)
        redline = await agent.generate_redline(sample_finding, sample_position, "buyer")

        assert redline is not None
        assert isinstance(redline, RedlineSuggestion)
        assert len(redline.proposed_language) > 0
        assert redline.proposed_language != sample_finding.current_language
        assert len(redline.rationale) > 0

    @pytest.mark.asyncio
    async def test_redline_has_priority(self, mock_llm, sample_finding, sample_position):
        from contractos.agents.draft_agent import DraftAgent

        mock_llm.add_response(json.dumps({
            "proposed_language": "Liability capped at 12 months of fees.",
            "rationale": "Standard market position.",
            "priority": "tier_1",
        }))

        agent = DraftAgent(mock_llm)
        redline = await agent.generate_redline(sample_finding, sample_position, "buyer")

        assert redline is not None
        assert redline.priority == NegotiationTier.TIER_1

    @pytest.mark.asyncio
    async def test_tier_1_has_fallback(self, mock_llm, sample_finding, sample_position):
        from contractos.agents.draft_agent import DraftAgent

        mock_llm.add_response(json.dumps({
            "proposed_language": "Cap at 12 months.",
            "rationale": "Standard.",
            "priority": "tier_1",
            "fallback_language": "Cap at 24 months as compromise.",
        }))

        agent = DraftAgent(mock_llm)
        redline = await agent.generate_redline(sample_finding, sample_position, "buyer")

        assert redline is not None
        assert redline.fallback_language is not None

    @pytest.mark.asyncio
    async def test_llm_failure_returns_none(self, mock_llm, sample_finding, sample_position):
        """If LLM fails, redline generation returns None gracefully."""
        from contractos.agents.draft_agent import DraftAgent

        # No response added — will raise IndexError
        agent = DraftAgent(mock_llm)
        redline = await agent.generate_redline(sample_finding, sample_position, "buyer")

        assert redline is None

    @pytest.mark.asyncio
    async def test_yellow_finding_redline(self, mock_llm, sample_position):
        """YELLOW findings also get redlines."""
        from contractos.agents.draft_agent import DraftAgent

        yellow_finding = ReviewFinding(
            finding_id="rf-002",
            clause_id="c-term-001",
            clause_type="termination",
            severity=ReviewSeverity.YELLOW,
            current_language="Termination with 15 days notice.",
            playbook_position="30 days notice",
            deviation_description="15 days vs 30 days notice",
        )

        mock_llm.add_response(json.dumps({
            "proposed_language": "Either party may terminate with 30 days written notice.",
            "rationale": "Aligns with standard notice period.",
            "priority": "tier_2",
        }))

        agent = DraftAgent(mock_llm)
        redline = await agent.generate_redline(yellow_finding, sample_position, "buyer")

        assert redline is not None
        assert redline.priority == NegotiationTier.TIER_2
