"""Binding resolver — resolves definitions, aliases, and entity references into Bindings."""

from __future__ import annotations

import uuid
from datetime import datetime

from contractos.models.binding import Binding, BindingScope, BindingType
from contractos.models.fact import Fact, FactType
from contractos.tools.contract_patterns import (
    DEFINITION_PATTERN,
    PARENTHETICAL_DEF_PATTERN,
    normalize_quotes,
)


def resolve_bindings(
    facts: list[Fact],
    existing_bindings: list[Binding],
    full_text: str,
    document_id: str,
) -> list[Binding]:
    """Resolve all bindings from extracted facts and document text.

    Pipeline:
    1. Extract definition-based bindings from text patterns (including parenthetical)
    2. Merge with existing alias-based bindings (from alias_detector)
    3. Deduplicate by term (case-insensitive)

    Returns:
        Complete list of bindings for the document.
    """
    new_bindings: list[Binding] = []

    # Step 1: Extract definitions from full text
    definition_bindings = _extract_definition_bindings(full_text, facts, document_id)
    new_bindings.extend(definition_bindings)

    # Step 2: Merge — existing alias bindings take precedence
    existing_terms = {b.term.lower() for b in existing_bindings}
    deduped = list(existing_bindings)
    for b in new_bindings:
        if b.term.lower() not in existing_terms:
            deduped.append(b)
            existing_terms.add(b.term.lower())

    return deduped


def _extract_definition_bindings(
    text: str,
    facts: list[Fact],
    document_id: str,
) -> list[Binding]:
    """Extract bindings from definition patterns in text.

    Uses both the standard definition pattern and the parenthetical
    definition pattern, with smart-quote normalization.
    """
    normalized = normalize_quotes(text)
    bindings: list[Binding] = []
    seen_terms: set[str] = set()

    # Standard definitions: "Term" shall mean ...
    for match in DEFINITION_PATTERN.finditer(normalized):
        term = match.group(1).strip()
        definition = match.group(2).strip()

        if not term or not definition:
            continue
        if term.lower() in seen_terms:
            continue

        source_fact_id = _find_nearest_fact(facts, match.start(), match.end())

        bindings.append(Binding(
            binding_id=f"b-def-{uuid.uuid4().hex[:8]}",
            binding_type=BindingType.DEFINITION,
            term=term,
            resolves_to=definition,
            source_fact_id=source_fact_id,
            document_id=document_id,
            scope=BindingScope.CONTRACT,
        ))
        seen_terms.add(term.lower())

    # Parenthetical definitions: (the "Agreement") or ("Service Provider")
    for match in PARENTHETICAL_DEF_PATTERN.finditer(normalized):
        term = match.group(1).strip()
        if not term or term.lower() in seen_terms:
            continue

        # Get surrounding context as the definition
        context_start = max(0, match.start() - 120)
        context = normalized[context_start:match.start()].strip()
        if len(context) > 100:
            context = context[-100:]

        source_fact_id = _find_nearest_fact(facts, match.start(), match.end())

        bindings.append(Binding(
            binding_id=f"b-def-{uuid.uuid4().hex[:8]}",
            binding_type=BindingType.DEFINITION,
            term=term,
            resolves_to=context if context else "(parenthetical definition)",
            source_fact_id=source_fact_id,
            document_id=document_id,
            scope=BindingScope.CONTRACT,
        ))
        seen_terms.add(term.lower())

        # Handle alternative term: (the "X" or "Y")
        if match.group(2):
            alt_term = match.group(2).strip()
            if alt_term and alt_term.lower() not in seen_terms:
                bindings.append(Binding(
                    binding_id=f"b-def-{uuid.uuid4().hex[:8]}",
                    binding_type=BindingType.DEFINITION,
                    term=alt_term,
                    resolves_to=context if context else "(parenthetical definition)",
                    source_fact_id=source_fact_id,
                    document_id=document_id,
                    scope=BindingScope.CONTRACT,
                ))
                seen_terms.add(alt_term.lower())

    return bindings


def _find_nearest_fact(facts: list[Fact], char_start: int, char_end: int) -> str:
    """Find the fact whose evidence span is closest to the given range."""
    best_fact_id = "unknown"
    best_distance = float("inf")

    for fact in facts:
        ev = fact.evidence
        # Check overlap
        if ev.char_start <= char_end and ev.char_end >= char_start:
            return fact.fact_id
        # Check distance
        distance = min(abs(ev.char_start - char_end), abs(ev.char_end - char_start))
        if distance < best_distance:
            best_distance = distance
            best_fact_id = fact.fact_id

    return best_fact_id


def resolve_term(
    term: str,
    bindings: list[Binding],
    *,
    max_depth: int = 5,
) -> str:
    """Resolve a term through the binding chain.

    Follows binding chains (e.g., "Buyer" → "Alpha Corp" → "Alpha Corporation Inc")
    up to max_depth to prevent infinite loops.

    Returns:
        The final resolved value, or the original term if no binding found.
    """
    current = term
    visited: set[str] = set()

    for _ in range(max_depth):
        if current.lower() in visited:
            break  # cycle detected
        visited.add(current.lower())

        binding = _find_binding(current, bindings)
        if binding is None:
            break
        current = binding.resolves_to

    return current


def _find_binding(term: str, bindings: list[Binding]) -> Binding | None:
    """Find a binding by term (case-insensitive)."""
    term_lower = term.lower()
    for b in bindings:
        if b.term.lower() == term_lower:
            return b
    return None
