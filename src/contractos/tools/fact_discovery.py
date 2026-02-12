"""LLM-powered hidden fact discovery — finds implicit obligations, risks, and unstated assumptions.

Unlike the deterministic pattern-based extraction (contract_patterns.py), this module
uses the LLM to reason about the contract text and discover facts that are:

1. Implicit obligations — duties implied but not explicitly stated
2. Hidden risks — liability exposure, ambiguous terms, missing protections
3. Unstated assumptions — conditions the contract assumes but doesn't declare
4. Cross-clause implications — obligations that emerge from combining clauses
5. Missing standard protections — common contract provisions that are absent

The discovery pipeline:
1. Gather all deterministically extracted facts and clauses
2. Build a discovery prompt with the contract text + existing facts
3. Ask the LLM to identify hidden/implicit facts beyond what patterns found
4. Parse and return structured discovered facts
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from contractos.llm.provider import LLMMessage, LLMProvider

logger = logging.getLogger(__name__)

DISCOVERY_SYSTEM_PROMPT = """You are ContractOS Discovery Engine — an expert legal analyst that finds HIDDEN facts
in contracts that go beyond simple pattern matching.

You have already been given the facts extracted by deterministic pattern matching (dates, amounts,
definitions, section references, etc.). Your job is to discover what the patterns MISSED:

1. **Implicit Obligations** — duties that are implied but not explicitly stated as "shall" or "must"
2. **Hidden Risks** — liability exposure, ambiguous terms, one-sided provisions, missing caps
3. **Unstated Assumptions** — conditions the contract assumes but doesn't declare
4. **Cross-Clause Implications** — obligations that emerge from combining multiple clauses
5. **Missing Standard Protections** — common contract provisions that are absent (e.g., force majeure, IP ownership, data protection)
6. **Ambiguous Terms** — phrases that could be interpreted multiple ways
7. **Implied Renewals or Escalations** — automatic terms that may not be obvious

For each discovered fact, provide:
- type: category from above (e.g., "implicit_obligation", "hidden_risk", "unstated_assumption", etc.)
- claim: what the hidden fact is
- evidence: the specific contract text that supports this discovery
- risk_level: "high", "medium", or "low"
- explanation: why this matters and how you discovered it

Respond in JSON format:
{
  "discovered_facts": [
    {
      "type": "implicit_obligation",
      "claim": "The buyer is implicitly required to...",
      "evidence": "Section 3.2 states that...",
      "risk_level": "medium",
      "explanation": "While not explicitly stated as an obligation..."
    }
  ],
  "summary": "Brief summary of what was discovered",
  "categories_found": "comma-separated list of categories found"
}"""


class DiscoveredFact:
    """A fact discovered by LLM analysis beyond pattern extraction."""

    def __init__(
        self,
        fact_type: str,
        claim: str,
        evidence: str = "",
        risk_level: str = "medium",
        explanation: str = "",
    ) -> None:
        self.type = fact_type
        self.claim = claim
        self.evidence = evidence
        self.risk_level = risk_level
        self.explanation = explanation

    def to_dict(self) -> dict[str, str]:
        return {
            "type": self.type,
            "claim": self.claim,
            "evidence": self.evidence,
            "risk_level": self.risk_level,
            "explanation": self.explanation,
        }


class DiscoveryResult:
    """Result of LLM-powered fact discovery."""

    def __init__(self) -> None:
        self.discovered_facts: list[DiscoveredFact] = []
        self.summary: str = ""
        self.categories_found: str = ""
        self.discovery_time_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "discovered_facts": [f.to_dict() for f in self.discovered_facts],
            "summary": self.summary,
            "categories_found": self.categories_found,
            "discovery_time_ms": self.discovery_time_ms,
            "count": len(self.discovered_facts),
        }


def _parse_lenient_json(text: str) -> dict[str, Any]:
    """Parse JSON from LLM response with lenient handling.

    Handles common LLM JSON issues:
    - Markdown code fences (```json ... ```)
    - Trailing commas
    - Single quotes instead of double quotes
    - Extra text before/after JSON
    """
    text = text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json) and last line (```)
        if len(lines) > 2:
            text = "\n".join(lines[1:-1]).strip()
        elif len(lines) == 2:
            text = lines[1].rstrip("`").strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in the text
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        json_text = text[brace_start : brace_end + 1]
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

        # Fix trailing commas: ,} or ,]
        cleaned = re.sub(r",\s*([}\]])", r"\1", json_text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    # Handle truncated JSON (response cut off by max_tokens)
    # Try to salvage partial discovered_facts array
    if brace_start >= 0:
        partial = text[brace_start:]
        # Find the discovered_facts array
        arr_match = re.search(r'"discovered_facts"\s*:\s*\[', partial)
        if arr_match:
            arr_start = arr_match.end()
            # Find complete objects within the array
            facts = []
            depth = 0
            obj_start = None
            for i in range(arr_start, len(partial)):
                ch = partial[i]
                if ch == '{':
                    if depth == 0:
                        obj_start = i
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0 and obj_start is not None:
                        obj_text = partial[obj_start : i + 1]
                        try:
                            obj = json.loads(obj_text)
                            facts.append(obj)
                        except json.JSONDecodeError:
                            # Try fixing trailing commas
                            obj_cleaned = re.sub(r",\s*([}\]])", r"\1", obj_text)
                            try:
                                obj = json.loads(obj_cleaned)
                                facts.append(obj)
                            except json.JSONDecodeError:
                                pass
                        obj_start = None
                elif ch == ']' and depth == 0:
                    break

            if facts:
                logger.info("Salvaged %d discovered facts from truncated JSON", len(facts))
                # Try to extract summary and categories
                summary_match = re.search(r'"summary"\s*:\s*"([^"]*)"', partial)
                cats_match = re.search(r'"categories_found"\s*:\s*"([^"]*)"', partial)
                return {
                    "discovered_facts": facts,
                    "summary": summary_match.group(1) if summary_match else f"Discovered {len(facts)} hidden facts",
                    "categories_found": cats_match.group(1) if cats_match else "",
                }

    # Last resort: return empty structure
    logger.warning("Could not parse LLM discovery response as JSON: %s...", text[:200])
    return {"discovered_facts": [], "summary": "Could not parse LLM response", "categories_found": ""}


async def discover_hidden_facts(
    contract_text: str,
    existing_facts_summary: str,
    clauses_summary: str,
    bindings_summary: str,
    llm: LLMProvider,
) -> DiscoveryResult:
    """Run LLM-powered discovery to find hidden facts beyond pattern extraction.

    Args:
        contract_text: Full text of the contract (truncated to ~8000 chars for token limits)
        existing_facts_summary: Summary of already-extracted facts
        clauses_summary: Summary of classified clauses
        bindings_summary: Summary of resolved bindings
        llm: LLM provider instance

    Returns:
        DiscoveryResult with discovered facts
    """
    start_time = time.monotonic()
    result = DiscoveryResult()

    # Truncate contract text to avoid token overflow
    max_text = 8000
    text = contract_text[:max_text]
    if len(contract_text) > max_text:
        text += f"\n\n[... truncated, {len(contract_text) - max_text} more characters ...]"

    # Build discovery prompt
    prompt = f"""## Contract Text
{text}

## Already Extracted Facts (by pattern matching)
{existing_facts_summary}

## Classified Clauses
{clauses_summary}

## Resolved Bindings
{bindings_summary}

---

Now analyze this contract deeply. Find hidden facts, implicit obligations, risks, and
unstated assumptions that the pattern-based extraction MISSED. Focus on what a procurement
professional or legal reviewer would want to know but might not see on a first read.

IMPORTANT: Return at most 8 discovered facts. Keep each claim under 100 words and each
evidence field under 80 words. Be concise but precise.
"""

    messages = [LLMMessage(role="user", content=prompt)]

    try:
        # Use complete (not complete_json) for more robust parsing
        # LLM responses can have trailing commas, unescaped chars, etc.
        raw_response = await llm.complete(
            messages, system=DISCOVERY_SYSTEM_PROMPT, temperature=0.1, max_tokens=8192
        )
        llm_response = _parse_lenient_json(raw_response.content)

        discovered = llm_response.get("discovered_facts", [])
        for d in discovered:
            if not isinstance(d, dict):
                continue
            fact = DiscoveredFact(
                fact_type=d.get("type", "hidden_fact"),
                claim=d.get("claim", ""),
                evidence=d.get("evidence", ""),
                risk_level=d.get("risk_level", "medium"),
                explanation=d.get("explanation", ""),
            )
            if fact.claim:  # Only add non-empty claims
                result.discovered_facts.append(fact)

        result.summary = llm_response.get("summary", f"Discovered {len(result.discovered_facts)} hidden facts")
        result.categories_found = llm_response.get("categories_found", "")

    except Exception as e:
        logger.error("Discovery failed: %s", e)
        result.summary = f"Discovery encountered an error: {e}"

    result.discovery_time_ms = int((time.monotonic() - start_time) * 1000)
    return result
