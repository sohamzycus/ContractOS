"""NDATriageAgent — automated 10-point NDA screening with GREEN/YELLOW/RED classification.

Evaluates an NDA against a configurable checklist using a mix of:
- Automated pattern matching on extracted facts/clauses
- LLM verification for nuanced judgment

Classification logic:
- All PASS → GREEN (route for signature)
- Any non-critical FAIL → YELLOW (counsel review)
- Any critical FAIL → RED (full review required)
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from contractos.fabric.trust_graph import TrustGraph
from contractos.llm.provider import LLMMessage, LLMProvider
from contractos.models.clause import Clause
from contractos.models.fact import Fact
from contractos.models.triage import (
    AutomationLevel,
    ChecklistItem,
    ChecklistResult,
    ChecklistStatus,
    TriageClassification,
    TriageLevel,
    TriageResult,
)
from contractos.tools.fact_discovery import _parse_lenient_json

logger = logging.getLogger(__name__)

NDA_TRIAGE_PROMPT = """You are ContractOS NDA Triage Agent — an expert at screening NDAs.

You are evaluating a specific aspect of an NDA. Based on the extracted facts and clause text,
determine if this checklist item PASSES, FAILS, or needs REVIEW.

Respond in JSON format:
{
  "status": "pass|fail|review",
  "finding": "What was found (1-2 sentences)",
  "evidence": "Specific text from the contract supporting this finding"
}"""

# Default NDA checklist — 10 standard screening items
DEFAULT_CHECKLIST: list[ChecklistItem] = [
    ChecklistItem(
        item_id="agreement_structure",
        name="Agreement Structure",
        automation=AutomationLevel.HYBRID,
        description="Is this a mutual or unilateral NDA? Is it standalone?",
    ),
    ChecklistItem(
        item_id="definition_scope",
        name="Definition Scope",
        automation=AutomationLevel.HYBRID,
        description="Are definitions of Confidential Information appropriately scoped?",
    ),
    ChecklistItem(
        item_id="receiving_party_obligations",
        name="Receiving Party Obligations",
        automation=AutomationLevel.LLM_ONLY,
        description="Are the receiving party's obligations reasonable and standard?",
    ),
    ChecklistItem(
        item_id="standard_carveouts",
        name="Standard Carveouts",
        automation=AutomationLevel.HYBRID,
        description="Are all 5 standard carveouts present? (public knowledge, prior possession, independent development, third-party receipt, legal compulsion)",
        critical=True,
    ),
    ChecklistItem(
        item_id="permitted_disclosures",
        name="Permitted Disclosures",
        automation=AutomationLevel.LLM_ONLY,
        description="Are permitted disclosures (employees, advisors, affiliates) adequately defined?",
    ),
    ChecklistItem(
        item_id="term_duration",
        name="Term and Duration",
        automation=AutomationLevel.HYBRID,
        description="Is the term reasonable (typically 1-5 years)?",
    ),
    ChecklistItem(
        item_id="return_destruction",
        name="Return/Destruction",
        automation=AutomationLevel.LLM_ONLY,
        description="Are return/destruction obligations upon termination clearly stated?",
    ),
    ChecklistItem(
        item_id="remedies",
        name="Remedies",
        automation=AutomationLevel.LLM_ONLY,
        description="Are remedies for breach appropriate (injunctive relief, damages)?",
    ),
    ChecklistItem(
        item_id="problematic_provisions",
        name="Problematic Provisions",
        automation=AutomationLevel.HYBRID,
        description="Are there non-solicitation, non-compete, or other problematic provisions?",
        critical=True,
    ),
    ChecklistItem(
        item_id="governing_law",
        name="Governing Law",
        automation=AutomationLevel.HYBRID,
        description="Is the governing law and jurisdiction acceptable?",
    ),
]


class NDATriageAgent:
    """Screens NDAs against a 10-point checklist."""

    def __init__(self, trust_graph: TrustGraph, llm: LLMProvider) -> None:
        self._graph = trust_graph
        self._llm = llm

    async def triage(
        self,
        document_id: str,
        checklist: list[ChecklistItem] | None = None,
    ) -> TriageResult:
        """Run NDA triage screening.

        Args:
            document_id: The NDA to screen.
            checklist: Optional custom checklist. Uses default if not provided.

        Returns:
            TriageResult with classification and checklist results.

        Raises:
            ValueError: If the document is not found.
        """
        start_time = time.monotonic()

        contract = self._graph.get_contract(document_id)
        if contract is None:
            raise ValueError(f"Document not found: {document_id}")

        items = checklist or DEFAULT_CHECKLIST
        facts = self._graph.get_facts_by_document(document_id)
        clauses = self._graph.get_clauses_by_document(document_id)

        # Build context for LLM
        facts_text = "\n".join(
            f"- [{f.fact_id}] ({f.evidence.location_hint}): {f.value[:200]}"
            for f in facts[:50]
        )
        clauses_text = "\n".join(
            f"- [{c.clause_id}] {c.clause_type.value}: {c.heading}"
            for c in clauses
        )

        results: list[ChecklistResult] = []
        for item in items:
            result = await self._evaluate_item(
                item, facts, clauses, facts_text, clauses_text
            )
            results.append(result)

        # Classify
        classification = self._classify(results, items)

        # Key issues
        key_issues = [
            f"{r.name}: {r.finding}"
            for r in results
            if r.status in (ChecklistStatus.FAIL, ChecklistStatus.REVIEW)
        ]

        # Counts
        pass_count = sum(1 for r in results if r.status == ChecklistStatus.PASS)
        fail_count = sum(1 for r in results if r.status == ChecklistStatus.FAIL)
        review_count = sum(1 for r in results if r.status == ChecklistStatus.REVIEW)

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        return TriageResult(
            document_id=document_id,
            classification=classification,
            checklist_results=results,
            key_issues=key_issues,
            summary=self._build_summary(results, classification),
            triage_time_ms=elapsed_ms,
            pass_count=pass_count,
            fail_count=fail_count,
            review_count=review_count,
        )

    async def _evaluate_item(
        self,
        item: ChecklistItem,
        facts: list[Fact],
        clauses: list[Clause],
        facts_text: str,
        clauses_text: str,
    ) -> ChecklistResult:
        """Evaluate a single checklist item."""
        # Run automated checks first for HYBRID items
        auto_result = None
        if item.automation in (AutomationLevel.AUTO, AutomationLevel.HYBRID):
            auto_result = self._auto_check(item, facts, clauses)

        # For AUTO items, return the automated result
        if item.automation == AutomationLevel.AUTO and auto_result:
            return auto_result

        # For HYBRID and LLM_ONLY, use LLM
        try:
            llm_result = await self._llm_evaluate(item, facts_text, clauses_text)
            status_str = llm_result.get("status", "review")
            try:
                status = ChecklistStatus(status_str)
            except ValueError:
                status = ChecklistStatus.REVIEW

            # For HYBRID: if auto check found something specific, prefer it
            if auto_result and auto_result.status == ChecklistStatus.FAIL:
                return auto_result

            return ChecklistResult(
                item_id=item.item_id,
                name=item.name,
                status=status,
                finding=llm_result.get("finding", ""),
                evidence=llm_result.get("evidence", ""),
            )
        except Exception as e:
            logger.error("LLM evaluation failed for %s: %s", item.item_id, e)
            return auto_result or ChecklistResult(
                item_id=item.item_id,
                name=item.name,
                status=ChecklistStatus.REVIEW,
                finding=f"Evaluation error: {e}",
            )

    def _auto_check(
        self,
        item: ChecklistItem,
        facts: list[Fact],
        clauses: list[Clause],
    ) -> ChecklistResult | None:
        """Run automated pattern matching for a checklist item."""
        all_text = " ".join(f.value for f in facts).lower()
        fact_ids = [f.fact_id for f in facts]

        if item.item_id == "standard_carveouts":
            return self._check_standard_carveouts(all_text, fact_ids)
        elif item.item_id == "term_duration":
            return self._check_term_duration(all_text, fact_ids)
        elif item.item_id == "governing_law":
            return self._check_governing_law(all_text, fact_ids, clauses)
        elif item.item_id == "problematic_provisions":
            return self._check_problematic_provisions(all_text, fact_ids)
        elif item.item_id == "agreement_structure":
            return self._check_agreement_structure(all_text, fact_ids, clauses)

        return None

    def _check_standard_carveouts(self, text: str, fact_ids: list[str]) -> ChecklistResult:
        """Check for 5 standard NDA carveouts."""
        carveouts = {
            "public_knowledge": r"public(?:ly)?\s+(?:available|known|knowledge)",
            "prior_possession": r"prior\s+(?:possession|knowledge|to\s+disclosure)",
            "independent_development": r"independent(?:ly)?\s+develop",
            "third_party_receipt": r"(?:third\s+party|received\s+from)",
            "legal_compulsion": r"(?:law|court\s+order|legal(?:ly)?\s+(?:compel|requir))",
        }
        found = []
        missing = []
        for name, pattern in carveouts.items():
            if re.search(pattern, text):
                found.append(name)
            else:
                missing.append(name)

        if not missing:
            return ChecklistResult(
                item_id="standard_carveouts",
                name="Standard Carveouts",
                status=ChecklistStatus.PASS,
                finding=f"All 5 standard carveouts present: {', '.join(found)}",
                fact_ids=fact_ids[:5],
            )
        else:
            return ChecklistResult(
                item_id="standard_carveouts",
                name="Standard Carveouts",
                status=ChecklistStatus.FAIL,
                finding=f"Missing carveouts: {', '.join(missing)}",
                fact_ids=fact_ids[:5],
            )

    def _check_term_duration(self, text: str, fact_ids: list[str]) -> ChecklistResult:
        """Check for reasonable term duration."""
        duration_match = re.search(
            r"(\d+)\s*(?:year|yr|month|mo)", text
        )
        if duration_match:
            return ChecklistResult(
                item_id="term_duration",
                name="Term and Duration",
                status=ChecklistStatus.PASS,
                finding=f"Term duration found: {duration_match.group(0)}",
                fact_ids=fact_ids[:3],
            )
        return ChecklistResult(
            item_id="term_duration",
            name="Term and Duration",
            status=ChecklistStatus.REVIEW,
            finding="No explicit term duration found — manual review recommended",
        )

    def _check_governing_law(
        self, text: str, fact_ids: list[str], clauses: list[Clause]
    ) -> ChecklistResult:
        """Check for governing law clause."""
        gov_clauses = [c for c in clauses if c.clause_type.value == "governing_law"]
        if gov_clauses:
            return ChecklistResult(
                item_id="governing_law",
                name="Governing Law",
                status=ChecklistStatus.PASS,
                finding=f"Governing law clause found: {gov_clauses[0].heading}",
                fact_ids=fact_ids[:3],
            )
        # Check text for jurisdiction mentions
        if re.search(r"govern(?:ed|ing)\s+(?:by\s+)?(?:the\s+)?law", text):
            return ChecklistResult(
                item_id="governing_law",
                name="Governing Law",
                status=ChecklistStatus.PASS,
                finding="Governing law reference found in text",
                fact_ids=fact_ids[:3],
            )
        return ChecklistResult(
            item_id="governing_law",
            name="Governing Law",
            status=ChecklistStatus.REVIEW,
            finding="No governing law clause identified",
        )

    def _check_problematic_provisions(self, text: str, fact_ids: list[str]) -> ChecklistResult:
        """Check for non-solicitation, non-compete, or other problematic provisions."""
        problematic = []
        if re.search(r"non[- ]?compet", text):
            problematic.append("non-compete")
        if re.search(r"non[- ]?solicit", text):
            problematic.append("non-solicitation")
        if re.search(r"exclusiv(?:e|ity)", text):
            problematic.append("exclusivity")

        if problematic:
            return ChecklistResult(
                item_id="problematic_provisions",
                name="Problematic Provisions",
                status=ChecklistStatus.FAIL,
                finding=f"Problematic provisions detected: {', '.join(problematic)}",
                fact_ids=fact_ids[:5],
            )
        return ChecklistResult(
            item_id="problematic_provisions",
            name="Problematic Provisions",
            status=ChecklistStatus.PASS,
            finding="No non-compete, non-solicitation, or exclusivity provisions found",
        )

    def _check_agreement_structure(
        self, text: str, fact_ids: list[str], clauses: list[Clause]
    ) -> ChecklistResult:
        """Check if NDA is mutual or unilateral."""
        is_mutual = bool(re.search(r"mutual|each\s+party|both\s+parties", text))
        return ChecklistResult(
            item_id="agreement_structure",
            name="Agreement Structure",
            status=ChecklistStatus.PASS if is_mutual else ChecklistStatus.REVIEW,
            finding="Mutual NDA detected" if is_mutual else "May be unilateral — review recommended",
            fact_ids=fact_ids[:3],
        )

    async def _llm_evaluate(
        self, item: ChecklistItem, facts_text: str, clauses_text: str
    ) -> dict[str, Any]:
        """Use LLM to evaluate a checklist item."""
        prompt = f"""## Checklist Item
- ID: {item.item_id}
- Name: {item.name}
- Description: {item.description}

## Extracted Facts
{facts_text}

## Classified Clauses
{clauses_text}

Evaluate this checklist item based on the extracted facts and clauses."""

        messages = [LLMMessage(role="user", content=prompt)]
        response = await self._llm.complete(
            messages, system=NDA_TRIAGE_PROMPT, temperature=0.0, max_tokens=1024
        )
        return _parse_lenient_json(response.content)

    def _classify(
        self,
        results: list[ChecklistResult],
        items: list[ChecklistItem],
    ) -> TriageClassification:
        """Determine overall classification from checklist results."""
        item_lookup = {i.item_id: i for i in items}

        has_critical_fail = False
        has_any_fail = False

        for r in results:
            if r.status == ChecklistStatus.FAIL:
                has_any_fail = True
                item = item_lookup.get(r.item_id)
                if item and item.critical:
                    has_critical_fail = True

        if has_critical_fail:
            return TriageClassification(
                level=TriageLevel.RED,
                routing="Full legal review required — critical issues found",
                timeline="3-5 business days",
                rationale="Critical checklist items failed — requires senior counsel review",
            )
        elif has_any_fail:
            return TriageClassification(
                level=TriageLevel.YELLOW,
                routing="Counsel review recommended — non-critical issues found",
                timeline="1-2 business days",
                rationale="Some checklist items failed but no critical issues",
            )
        else:
            return TriageClassification(
                level=TriageLevel.GREEN,
                routing="Approve and route for signature",
                timeline="Same day",
                rationale="All checklist items passed — standard NDA",
            )

    def _build_summary(
        self, results: list[ChecklistResult], classification: TriageClassification
    ) -> str:
        """Build a summary of the triage results."""
        pass_count = sum(1 for r in results if r.status == ChecklistStatus.PASS)
        fail_count = sum(1 for r in results if r.status == ChecklistStatus.FAIL)
        review_count = sum(1 for r in results if r.status == ChecklistStatus.REVIEW)
        total = len(results)

        return (
            f"NDA Triage: {total} items evaluated — "
            f"{pass_count} PASS, {fail_count} FAIL, {review_count} REVIEW. "
            f"Classification: {classification.level.value.upper()}. "
            f"Routing: {classification.routing}"
        )
