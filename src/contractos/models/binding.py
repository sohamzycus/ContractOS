"""Binding model — explicitly stated semantic mappings in contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class BindingType(StrEnum):
    """Types of bindings found in contracts."""

    DEFINITION = "definition"
    ASSIGNMENT = "assignment"
    INCORPORATION = "incorporation"
    DELEGATION = "delegation"
    SCOPE_LIMITATION = "scope_limitation"


class BindingScope(StrEnum):
    """Scope of a binding's applicability."""

    CONTRACT = "contract"
    CONTRACT_FAMILY = "contract_family"
    REPOSITORY = "repository"


class Binding(BaseModel):
    """An explicitly stated semantic mapping found in a contract.

    Bindings are deterministic (not probabilistic) but require resolution
    logic to apply throughout the document. They sit between Facts and
    Inferences in the truth model.
    """

    binding_id: str = Field(min_length=1)
    binding_type: BindingType
    term: str = Field(min_length=1)
    resolves_to: str = Field(min_length=1)
    source_fact_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    scope: BindingScope = BindingScope.CONTRACT
    is_overridden_by: str | None = None
