"""Workspace and ReasoningSession models — persistent user context."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SessionStatus(StrEnum):
    """Status of a reasoning session."""

    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class Workspace(BaseModel):
    """Persistent user context for ContractOS.

    Like Cursor remembers your project context, ContractOS remembers
    your contract workspace.
    """

    workspace_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    indexed_documents: list[str] = Field(default_factory=list)
    created_at: datetime
    last_accessed_at: datetime
    settings: dict[str, Any] = Field(default_factory=dict)


class ReasoningSession(BaseModel):
    """A single query lifecycle — from question to provenance-backed answer."""

    session_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    query_text: str = Field(min_length=1)
    query_scope: str = Field(min_length=1)
    target_document_ids: list[str] = Field(default_factory=list)
    answer: str | None = None
    answer_type: str | None = None
    confidence: float | None = None
    status: SessionStatus = SessionStatus.ACTIVE
    started_at: datetime
    completed_at: datetime | None = None
    generation_time_ms: int | None = None
