"""Entity alias detector — identifies party aliases and produces Binding records."""

from __future__ import annotations

import uuid
from datetime import datetime

from contractos.models.binding import Binding, BindingScope, BindingType
from contractos.models.fact import EntityType, Fact, FactEvidence, FactType
from contractos.tools.contract_patterns import ALIAS_PATTERN


def detect_aliases(
    text: str,
    document_id: str,
    *,
    extraction_method: str = "alias_detector_v1",
) -> tuple[list[Fact], list[Binding]]:
    """Detect entity aliases in contract text.

    Looks for patterns like:
    - "X, hereinafter referred to as 'Y'"
    - "X (the 'Y')"
    - "X, hereafter 'Y'"

    Returns:
        Tuple of (alias facts, binding records).
    """
    facts: list[Fact] = []
    bindings: list[Binding] = []
    now = datetime.now()

    for match in ALIAS_PATTERN.finditer(text):
        entity_name = match.group(1).strip()
        alias = match.group(2).strip()

        if not entity_name or not alias:
            continue

        fact_id = f"f-alias-{uuid.uuid4().hex[:8]}"

        # Create a fact for the alias definition
        fact = Fact(
            fact_id=fact_id,
            fact_type=FactType.ENTITY,
            entity_type=EntityType.PARTY,
            value=f"{entity_name} → {alias}",
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

        # Create a binding: alias → entity
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

    return facts, bindings
