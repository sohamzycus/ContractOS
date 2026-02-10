"""Mandatory fact extractor — checks clause types for required facts and fills slots."""

from __future__ import annotations

from contractos.models.clause import Clause, ClauseTypeEnum
from contractos.models.clause_type import ClauseFactSlot, SlotStatus
from contractos.models.fact import Fact
from contractos.tools.contract_patterns import (
    DURATION_PATTERN,
    MONETARY_PATTERN,
    PERCENTAGE_PATTERN,
)

# ── Clause Type → Required/Optional Facts Registry ────────────────

_CLAUSE_FACT_REGISTRY: dict[ClauseTypeEnum, list[tuple[str, bool]]] = {
    # (fact_spec_name, required)
    ClauseTypeEnum.TERMINATION: [
        ("notice_period", True),
        ("termination_reasons", True),
        ("cure_period", False),
        ("survival_clauses", False),
    ],
    ClauseTypeEnum.PAYMENT: [
        ("payment_amount", True),
        ("payment_schedule", True),
        ("currency", False),
        ("late_payment_penalty", False),
    ],
    ClauseTypeEnum.CONFIDENTIALITY: [
        ("confidentiality_duration", True),
        ("confidential_information_definition", True),
        ("exclusions", False),
    ],
    ClauseTypeEnum.LIABILITY: [
        ("liability_cap", True),
        ("exclusion_types", False),
    ],
    ClauseTypeEnum.WARRANTY: [
        ("warranty_period", False),
        ("warranty_scope", True),
    ],
    ClauseTypeEnum.INDEMNIFICATION: [
        ("indemnification_scope", True),
        ("indemnification_cap", False),
    ],
    ClauseTypeEnum.NON_COMPETE: [
        ("non_compete_duration", True),
        ("geographic_scope", False),
    ],
    ClauseTypeEnum.NOTICE: [
        ("notice_method", True),
        ("notice_address", False),
    ],
}

# Simple heuristic matchers for fact spec names
_FACT_MATCHERS: dict[str, list[str]] = {
    "notice_period": ["notice", "days", "months", "written notice"],
    "termination_reasons": ["breach", "insolvency", "mutual agreement", "cause", "convenience"],
    "cure_period": ["cure", "remedy", "rectify"],
    "payment_amount": ["$", "€", "£", "usd", "amount", "fee", "price"],
    "payment_schedule": ["net", "due", "invoice", "monthly", "quarterly", "annually"],
    "currency": ["usd", "eur", "gbp", "inr", "dollar", "euro", "pound"],
    "late_payment_penalty": ["late", "penalty", "interest", "overdue"],
    "confidentiality_duration": ["months", "years", "period", "term"],
    "confidential_information_definition": ["confidential information", "trade secret", "proprietary"],
    "exclusions": ["exclude", "exception", "not include"],
    "liability_cap": ["cap", "limit", "maximum", "aggregate"],
    "exclusion_types": ["consequential", "indirect", "incidental", "punitive"],
    "warranty_period": ["months", "years", "warranty period"],
    "warranty_scope": ["warrant", "represent", "guarantee"],
    "indemnification_scope": ["indemnif", "hold harmless", "defend"],
    "indemnification_cap": ["cap", "limit", "maximum"],
    "non_compete_duration": ["months", "years", "period"],
    "geographic_scope": ["territory", "region", "geographic", "worldwide"],
    "notice_method": ["email", "mail", "written", "registered"],
    "notice_address": ["address", "attention", "sent to"],
    "survival_clauses": ["survive", "survival"],
}


def extract_mandatory_facts(
    clause: Clause,
    clause_text: str,
    existing_facts: list[Fact] | None = None,
) -> list[ClauseFactSlot]:
    """Check a clause for mandatory and optional facts, returning slot statuses.

    Args:
        clause: The clause to check.
        clause_text: Full text content of the clause.
        existing_facts: Facts already extracted for this clause.

    Returns:
        List of ClauseFactSlot records indicating filled/missing status.
    """
    registry_entry = _CLAUSE_FACT_REGISTRY.get(clause.clause_type, [])
    if not registry_entry:
        return []

    slots: list[ClauseFactSlot] = []
    text_lower = clause_text.lower()

    for fact_spec_name, required in registry_entry:
        # Check if any keyword matches in the clause text
        keywords = _FACT_MATCHERS.get(fact_spec_name, [])
        found = any(kw.lower() in text_lower for kw in keywords)

        # Also check for pattern matches (durations, monetary, etc.)
        if not found and fact_spec_name in ("notice_period", "cure_period", "confidentiality_duration",
                                              "warranty_period", "non_compete_duration"):
            found = bool(DURATION_PATTERN.search(clause_text))
        if not found and fact_spec_name in ("payment_amount", "liability_cap", "indemnification_cap"):
            found = bool(MONETARY_PATTERN.search(clause_text))

        # Try to find a matching existing fact
        filled_by = None
        if found and existing_facts:
            for fact in existing_facts:
                fact_value_lower = fact.value.lower()
                if any(kw.lower() in fact_value_lower for kw in keywords):
                    filled_by = fact.fact_id
                    break

        if found and filled_by:
            status = SlotStatus.FILLED
        elif found:
            status = SlotStatus.PARTIAL  # text evidence found but no linked fact
        else:
            status = SlotStatus.MISSING

        slots.append(ClauseFactSlot(
            clause_id=clause.clause_id,
            fact_spec_name=fact_spec_name,
            status=status,
            filled_by_fact_id=filled_by,
            required=required,
        ))

    return slots
