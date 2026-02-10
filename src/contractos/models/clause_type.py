"""Clause type registry models — what facts each clause type expects."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from contractos.models.clause import ClauseTypeEnum
from contractos.models.fact import EntityType


class SlotStatus(StrEnum):
    """Status of a mandatory/optional fact slot within a clause."""

    FILLED = "filled"
    MISSING = "missing"
    PARTIAL = "partial"


class MandatoryFactSpec(BaseModel):
    """Specification of a fact that a clause type is expected to contain."""

    fact_name: str = Field(min_length=1)
    fact_description: str = Field(min_length=1)
    entity_type: EntityType
    required: bool = True


class ClauseTypeSpec(BaseModel):
    """Registry entry defining what a clause type should contain."""

    type_id: ClauseTypeEnum
    display_name: str = Field(min_length=1)
    mandatory_facts: list[MandatoryFactSpec] = Field(default_factory=list)
    optional_facts: list[MandatoryFactSpec] = Field(default_factory=list)
    common_cross_refs: list[ClauseTypeEnum] = Field(default_factory=list)


class ClauseFactSlot(BaseModel):
    """Tracks whether a clause has its expected mandatory/optional facts."""

    clause_id: str = Field(min_length=1)
    fact_spec_name: str = Field(min_length=1)
    status: SlotStatus
    filled_by_fact_id: str | None = None
    required: bool = True

    def model_post_init(self, __context: object) -> None:
        if self.status == SlotStatus.FILLED and self.filled_by_fact_id is None:
            msg = "filled_by_fact_id is required when status is FILLED"
            raise ValueError(msg)
