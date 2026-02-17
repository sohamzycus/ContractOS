"""Entity alias detector — identifies party aliases and produces Binding records.

Supports multiple alias patterns including:
- "X, hereinafter referred to as 'Y'"
- "X (the 'Y')"
- "X, hereafter 'Y'"
- "Entity Corp, a Delaware corporation ('Alias')"
"""

from __future__ import annotations

import uuid
from datetime import datetime

from contractos.models.binding import Binding, BindingScope, BindingType
from contractos.models.fact import EntityType, Fact, FactEvidence, FactType
from contractos.tools.contract_patterns import (
    ALIAS_PATTERN,
    PARTY_ALIAS_PATTERN,
    normalize_quotes,
)


def detect_aliases(
    text: str,
    document_id: str,
    *,
    extraction_method: str = "alias_detector_v2",
) -> tuple[list[Fact], list[Binding]]:
    """Detect entity aliases in contract text.

    Normalizes smart/curly quotes before matching, then applies
    multiple alias patterns to maximize entity detection.

    Returns:
        Tuple of (alias facts, binding records).
    """
    normalized = normalize_quotes(text)
    facts: list[Fact] = []
    bindings: list[Binding] = []
    seen_aliases: set[str] = set()
    now = datetime.now()

    # Pattern 1: Standard alias pattern (hereinafter, the "X", etc.)
    for match in ALIAS_PATTERN.finditer(normalized):
        entity_name = match.group(1).strip()
        alias = match.group(2).strip()
        _add_alias(
            entity_name, alias, match, document_id, extraction_method,
            now, facts, bindings, seen_aliases,
        )

    # Pattern 2: Party alias pattern ("Corp, a <type> corporation ("Alias")")
    for match in PARTY_ALIAS_PATTERN.finditer(normalized):
        entity_name = match.group(1).strip()
        alias = match.group(2).strip()
        _add_alias(
            entity_name, alias, match, document_id, extraction_method,
            now, facts, bindings, seen_aliases,
        )

    return facts, bindings


def _add_alias(
    entity_name: str,
    alias: str,
    match,
    document_id: str,
    extraction_method: str,
    now: datetime,
    facts: list[Fact],
    bindings: list[Binding],
    seen_aliases: set[str],
) -> None:
    """Add an alias fact and binding, deduplicating by alias name."""
    if not entity_name or not alias:
        return
    if alias.lower() in seen_aliases:
        return
    seen_aliases.add(alias.lower())

    fact_id = f"f-alias-{uuid.uuid4().hex[:8]}"

    fact = Fact(
        fact_id=fact_id,
        fact_type=FactType.ENTITY,
        entity_type=EntityType.PARTY,
        value=f"{entity_name} \u2192 {alias}",
        evidence=FactEvidence(
            document_id=document_id,
            text_span=match.group(0),
            char_start=match.start(),
            char_end=match.end(),
            location_hint=f"characters {match.start()}-{match.end()}",
            structural_path="body > alias_definition",
        ),
        extraction_method=extraction_method,
        extracted_at=now,
    )
    facts.append(fact)

    binding = Binding(
        binding_id=f"b-alias-{uuid.uuid4().hex[:8]}",
        binding_type=BindingType.DEFINITION,
        term=alias,
        resolves_to=entity_name,
        source_fact_id=fact_id,
        document_id=document_id,
        scope=BindingScope.CONTRACT,
    )
    bindings.append(binding)
