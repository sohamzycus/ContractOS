"""Triage models — NDA screening checklist and classification.

Part of the Truth Model:
- ChecklistResult status is an Inference (derived from extraction + checklist criteria)
- TriageClassification is an Opinion (aggregate judgment based on checklist)
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AutomationLevel(StrEnum):
    """How a checklist item is evaluated."""

    AUTO = "auto"          # Fully automated (pattern matching)
    HYBRID = "hybrid"      # Automated + LLM verification
    LLM_ONLY = "llm_only"  # Requires LLM judgment


class ChecklistStatus(StrEnum):
    """Status of a checklist item evaluation."""

    PASS = "pass"
    FAIL = "fail"
    REVIEW = "review"
    NOT_APPLICABLE = "n/a"


class TriageLevel(StrEnum):
    """Overall triage classification level."""

    GREEN = "green"    # Standard — route for signature
    YELLOW = "yellow"  # Counsel review needed
    RED = "red"        # Significant issues — full review


class ChecklistItem(BaseModel):
    """A single item in the NDA triage checklist."""

    item_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    automation: AutomationLevel
    description: str = ""
    critical: bool = False


class ChecklistResult(BaseModel):
    """Result of evaluating a single checklist item."""

    item_id: str
    name: str
    status: ChecklistStatus
    finding: str = ""
    evidence: str = ""
    fact_ids: list[str] = Field(default_factory=list)


class TriageClassification(BaseModel):
    """Overall NDA triage classification."""

    level: TriageLevel
    routing: str = ""
    timeline: str = ""
    rationale: str = ""


class TriageResult(BaseModel):
    """Complete NDA triage result."""

    document_id: str = Field(min_length=1)
    classification: TriageClassification
    checklist_results: list[ChecklistResult] = Field(default_factory=list)
    key_issues: list[str] = Field(default_factory=list)
    summary: str = ""
    triage_time_ms: int = 0
    pass_count: int = 0
    fail_count: int = 0
    review_count: int = 0
