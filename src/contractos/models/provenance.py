"""Provenance chain models — evidence backing every ContractOS answer."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ProvenanceNode(BaseModel):
    """A single node in the provenance chain."""

    node_type: Literal["fact", "binding", "inference", "external", "reasoning"]
    reference_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    document_location: str | None = None


class ProvenanceChain(BaseModel):
    """Full evidence chain for an answer.

    Every answer ContractOS produces must be backed by a provenance chain.
    An empty chain is invalid — at minimum it must contain a reasoning node.
    """

    nodes: list[ProvenanceNode] = Field(min_length=1)
    reasoning_summary: str = Field(min_length=1)
