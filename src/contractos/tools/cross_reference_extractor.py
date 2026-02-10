"""Cross-reference extractor — identifies and resolves section references within a document."""

from __future__ import annotations

import uuid

from contractos.models.clause import (
    Clause,
    CrossReference,
    ReferenceEffect,
    ReferenceType,
)
from contractos.tools.contract_patterns import SECTION_REF_PATTERN

# Keywords that hint at the effect of a reference
_EFFECT_KEYWORDS: list[tuple[list[str], ReferenceEffect]] = [
    (["subject to", "conditional", "provided that", "unless"], ReferenceEffect.CONDITIONS),
    (["notwithstanding", "override", "supersede", "prevail"], ReferenceEffect.OVERRIDES),
    (["in accordance with", "pursuant to", "as specified in", "as set forth"], ReferenceEffect.INCORPORATES),
    (["except as", "other than", "excluding"], ReferenceEffect.LIMITS),
    (["as defined in", "defined in", "meaning given in"], ReferenceEffect.DEFINES),
]


def _classify_effect(context: str) -> ReferenceEffect:
    """Classify the effect of a cross-reference based on surrounding context."""
    context_lower = context.lower()
    for keywords, effect in _EFFECT_KEYWORDS:
        for kw in keywords:
            if kw in context_lower:
                return effect
    return ReferenceEffect.REFERENCES  # default


def _classify_reference_type(ref_text: str) -> ReferenceType:
    """Classify the type of reference based on the reference text."""
    ref_lower = ref_text.lower()
    if "appendix" in ref_lower:
        return ReferenceType.APPENDIX_REF
    if "schedule" in ref_lower:
        return ReferenceType.SCHEDULE_REF
    if "exhibit" in ref_lower:
        return ReferenceType.EXHIBIT_REF
    if "annex" in ref_lower:
        return ReferenceType.ANNEX_REF
    if "clause" in ref_lower or "article" in ref_lower:
        return ReferenceType.CLAUSE_REF
    return ReferenceType.SECTION_REF


def extract_cross_references(
    text: str,
    source_clause_id: str,
    clauses: list[Clause] | None = None,
    *,
    context_window: int = 80,
) -> list[CrossReference]:
    """Extract cross-references from clause text.

    Args:
        text: The text to search for references.
        source_clause_id: ID of the clause containing the references.
        clauses: Optional list of clauses for resolution.
        context_window: Characters of context around each reference.

    Returns:
        List of CrossReference objects.
    """
    refs: list[CrossReference] = []
    clause_lookup = _build_clause_lookup(clauses or [])

    for match in SECTION_REF_PATTERN.finditer(text):
        ref_text = match.group(0)
        ref_number = match.group(1)

        # Get surrounding context
        ctx_start = max(0, match.start() - context_window)
        ctx_end = min(len(text), match.end() + context_window)
        context = text[ctx_start:ctx_end]

        # Try to resolve to a known clause
        target_clause_id = clause_lookup.get(ref_number)
        resolved = target_clause_id is not None

        xref = CrossReference(
            reference_id=f"xr-{uuid.uuid4().hex[:8]}",
            source_clause_id=source_clause_id,
            target_reference=ref_text,
            target_clause_id=target_clause_id,
            reference_type=_classify_reference_type(ref_text),
            effect=_classify_effect(context),
            context=context.strip(),
            resolved=resolved,
            source_fact_id="",  # Will be linked after fact extraction
        )
        refs.append(xref)

    return refs


def _build_clause_lookup(clauses: list[Clause]) -> dict[str, str]:
    """Build a mapping from section_number → clause_id for resolution."""
    lookup: dict[str, str] = {}
    for clause in clauses:
        if clause.section_number:
            lookup[clause.section_number] = clause.clause_id
    return lookup
