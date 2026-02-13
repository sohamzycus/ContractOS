"""Unit tests for _parse_lenient_json and _salvage_array_objects.

Covers the generic truncated-JSON salvage logic added in Phase 12:
- Obligations arrays truncated by max_tokens
- Risk memo arrays truncated by max_tokens
- Clean JSON parsing (baseline)
- Markdown code fences
- Trailing commas
"""

from __future__ import annotations

import json

import pytest

from contractos.tools.fact_discovery import _parse_lenient_json, _salvage_array_objects


class TestParseLenientJsonBaseline:
    """Baseline: valid JSON should parse without issues."""

    def test_valid_json(self):
        text = json.dumps({"key": "value", "count": 42})
        result = _parse_lenient_json(text)
        assert result["key"] == "value"
        assert result["count"] == 42

    def test_valid_json_with_arrays(self):
        data = {"obligations": [{"party": "A"}, {"party": "B"}], "summary": "Two obligations"}
        result = _parse_lenient_json(json.dumps(data))
        assert len(result["obligations"]) == 2

    def test_markdown_fenced_json(self):
        text = '```json\n{"key": "value"}\n```'
        result = _parse_lenient_json(text)
        assert result["key"] == "value"

    def test_json_with_surrounding_text(self):
        text = 'Here is the result:\n{"answer": "yes"}\nThat\'s all.'
        result = _parse_lenient_json(text)
        assert result["answer"] == "yes"

    def test_trailing_comma_in_object(self):
        text = '{"a": 1, "b": 2,}'
        result = _parse_lenient_json(text)
        assert result["a"] == 1
        assert result["b"] == 2

    def test_trailing_comma_in_array(self):
        text = '{"items": [1, 2, 3,]}'
        result = _parse_lenient_json(text)
        assert result["items"] == [1, 2, 3]


class TestSalvageArrayObjects:
    """Tests for the _salvage_array_objects helper."""

    def test_complete_array(self):
        text = '[{"a": 1}, {"b": 2}]'
        items = _salvage_array_objects(text, 1)  # past the opening [
        assert len(items) == 2
        assert items[0] == {"a": 1}
        assert items[1] == {"b": 2}

    def test_truncated_array_salvages_complete_objects(self):
        text = '[{"a": 1}, {"b": 2}, {"c": 3'  # 3rd object incomplete
        items = _salvage_array_objects(text, 1)
        assert len(items) == 2
        assert items[0] == {"a": 1}
        assert items[1] == {"b": 2}

    def test_empty_array(self):
        text = '[]'
        items = _salvage_array_objects(text, 1)
        assert len(items) == 0

    def test_deeply_nested_objects(self):
        text = '[{"outer": {"inner": "val"}}, {"x": 1}]'
        items = _salvage_array_objects(text, 1)
        assert len(items) == 2
        assert items[0]["outer"]["inner"] == "val"

    def test_objects_with_string_containing_braces(self):
        text = '[{"text": "use { and } in strings"}, {"ok": true}]'
        items = _salvage_array_objects(text, 1)
        assert len(items) == 2
        assert "{" in items[0]["text"]

    def test_objects_with_escaped_quotes(self):
        text = r'[{"text": "say \"hello\""}, {"n": 1}]'
        items = _salvage_array_objects(text, 1)
        assert len(items) == 2

    def test_truncated_mid_string(self):
        """Truncated in the middle of a string value — should salvage prior objects."""
        text = '[{"a": 1}, {"b": "this is a long str'
        items = _salvage_array_objects(text, 1)
        assert len(items) == 1
        assert items[0] == {"a": 1}


class TestParseLenientJsonObligations:
    """Test truncated JSON with obligations arrays."""

    def test_truncated_obligations_are_salvaged(self):
        """Simulate LLM response cut off mid-obligations array."""
        truncated = (
            '{"summary": "Contract has many obligations", '
            '"total_affirmative": 5, "total_negative": 2, "total_conditional": 1, '
            '"obligations": ['
            '{"party": "Client", "type": "affirmative", "description": "Pay fees"},'
            '{"party": "Vendor", "type": "negative", "description": "No compete"},'
            '{"party": "Client", "type": "conditional", "description": "If termin'
        )
        result = _parse_lenient_json(truncated)
        assert len(result["obligations"]) == 2
        assert result["obligations"][0]["party"] == "Client"
        assert result["obligations"][1]["type"] == "negative"
        # Scalar fields before the array should be extracted
        assert result.get("summary") == "Contract has many obligations"
        assert result.get("total_affirmative") == 5

    def test_complete_obligations_parse_normally(self):
        """Valid obligations JSON should parse without salvage logic."""
        data = {
            "summary": "Found 3 obligations",
            "total_affirmative": 2,
            "total_negative": 1,
            "total_conditional": 0,
            "obligations": [
                {"party": "A", "type": "affirmative", "description": "Do X"},
                {"party": "A", "type": "affirmative", "description": "Do Y"},
                {"party": "B", "type": "negative", "description": "Don't Z"},
            ],
        }
        result = _parse_lenient_json(json.dumps(data))
        assert len(result["obligations"]) == 3
        assert result["total_affirmative"] == 2


class TestParseLenientJsonRiskMemo:
    """Test truncated JSON with risk memo arrays."""

    def test_truncated_key_risks_are_salvaged(self):
        """Simulate risk memo response truncated in key_risks array."""
        truncated = (
            '{"executive_summary": "High risk contract", '
            '"overall_risk_rating": "high", '
            '"missing_protections": ["No force majeure"], '
            '"escalation_items": ["IP ownership unclear"], '
            '"recommendations": [{"priority": "high", "action": "Add FM clause", "owner": "Legal"}], '
            '"key_risks": ['
            '{"risk": "Unlimited liability", "severity": 5, "likelihood": 3, "category": "financial", "mitigation": "Add cap"},'
            '{"risk": "No IP protection", "severity": 4, "likelihood": 4, "category": "ip", "mitigation": "Add IP cl'
        )
        result = _parse_lenient_json(truncated)
        assert "key_risks" in result
        assert len(result["key_risks"]) == 1
        assert result["key_risks"][0]["risk"] == "Unlimited liability"
        assert result.get("executive_summary") == "High risk contract"
        assert result.get("overall_risk_rating") == "high"

    def test_complete_risk_memo_parses_normally(self):
        """Valid risk memo JSON should parse correctly."""
        data = {
            "executive_summary": "Medium risk",
            "overall_risk_rating": "medium",
            "key_risks": [{"risk": "Late delivery", "severity": 3, "likelihood": 3, "category": "ops", "mitigation": "SLA"}],
            "missing_protections": ["No audit clause"],
            "recommendations": [{"priority": "medium", "action": "Add audit rights", "owner": "Procurement"}],
            "escalation_items": [],
        }
        result = _parse_lenient_json(json.dumps(data))
        assert len(result["key_risks"]) == 1
        assert result["overall_risk_rating"] == "medium"


class TestParseLenientJsonDiscoveredFacts:
    """Ensure the refactored code still handles discovered_facts truncation."""

    def test_truncated_discovered_facts_still_salvaged(self):
        """Backward-compat: truncated discovered_facts should still be salvaged."""
        truncated = (
            '{"discovered_facts": ['
            '{"type": "hidden_risk", "claim": "No FM clause", "risk_level": "high"},'
            '{"type": "implicit_obligation", "claim": "Must keep records", "risk_level": "medium"},'
            '{"type": "missing_protection", "claim": "No GDPR compli'
        )
        result = _parse_lenient_json(truncated)
        assert len(result["discovered_facts"]) == 2
        assert result["discovered_facts"][0]["type"] == "hidden_risk"

    def test_empty_response_returns_default_structure(self):
        """Completely unparseable text returns empty default."""
        result = _parse_lenient_json("This is not JSON at all.")
        assert result["discovered_facts"] == []
        assert "parse" in result["summary"].lower() or "could" in result["summary"].lower()
