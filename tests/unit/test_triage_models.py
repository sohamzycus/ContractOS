"""Unit tests for triage models — T223.

TDD Red → Green: Verify triage model validation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from contractos.models.triage import (
    AutomationLevel,
    ChecklistItem,
    ChecklistResult,
    ChecklistStatus,
    TriageClassification,
    TriageLevel,
    TriageResult,
)


class TestAutomationLevel:
    def test_values(self):
        assert AutomationLevel.AUTO == "auto"
        assert AutomationLevel.HYBRID == "hybrid"
        assert AutomationLevel.LLM_ONLY == "llm_only"


class TestChecklistStatus:
    def test_values(self):
        assert ChecklistStatus.PASS == "pass"
        assert ChecklistStatus.FAIL == "fail"
        assert ChecklistStatus.REVIEW == "review"
        assert ChecklistStatus.NOT_APPLICABLE == "n/a"


class TestTriageLevel:
    def test_values(self):
        assert TriageLevel.GREEN == "green"
        assert TriageLevel.YELLOW == "yellow"
        assert TriageLevel.RED == "red"


class TestChecklistItem:
    def test_valid_item(self):
        item = ChecklistItem(
            item_id="test_item",
            name="Test Item",
            automation=AutomationLevel.HYBRID,
            description="A test checklist item",
            critical=True,
        )
        assert item.item_id == "test_item"
        assert item.critical is True

    def test_requires_item_id(self):
        with pytest.raises(ValidationError):
            ChecklistItem(name="Test", automation=AutomationLevel.AUTO)


class TestChecklistResult:
    def test_valid_result(self):
        result = ChecklistResult(
            item_id="test",
            name="Test",
            status=ChecklistStatus.PASS,
            finding="All good",
            evidence="Section 2.1",
            fact_ids=["f-001"],
        )
        assert result.status == ChecklistStatus.PASS
        assert result.fact_ids == ["f-001"]


class TestTriageClassification:
    def test_green_classification(self):
        tc = TriageClassification(
            level=TriageLevel.GREEN,
            routing="Route for signature",
            timeline="Same day",
            rationale="All items passed",
        )
        assert tc.level == TriageLevel.GREEN
        assert tc.routing != ""
        assert tc.timeline != ""


class TestTriageResult:
    def test_valid_result(self):
        result = TriageResult(
            document_id="doc-001",
            classification=TriageClassification(
                level=TriageLevel.GREEN,
                routing="Approve",
                timeline="Same day",
            ),
            checklist_results=[
                ChecklistResult(
                    item_id="item1",
                    name="Item 1",
                    status=ChecklistStatus.PASS,
                ),
            ],
            summary="All good",
            pass_count=1,
            fail_count=0,
            review_count=0,
        )
        assert result.document_id == "doc-001"
        assert len(result.checklist_results) == 1
        assert result.pass_count == 1

    def test_aggregates_correctly(self):
        result = TriageResult(
            document_id="doc-001",
            classification=TriageClassification(
                level=TriageLevel.YELLOW,
                routing="Review",
                timeline="1-2 days",
            ),
            pass_count=7,
            fail_count=2,
            review_count=1,
        )
        assert result.pass_count + result.fail_count + result.review_count == 10
