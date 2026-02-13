"""DraftAgent — generates specific alternative contract language for YELLOW/RED findings.

The DraftAgent receives a ReviewFinding and generates a RedlineSuggestion with:
- Proposed alternative language
- Rationale suitable for sharing with counterparty
- Priority tier
- Fallback language for Tier 1 findings
"""

from __future__ import annotations

import json
import logging
from typing import Any

from contractos.llm.provider import LLMMessage, LLMProvider
from contractos.models.playbook import NegotiationTier, PlaybookPosition
from contractos.models.review import RedlineSuggestion, ReviewFinding
from contractos.tools.fact_discovery import _parse_lenient_json

logger = logging.getLogger(__name__)

REDLINE_GENERATION_PROMPT = """You are ContractOS DraftAgent — an expert contract drafter.

Given a clause that deviates from the organization's standard position, generate specific
alternative language that brings the clause closer to the standard position.

Your output must be suitable for sharing with the counterparty — professional, specific,
and legally precise. Do not include internal strategy notes.

Respond in JSON format:
{
  "proposed_language": "The exact replacement text for the clause",
  "rationale": "Why this change is proposed (suitable for counterparty)",
  "priority": "tier_1|tier_2|tier_3",
  "fallback_language": "Alternative if primary is rejected (optional, for tier_1 only)"
}"""


class DraftAgent:
    """Generates redline suggestions for contract clause deviations."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def generate_redline(
        self,
        finding: ReviewFinding,
        position: PlaybookPosition,
        user_side: str,
    ) -> RedlineSuggestion | None:
        """Generate a redline suggestion for a finding.

        Args:
            finding: The review finding (YELLOW or RED).
            position: The playbook position being compared against.
            user_side: "buyer" or "seller".

        Returns:
            RedlineSuggestion or None if generation fails.
        """
        prompt = f"""## Current Clause Language
{finding.current_language}

## Deviation
{finding.deviation_description}

## Playbook Standard Position
{position.standard_position}

## Business Impact
{finding.business_impact}

## Context
- Clause Type: {finding.clause_type}
- User Side: {user_side}
- Severity: {finding.severity.value}
- Priority: {position.priority.value}

Generate specific alternative language that addresses this deviation."""

        try:
            messages = [LLMMessage(role="user", content=prompt)]
            response = await self._llm.complete(
                messages, system=REDLINE_GENERATION_PROMPT, temperature=0.0, max_tokens=2048
            )
            result = _parse_lenient_json(response.content)
            return self._parse_redline(result, position)
        except Exception as e:
            logger.error("Redline generation failed: %s", e)
            return None

    def _parse_redline(
        self, data: dict[str, Any], position: PlaybookPosition
    ) -> RedlineSuggestion | None:
        """Parse LLM response into a RedlineSuggestion."""
        proposed = data.get("proposed_language", "")
        rationale = data.get("rationale", "")

        if not proposed or not rationale:
            return None

        # Parse priority
        priority_str = data.get("priority", position.priority.value)
        try:
            priority = NegotiationTier(priority_str)
        except ValueError:
            priority = position.priority

        fallback = data.get("fallback_language")

        return RedlineSuggestion(
            proposed_language=proposed,
            rationale=rationale,
            priority=priority,
            fallback_language=fallback if fallback else None,
        )
