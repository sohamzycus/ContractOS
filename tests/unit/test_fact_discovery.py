"""Unit tests for LLM-powered hidden fact discovery."""

from __future__ import annotations

import json

import pytest

from contractos.llm.provider import MockLLMProvider
from contractos.tools.fact_discovery import DiscoveredFact, DiscoveryResult, discover_hidden_facts


@pytest.fixture
def mock_llm():
    return MockLLMProvider()


@pytest.fixture
def sample_contract_text():
    return """
    This Agreement is between Acme Corp ("Buyer") and Widget Inc ("Supplier").

    1. TERM: This Agreement shall be effective for a period of twenty-four (24) months
    from the Effective Date.

    2. PAYMENT: The Buyer shall pay the Supplier within Net 90 days of invoice receipt.
    Late payments shall accrue interest at 1.5% per month.

    3. CONFIDENTIALITY: Each Party shall treat as confidential all information received
    from the other Party that is marked as confidential.

    4. TERMINATION: Either Party may terminate this Agreement with 30 days written notice.
    Upon termination, all outstanding invoices become immediately due and payable.

    5. LIMITATION OF LIABILITY: The Supplier's total liability shall not exceed the fees
    paid in the preceding twelve (12) months.

    6. GOVERNING LAW: This Agreement shall be governed by the laws of the State of Delaware.
    """


@pytest.fixture
def sample_facts_summary():
    return """
    - [f-001] (text_span) "twenty-four (24) months" @ characters 120-145
    - [f-002] (text_span) "Net 90 days" @ characters 200-211
    - [f-003] (text_span) "1.5% per month" @ characters 250-264
    - [f-004] (text_span) "30 days" @ characters 350-357
    - [f-005] (entity) "Acme Corp" @ characters 30-39
    """


@pytest.fixture
def sample_clauses_summary():
    return """
    - [cl-001] term: 1. TERM
    - [cl-002] payment: 2. PAYMENT
    - [cl-003] confidentiality: 3. CONFIDENTIALITY
    - [cl-004] termination: 4. TERMINATION
    - [cl-005] limitation_of_liability: 5. LIMITATION OF LIABILITY
    - [cl-006] governing_law: 6. GOVERNING LAW
    """


@pytest.fixture
def sample_bindings_summary():
    return """
    - "Buyer" -> "Acme Corp" (alias)
    - "Supplier" -> "Widget Inc" (alias)
    """


class TestDiscoveredFact:
    """Tests for the DiscoveredFact model."""

    def test_create_discovered_fact(self):
        fact = DiscoveredFact(
            fact_type="implicit_obligation",
            claim="Buyer must provide purchase orders",
            evidence="Section 2 implies ordering process",
            risk_level="medium",
            explanation="Payment clause assumes orders exist",
        )
        assert fact.type == "implicit_obligation"
        assert fact.claim == "Buyer must provide purchase orders"
        assert fact.risk_level == "medium"

    def test_to_dict(self):
        fact = DiscoveredFact(
            fact_type="hidden_risk",
            claim="No force majeure clause",
            risk_level="high",
        )
        d = fact.to_dict()
        assert d["type"] == "hidden_risk"
        assert d["claim"] == "No force majeure clause"
        assert d["risk_level"] == "high"
        assert "evidence" in d
        assert "explanation" in d


class TestDiscoveryResult:
    """Tests for the DiscoveryResult model."""

    def test_empty_result(self):
        result = DiscoveryResult()
        assert len(result.discovered_facts) == 0
        assert result.summary == ""
        d = result.to_dict()
        assert d["count"] == 0

    def test_result_with_facts(self):
        result = DiscoveryResult()
        result.discovered_facts.append(
            DiscoveredFact("hidden_risk", "No IP clause", risk_level="high")
        )
        result.discovered_facts.append(
            DiscoveredFact("implicit_obligation", "Must maintain records", risk_level="low")
        )
        result.summary = "Found 2 hidden facts"
        d = result.to_dict()
        assert d["count"] == 2
        assert len(d["discovered_facts"]) == 2


class TestDiscoverHiddenFacts:
    """Tests for the LLM-powered discovery function."""

    @pytest.mark.asyncio
    async def test_discovery_returns_facts(
        self, mock_llm, sample_contract_text, sample_facts_summary,
        sample_clauses_summary, sample_bindings_summary,
    ):
        """Discovery should return structured facts from LLM response."""
        mock_llm.add_response(json.dumps({
            "discovered_facts": [
                {
                    "type": "hidden_risk",
                    "claim": "No force majeure clause exists",
                    "evidence": "The agreement lacks any force majeure provision",
                    "risk_level": "high",
                    "explanation": "Without force majeure, parties cannot excuse performance due to extraordinary events",
                },
                {
                    "type": "implicit_obligation",
                    "claim": "Buyer implicitly required to provide purchase orders before payment",
                    "evidence": "Section 2 references 'invoice receipt' which implies a prior ordering process",
                    "risk_level": "medium",
                    "explanation": "The payment clause assumes an ordering workflow exists",
                },
                {
                    "type": "missing_protection",
                    "claim": "No data protection or GDPR compliance clause",
                    "evidence": "The agreement contains no provisions for data handling",
                    "risk_level": "high",
                    "explanation": "Modern contracts should address data protection obligations",
                },
            ],
            "summary": "Found 3 hidden facts: missing force majeure, implicit ordering obligation, no data protection",
            "categories_found": "hidden_risk, implicit_obligation, missing_protection",
        }))

        result = await discover_hidden_facts(
            contract_text=sample_contract_text,
            existing_facts_summary=sample_facts_summary,
            clauses_summary=sample_clauses_summary,
            bindings_summary=sample_bindings_summary,
            llm=mock_llm,
        )

        assert len(result.discovered_facts) == 3
        assert result.discovered_facts[0].type == "hidden_risk"
        assert "force majeure" in result.discovered_facts[0].claim.lower()
        assert result.discovered_facts[0].risk_level == "high"
        assert result.discovered_facts[1].type == "implicit_obligation"
        assert result.discovered_facts[2].type == "missing_protection"
        assert result.summary != ""
        assert result.categories_found != ""
        assert result.discovery_time_ms >= 0

    @pytest.mark.asyncio
    async def test_discovery_handles_empty_response(
        self, mock_llm, sample_contract_text, sample_facts_summary,
        sample_clauses_summary, sample_bindings_summary,
    ):
        """Discovery should handle LLM returning no facts gracefully."""
        mock_llm.add_response(json.dumps({
            "discovered_facts": [],
            "summary": "No hidden facts found",
            "categories_found": "",
        }))

        result = await discover_hidden_facts(
            contract_text=sample_contract_text,
            existing_facts_summary=sample_facts_summary,
            clauses_summary=sample_clauses_summary,
            bindings_summary=sample_bindings_summary,
            llm=mock_llm,
        )

        assert len(result.discovered_facts) == 0
        assert result.summary == "No hidden facts found"

    @pytest.mark.asyncio
    async def test_discovery_handles_llm_error(
        self, sample_contract_text, sample_facts_summary,
        sample_clauses_summary, sample_bindings_summary,
    ):
        """Discovery should handle LLM errors gracefully."""
        mock_llm = MockLLMProvider()  # No responses added — will raise

        result = await discover_hidden_facts(
            contract_text=sample_contract_text,
            existing_facts_summary=sample_facts_summary,
            clauses_summary=sample_clauses_summary,
            bindings_summary=sample_bindings_summary,
            llm=mock_llm,
        )

        assert len(result.discovered_facts) == 0
        assert "error" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_discovery_truncates_long_text(
        self, mock_llm, sample_facts_summary,
        sample_clauses_summary, sample_bindings_summary,
    ):
        """Discovery should truncate very long contract text."""
        long_text = "A" * 20000  # 20k chars

        mock_llm.add_response(json.dumps({
            "discovered_facts": [
                {"type": "hidden_risk", "claim": "Test", "risk_level": "low"},
            ],
            "summary": "Found 1 fact",
            "categories_found": "hidden_risk",
        }))

        result = await discover_hidden_facts(
            contract_text=long_text,
            existing_facts_summary=sample_facts_summary,
            clauses_summary=sample_clauses_summary,
            bindings_summary=sample_bindings_summary,
            llm=mock_llm,
        )

        # Should still work despite long text
        assert len(result.discovered_facts) == 1
        # Verify the LLM received truncated text
        call = mock_llm.call_log[0]
        assert "truncated" in call["messages"][0]["content"]

    @pytest.mark.asyncio
    async def test_discovery_filters_empty_claims(
        self, mock_llm, sample_contract_text, sample_facts_summary,
        sample_clauses_summary, sample_bindings_summary,
    ):
        """Discovery should filter out facts with empty claims."""
        mock_llm.add_response(json.dumps({
            "discovered_facts": [
                {"type": "hidden_risk", "claim": "Valid claim", "risk_level": "high"},
                {"type": "hidden_risk", "claim": "", "risk_level": "low"},  # Empty
            ],
            "summary": "Found facts",
            "categories_found": "hidden_risk",
        }))

        result = await discover_hidden_facts(
            contract_text=sample_contract_text,
            existing_facts_summary=sample_facts_summary,
            clauses_summary=sample_clauses_summary,
            bindings_summary=sample_bindings_summary,
            llm=mock_llm,
        )

        assert len(result.discovered_facts) == 1
        assert result.discovered_facts[0].claim == "Valid claim"
