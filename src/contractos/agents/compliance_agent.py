"""ComplianceAgent — compares extracted clauses against a configurable playbook.

Hybrid classification pipeline:
1. Rule-based pre-classification (deterministic):
   - Missing required clause → automatic RED
   - Escalation trigger pattern match → force RED
2. LLM-assisted classification (grounded):
   - Send clause text + playbook position to LLM
   - LLM returns severity, deviation description, business impact, risk score
3. Risk profile aggregation

Every finding is backed by extracted facts with provenance chains.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

from contractos.fabric.trust_graph import TrustGraph
from contractos.llm.provider import LLMMessage, LLMProvider
from contractos.models.clause import Clause
from contractos.models.fact import Fact
from contractos.models.playbook import NegotiationTier, PlaybookConfig, PlaybookPosition
from contractos.models.review import ReviewFinding, ReviewResult, ReviewSeverity
from contractos.models.risk import RiskLevel, RiskProfile, RiskScore
from contractos.tools.fact_discovery import _parse_lenient_json

logger = logging.getLogger(__name__)

COMPLIANCE_REVIEW_PROMPT = """You are ContractOS ComplianceAgent — an expert contract reviewer.

You are comparing a specific clause from a contract against an organization's playbook position.
Your job is to classify the clause as GREEN, YELLOW, or RED:

- **GREEN**: The clause aligns with or is better than the organization's standard position.
- **YELLOW**: The clause deviates from the standard but is within the acceptable range. Negotiation recommended.
- **RED**: The clause is outside the acceptable range or poses significant risk. Escalation required.

For each classification, provide:
1. severity: "green", "yellow", or "red"
2. deviation_description: What specifically deviates from the standard position
3. business_impact: Practical impact of accepting this clause as-is
4. risk_score: { "severity": 1-5, "likelihood": 1-5 } where:
   - severity = impact if the risk materializes (1=minimal, 5=catastrophic)
   - likelihood = probability of the risk materializing (1=unlikely, 5=almost certain)

Respond ONLY in JSON format:
{
  "severity": "green|yellow|red",
  "deviation_description": "...",
  "business_impact": "...",
  "risk_score": { "severity": 1, "likelihood": 1 }
}"""


class ComplianceAgent:
    """Reviews contract clauses against a playbook, producing findings with provenance."""

    def __init__(self, trust_graph: TrustGraph, llm: LLMProvider) -> None:
        self._graph = trust_graph
        self._llm = llm

    async def review(
        self,
        document_id: str,
        playbook: PlaybookConfig,
        *,
        user_side: str = "buyer",
        focus_areas: list[str] | None = None,
        generate_redlines: bool = False,
    ) -> ReviewResult:
        """Run a playbook review on a contract.

        Args:
            document_id: The contract to review.
            playbook: Playbook configuration with positions.
            user_side: "buyer" or "seller" — affects perspective.
            focus_areas: Optional list of clause types to focus on.
            generate_redlines: Whether to generate redline suggestions.

        Returns:
            ReviewResult with per-clause findings, risk profile, and strategy.

        Raises:
            ValueError: If the document is not found.
        """
        start_time = time.monotonic()

        # Verify document exists
        contract = self._graph.get_contract(document_id)
        if contract is None:
            raise ValueError(f"Document not found: {document_id}")

        # Load clauses and facts
        clauses = self._graph.get_clauses_by_document(document_id)
        facts = self._graph.get_facts_by_document(document_id)
        fact_lookup = {f.fact_id: f for f in facts}

        # Build clause lookup by type
        clause_by_type: dict[str, list[Clause]] = {}
        for clause in clauses:
            ct = clause.clause_type.value
            clause_by_type.setdefault(ct, []).append(clause)

        findings: list[ReviewFinding] = []

        # Review each playbook position
        for pos_key, position in playbook.positions.items():
            # Skip if focus_areas specified and this isn't in focus
            if focus_areas and position.clause_type not in focus_areas:
                continue

            ct = position.clause_type
            matching_clauses = clause_by_type.get(ct, [])

            if not matching_clauses:
                # Missing clause
                if position.required:
                    findings.append(self._missing_clause_finding(position))
                continue

            # Review each matching clause
            for clause in matching_clauses:
                finding = await self._review_clause(
                    clause, position, fact_lookup, user_side
                )
                findings.append(finding)

        # Build risk profile
        risk_profile = self._build_risk_profile(findings)

        # Generate negotiation strategy
        strategy = await self._generate_strategy(findings, playbook)

        # Count severities
        green_count = sum(1 for f in findings if f.severity == ReviewSeverity.GREEN)
        yellow_count = sum(1 for f in findings if f.severity == ReviewSeverity.YELLOW)
        red_count = sum(1 for f in findings if f.severity == ReviewSeverity.RED)

        # Missing clauses
        missing = [
            f.clause_type for f in findings
            if "missing" in f.deviation_description.lower() and f.severity == ReviewSeverity.RED
        ]

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        return ReviewResult(
            document_id=document_id,
            playbook_name=playbook.name,
            findings=findings,
            summary=self._build_summary(findings, playbook.name),
            risk_profile=risk_profile,
            negotiation_strategy=strategy,
            review_time_ms=elapsed_ms,
            green_count=green_count,
            yellow_count=yellow_count,
            red_count=red_count,
            missing_clauses=missing,
        )

    async def _review_clause(
        self,
        clause: Clause,
        position: PlaybookPosition,
        fact_lookup: dict[str, Fact],
        user_side: str,
    ) -> ReviewFinding:
        """Review a single clause against a playbook position.

        Pipeline:
        1. Get clause text from contained facts
        2. Check escalation triggers (deterministic)
        3. If no trigger → LLM classification
        4. Build finding with provenance
        """
        # Get clause text from facts
        clause_text = self._get_clause_text(clause, fact_lookup)
        provenance_facts = list(clause.contained_fact_ids) if clause.contained_fact_ids else []
        if clause.fact_id and clause.fact_id not in provenance_facts:
            provenance_facts.insert(0, clause.fact_id)

        # Get char offsets from the primary fact
        char_start = 0
        char_end = 0
        if clause.fact_id and clause.fact_id in fact_lookup:
            primary_fact = fact_lookup[clause.fact_id]
            char_start = primary_fact.evidence.char_start
            char_end = primary_fact.evidence.char_end

        # Step 1: Check escalation triggers (deterministic override)
        triggered = self._check_escalation_triggers(clause_text, position.escalation_triggers)
        if triggered:
            return ReviewFinding(
                finding_id=f"rf-{uuid.uuid4().hex[:8]}",
                clause_id=clause.clause_id,
                clause_type=clause.clause_type.value,
                clause_heading=clause.heading,
                severity=ReviewSeverity.RED,
                current_language=clause_text[:500],
                playbook_position=position.standard_position,
                deviation_description=f"Escalation trigger matched: {triggered}",
                business_impact=f"Critical risk — escalation trigger '{triggered}' detected in clause text",
                risk_score=RiskScore(severity=5, likelihood=4),
                provenance_facts=provenance_facts,
                char_start=char_start,
                char_end=char_end,
            )

        # Step 2: LLM classification
        try:
            llm_result = await self._llm_classify(clause_text, position, user_side)
            severity_str = llm_result.get("severity", "yellow")
            severity = ReviewSeverity(severity_str) if severity_str in ("green", "yellow", "red") else ReviewSeverity.YELLOW

            # Parse risk score
            risk_data = llm_result.get("risk_score", {})
            risk_score = None
            if isinstance(risk_data, dict) and "severity" in risk_data and "likelihood" in risk_data:
                try:
                    risk_score = RiskScore(
                        severity=int(risk_data["severity"]),
                        likelihood=int(risk_data["likelihood"]),
                    )
                except Exception:
                    risk_score = RiskScore(severity=2, likelihood=2)

            return ReviewFinding(
                finding_id=f"rf-{uuid.uuid4().hex[:8]}",
                clause_id=clause.clause_id,
                clause_type=clause.clause_type.value,
                clause_heading=clause.heading,
                severity=severity,
                current_language=clause_text[:500],
                playbook_position=position.standard_position,
                deviation_description=llm_result.get("deviation_description", ""),
                business_impact=llm_result.get("business_impact", ""),
                risk_score=risk_score,
                provenance_facts=provenance_facts,
                char_start=char_start,
                char_end=char_end,
            )
        except Exception as e:
            logger.error("LLM classification failed for clause %s: %s", clause.clause_id, e)
            return ReviewFinding(
                finding_id=f"rf-{uuid.uuid4().hex[:8]}",
                clause_id=clause.clause_id,
                clause_type=clause.clause_type.value,
                clause_heading=clause.heading,
                severity=ReviewSeverity.YELLOW,
                current_language=clause_text[:500],
                playbook_position=position.standard_position,
                deviation_description=f"Classification error: {e}",
                business_impact="Unable to assess — manual review recommended",
                provenance_facts=provenance_facts,
                char_start=char_start,
                char_end=char_end,
            )

    def _missing_clause_finding(self, position: PlaybookPosition) -> ReviewFinding:
        """Create a RED finding for a missing required clause."""
        return ReviewFinding(
            finding_id=f"rf-{uuid.uuid4().hex[:8]}",
            clause_id="",
            clause_type=position.clause_type,
            clause_heading=f"Missing: {position.clause_type}",
            severity=ReviewSeverity.RED,
            current_language="",
            playbook_position=position.standard_position,
            deviation_description=f"Missing required clause: {position.clause_type}. "
                f"The playbook requires this clause but it was not found in the contract.",
            business_impact=f"No {position.clause_type} protection — significant risk exposure",
            risk_score=RiskScore(severity=4, likelihood=4),
            provenance_facts=[],
        )

    def _get_clause_text(self, clause: Clause, fact_lookup: dict[str, Fact]) -> str:
        """Extract the full text of a clause from its contained facts."""
        texts = []
        # Primary fact
        if clause.fact_id and clause.fact_id in fact_lookup:
            texts.append(fact_lookup[clause.fact_id].value)
        # Contained facts
        for fid in clause.contained_fact_ids:
            if fid in fact_lookup and fid != clause.fact_id:
                texts.append(fact_lookup[fid].value)
        return " ".join(texts) if texts else clause.heading

    def _check_escalation_triggers(
        self, clause_text: str, triggers: list[str]
    ) -> str | None:
        """Check if any escalation trigger pattern matches the clause text.

        Returns the matched trigger or None.
        """
        text_lower = clause_text.lower()
        for trigger in triggers:
            if trigger.lower() in text_lower:
                return trigger
        return None

    async def _llm_classify(
        self, clause_text: str, position: PlaybookPosition, user_side: str
    ) -> dict[str, Any]:
        """Send clause + playbook position to LLM for classification."""
        prompt = f"""## Clause Text
{clause_text}

## Playbook Position
- Clause Type: {position.clause_type}
- Standard Position: {position.standard_position}
- Acceptable Range: {position.acceptable_range.min_position + ' to ' + position.acceptable_range.max_position if position.acceptable_range else 'Not specified'}
- Priority: {position.priority.value}
- Review Guidance: {position.review_guidance or 'None'}

## Context
- User Side: {user_side}
- Required Clause: {'Yes' if position.required else 'No'}

Compare the clause text against the playbook position and classify as GREEN, YELLOW, or RED."""

        messages = [LLMMessage(role="user", content=prompt)]
        response = await self._llm.complete(
            messages, system=COMPLIANCE_REVIEW_PROMPT, temperature=0.0, max_tokens=2048
        )
        return _parse_lenient_json(response.content)

    def _build_risk_profile(self, findings: list[ReviewFinding]) -> RiskProfile:
        """Aggregate findings into a risk profile."""
        if not findings:
            return RiskProfile(
                overall_level=RiskLevel.LOW,
                overall_score=0.0,
                highest_risk_finding="",
                risk_distribution={"low": 0, "medium": 0, "high": 0, "critical": 0},
                tier_1_issues=0,
                tier_2_issues=0,
                tier_3_issues=0,
            )

        # Compute distribution
        distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        scores: list[int] = []
        highest_score = 0
        highest_finding = ""

        for f in findings:
            if f.risk_score:
                scores.append(f.risk_score.score)
                distribution[f.risk_score.level.value] += 1
                if f.risk_score.score > highest_score:
                    highest_score = f.risk_score.score
                    highest_finding = f.finding_id
            else:
                # Default score based on severity
                if f.severity == ReviewSeverity.RED:
                    distribution["high"] += 1
                    scores.append(12)
                elif f.severity == ReviewSeverity.YELLOW:
                    distribution["medium"] += 1
                    scores.append(6)
                else:
                    distribution["low"] += 1
                    scores.append(2)

        avg_score = sum(scores) / len(scores) if scores else 0
        overall_level = _derive_level_from_score(avg_score)

        # Count tier issues (RED and YELLOW findings)
        red_findings = [f for f in findings if f.severity == ReviewSeverity.RED]
        yellow_findings = [f for f in findings if f.severity == ReviewSeverity.YELLOW]

        return RiskProfile(
            overall_level=overall_level,
            overall_score=round(avg_score, 1),
            highest_risk_finding=highest_finding,
            risk_distribution=distribution,
            tier_1_issues=len(red_findings),
            tier_2_issues=len(yellow_findings),
            tier_3_issues=0,
        )

    async def _generate_strategy(
        self, findings: list[ReviewFinding], playbook: PlaybookConfig
    ) -> str:
        """Generate a negotiation strategy summary using LLM."""
        if not findings:
            return "No findings to negotiate."

        red = [f for f in findings if f.severity == ReviewSeverity.RED]
        yellow = [f for f in findings if f.severity == ReviewSeverity.YELLOW]

        if not red and not yellow:
            return "All clauses align with playbook positions. No negotiation needed."

        summary_parts = []
        if red:
            summary_parts.append(f"RED issues ({len(red)}): " + ", ".join(
                f"{f.clause_type}: {f.deviation_description[:80]}" for f in red
            ))
        if yellow:
            summary_parts.append(f"YELLOW issues ({len(yellow)}): " + ", ".join(
                f"{f.clause_type}: {f.deviation_description[:80]}" for f in yellow
            ))

        prompt = f"""Based on these contract review findings, generate a brief negotiation strategy:

{chr(10).join(summary_parts)}

Organize by priority tier:
- Tier 1 (Must-have): Issues that are deal-breakers
- Tier 2 (Should-have): Issues worth negotiating
- Tier 3 (Nice-to-have): Concession candidates

Keep the strategy under 200 words."""

        try:
            messages = [LLMMessage(role="user", content=prompt)]
            response = await self._llm.complete(
                messages, temperature=0.0, max_tokens=1024
            )
            return response.content.strip()
        except Exception as e:
            logger.error("Strategy generation failed: %s", e)
            parts = []
            if red:
                parts.append(f"Tier 1 (Must-fix): {len(red)} RED issues require immediate attention.")
            if yellow:
                parts.append(f"Tier 2 (Negotiate): {len(yellow)} YELLOW issues should be addressed.")
            return " ".join(parts) if parts else "Review findings and prioritize negotiations."

    def _build_summary(self, findings: list[ReviewFinding], playbook_name: str) -> str:
        """Build an executive summary of the review."""
        green = sum(1 for f in findings if f.severity == ReviewSeverity.GREEN)
        yellow = sum(1 for f in findings if f.severity == ReviewSeverity.YELLOW)
        red = sum(1 for f in findings if f.severity == ReviewSeverity.RED)
        total = len(findings)

        if red == 0 and yellow == 0:
            return f"Playbook review ({playbook_name}): All {total} clauses align with standard positions."
        return (
            f"Playbook review ({playbook_name}): {total} clauses reviewed — "
            f"{green} GREEN, {yellow} YELLOW, {red} RED."
        )


def _derive_level_from_score(score: float) -> RiskLevel:
    """Derive risk level from an average score."""
    if score <= 4:
        return RiskLevel.LOW
    if score <= 9:
        return RiskLevel.MEDIUM
    if score <= 15:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL
