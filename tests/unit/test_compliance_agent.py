"""Unit tests for ComplianceAgent — T208.

TDD Red: Write tests FIRST, verify they FAIL, then implement agent.
Tests the hybrid classification pipeline:
  1. Missing required clause → RED (deterministic)
  2. Escalation trigger match → RED (deterministic override)
  3. LLM classification for nuanced judgment → GREEN/YELLOW/RED
"""

from __future__ import annotations

import json

import pytest

from contractos.fabric.trust_graph import TrustGraph
from contractos.llm.provider import MockLLMProvider
from contractos.models.clause import Clause, ClauseTypeEnum
from contractos.models.fact import Fact, FactEvidence, FactType
from contractos.models.playbook import (
    AcceptableRange,
    NegotiationTier,
    PlaybookConfig,
    PlaybookPosition,
)
from contractos.models.review import ReviewSeverity


@pytest.fixture
def trust_graph():
    return TrustGraph(":memory:")


@pytest.fixture
def mock_llm():
    return MockLLMProvider()


@pytest.fixture
def sample_playbook():
    return PlaybookConfig(
        name="Test Playbook",
        version="1.0",
        positions={
            "termination": PlaybookPosition(
                clause_type="termination",
                standard_position="Either party may terminate with 30 days notice",
                acceptable_range=AcceptableRange(
                    min_position="15 days notice",
                    max_position="90 days notice",
                ),
                escalation_triggers=["No termination for convenience", "Unilateral termination"],
                priority=NegotiationTier.TIER_2,
                required=True,
            ),
            "liability": PlaybookPosition(
                clause_type="liability",
                standard_position="Mutual cap at 12 months of fees",
                escalation_triggers=["Uncapped liability", "No consequential damages exclusion"],
                priority=NegotiationTier.TIER_1,
                required=True,
            ),
            "confidentiality": PlaybookPosition(
                clause_type="confidentiality",
                standard_position="Mutual confidentiality with standard carve-outs",
                priority=NegotiationTier.TIER_2,
                required=False,
            ),
            "payment": PlaybookPosition(
                clause_type="payment",
                standard_position="Net 30 from invoice date",
                acceptable_range=AcceptableRange(
                    min_position="Net 15",
                    max_position="Net 60",
                ),
                priority=NegotiationTier.TIER_3,
                required=False,
            ),
        },
    )


def _seed_graph(graph: TrustGraph, doc_id: str = "doc-001"):
    """Seed TrustGraph with a contract, facts, and clauses."""
    from datetime import datetime
    from contractos.models.document import Contract

    contract = Contract(
        document_id=doc_id,
        title="Test Agreement",
        file_path="/tmp/test.pdf",
        file_format="pdf",
        file_hash="abc123",
        word_count=5000,
        page_count=10,
        indexed_at=datetime(2026, 1, 1),
        last_parsed_at=datetime(2026, 1, 1),
        extraction_version="v1",
    )
    graph.insert_contract(contract)

    # Termination clause — standard terms
    fact_term = Fact(
        fact_id="f-term-001",
        fact_type=FactType.TEXT_SPAN,
        value="Either party may terminate this Agreement with 30 days written notice.",
        evidence=FactEvidence(
            document_id=doc_id,
            text_span="Either party may terminate this Agreement with 30 days written notice.",
            char_start=1000,
            char_end=1070,
            location_hint="§12.1",
            structural_path="body > section[12] > para[1]",
        ),
        extraction_method="pattern",
        extracted_at=datetime(2026, 1, 1),
    )
    graph.insert_fact(fact_term)

    clause_term = Clause(
        clause_id="c-term-001",
        document_id=doc_id,
        clause_type=ClauseTypeEnum.TERMINATION,
        heading="12.1 Termination",
        section_number="12.1",
        fact_id="f-term-001",
        contained_fact_ids=["f-term-001"],
        classification_method="pattern_match",
    )
    graph.insert_clause(clause_term)

    # Liability clause — with escalation trigger (uncapped)
    fact_liab = Fact(
        fact_id="f-liab-001",
        fact_type=FactType.TEXT_SPAN,
        value="The Supplier shall have uncapped liability for all claims arising under this Agreement.",
        evidence=FactEvidence(
            document_id=doc_id,
            text_span="The Supplier shall have uncapped liability for all claims arising under this Agreement.",
            char_start=2000,
            char_end=2085,
            location_hint="§8.1",
            structural_path="body > section[8] > para[1]",
        ),
        extraction_method="pattern",
        extracted_at=datetime(2026, 1, 1),
    )
    graph.insert_fact(fact_liab)

    clause_liab = Clause(
        clause_id="c-liab-001",
        document_id=doc_id,
        clause_type=ClauseTypeEnum.LIABILITY,
        heading="8.1 Limitation of Liability",
        section_number="8.1",
        fact_id="f-liab-001",
        contained_fact_ids=["f-liab-001"],
        classification_method="pattern_match",
    )
    graph.insert_clause(clause_liab)

    # Payment clause — acceptable terms
    fact_pay = Fact(
        fact_id="f-pay-001",
        fact_type=FactType.TEXT_SPAN,
        value="Payment shall be due Net 30 from the date of invoice.",
        evidence=FactEvidence(
            document_id=doc_id,
            text_span="Payment shall be due Net 30 from the date of invoice.",
            char_start=3000,
            char_end=3053,
            location_hint="§5.1",
            structural_path="body > section[5] > para[1]",
        ),
        extraction_method="pattern",
        extracted_at=datetime(2026, 1, 1),
    )
    graph.insert_fact(fact_pay)

    clause_pay = Clause(
        clause_id="c-pay-001",
        document_id=doc_id,
        clause_type=ClauseTypeEnum.PAYMENT,
        heading="5.1 Payment Terms",
        section_number="5.1",
        fact_id="f-pay-001",
        contained_fact_ids=["f-pay-001"],
        classification_method="pattern_match",
    )
    graph.insert_clause(clause_pay)

    return doc_id


class TestComplianceAgentReview:
    """Test ComplianceAgent.review() returns ReviewResult with correct findings."""

    @pytest.mark.asyncio
    async def test_review_returns_review_result(self, trust_graph, mock_llm, sample_playbook):
        from contractos.agents.compliance_agent import ComplianceAgent
        from contractos.models.review import ReviewResult

        doc_id = _seed_graph(trust_graph)

        # LLM responses for: termination classification, payment classification, negotiation strategy
        mock_llm.add_response(json.dumps({
            "severity": "green",
            "deviation_description": "Clause aligns with standard position",
            "business_impact": "No impact — standard terms",
            "risk_score": {"severity": 1, "likelihood": 1},
        }))
        mock_llm.add_response(json.dumps({
            "severity": "green",
            "deviation_description": "Payment terms match standard",
            "business_impact": "No impact",
            "risk_score": {"severity": 1, "likelihood": 1},
        }))
        # Strategy generation
        mock_llm.add_response("Focus on liability cap as highest priority.")

        agent = ComplianceAgent(trust_graph, mock_llm)
        result = await agent.review(doc_id, sample_playbook)

        assert isinstance(result, ReviewResult)
        assert result.document_id == doc_id
        assert result.playbook_name == "Test Playbook"
        assert len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_missing_required_clause_is_red(self, trust_graph, mock_llm, sample_playbook):
        """Required clause not in contract → automatic RED."""
        from contractos.agents.compliance_agent import ComplianceAgent

        doc_id = _seed_graph(trust_graph)
        # Confidentiality is NOT seeded but IS in playbook (not required though)
        # Liability IS required and IS present but has escalation trigger
        # Let's test with a playbook that requires a clause not in the contract

        playbook = PlaybookConfig(
            name="Strict Playbook",
            positions={
                "data_protection": PlaybookPosition(
                    clause_type="data_protection",
                    standard_position="GDPR compliance required",
                    priority=NegotiationTier.TIER_1,
                    required=True,
                ),
            },
        )

        # No LLM calls needed for missing clause (deterministic)
        # But strategy generation needs one
        mock_llm.add_response("Address missing data protection clause immediately.")

        agent = ComplianceAgent(trust_graph, mock_llm)
        result = await agent.review(doc_id, playbook)

        red_findings = [f for f in result.findings if f.severity == ReviewSeverity.RED]
        assert len(red_findings) >= 1
        missing = [f for f in red_findings if "missing" in f.deviation_description.lower()]
        assert len(missing) >= 1

    @pytest.mark.asyncio
    async def test_escalation_trigger_forces_red(self, trust_graph, mock_llm, sample_playbook):
        """Escalation trigger match → RED regardless of LLM classification."""
        from contractos.agents.compliance_agent import ComplianceAgent

        doc_id = _seed_graph(trust_graph)

        # LLM response for termination (GREEN — standard terms)
        mock_llm.add_response(json.dumps({
            "severity": "green",
            "deviation_description": "Standard termination clause",
            "business_impact": "No impact",
            "risk_score": {"severity": 1, "likelihood": 1},
        }))
        # LLM response for payment (GREEN)
        mock_llm.add_response(json.dumps({
            "severity": "green",
            "deviation_description": "Standard payment terms",
            "business_impact": "No impact",
            "risk_score": {"severity": 1, "likelihood": 1},
        }))
        # Strategy
        mock_llm.add_response("Address uncapped liability immediately.")

        agent = ComplianceAgent(trust_graph, mock_llm)
        result = await agent.review(doc_id, sample_playbook)

        # Liability clause has "uncapped liability" which matches escalation trigger
        liab_findings = [f for f in result.findings if f.clause_type == "liability"]
        assert len(liab_findings) >= 1
        assert liab_findings[0].severity == ReviewSeverity.RED

    @pytest.mark.asyncio
    async def test_green_classification(self, trust_graph, mock_llm, sample_playbook):
        """Clause matching playbook standard → GREEN."""
        from contractos.agents.compliance_agent import ComplianceAgent

        doc_id = _seed_graph(trust_graph)

        # LLM classifies termination as GREEN
        mock_llm.add_response(json.dumps({
            "severity": "green",
            "deviation_description": "Clause aligns with standard 30-day notice",
            "business_impact": "No impact",
            "risk_score": {"severity": 1, "likelihood": 1},
        }))
        # LLM classifies payment as GREEN
        mock_llm.add_response(json.dumps({
            "severity": "green",
            "deviation_description": "Net 30 matches standard",
            "business_impact": "No impact",
            "risk_score": {"severity": 1, "likelihood": 1},
        }))
        # Strategy
        mock_llm.add_response("No significant issues found.")

        agent = ComplianceAgent(trust_graph, mock_llm)
        result = await agent.review(doc_id, sample_playbook)

        term_findings = [f for f in result.findings if f.clause_type == "termination"]
        assert len(term_findings) >= 1
        assert term_findings[0].severity == ReviewSeverity.GREEN

    @pytest.mark.asyncio
    async def test_yellow_classification(self, trust_graph, mock_llm):
        """Clause outside standard but within range → YELLOW."""
        from contractos.agents.compliance_agent import ComplianceAgent

        doc_id = _seed_graph(trust_graph)

        playbook = PlaybookConfig(
            name="Test",
            positions={
                "termination": PlaybookPosition(
                    clause_type="termination",
                    standard_position="60 days notice required",
                    acceptable_range=AcceptableRange(
                        min_position="30 days",
                        max_position="90 days",
                    ),
                    priority=NegotiationTier.TIER_2,
                ),
            },
        )

        # LLM classifies as YELLOW (within range but not standard)
        mock_llm.add_response(json.dumps({
            "severity": "yellow",
            "deviation_description": "30 days notice vs. preferred 60 days",
            "business_impact": "Shorter notice period reduces transition time",
            "risk_score": {"severity": 2, "likelihood": 3},
        }))
        # Strategy
        mock_llm.add_response("Negotiate for 60-day notice period.")

        agent = ComplianceAgent(trust_graph, mock_llm)
        result = await agent.review(doc_id, playbook)

        term_findings = [f for f in result.findings if f.clause_type == "termination"]
        assert len(term_findings) >= 1
        assert term_findings[0].severity == ReviewSeverity.YELLOW

    @pytest.mark.asyncio
    async def test_findings_have_provenance_facts(self, trust_graph, mock_llm, sample_playbook):
        """Each finding references extracted fact IDs."""
        from contractos.agents.compliance_agent import ComplianceAgent

        doc_id = _seed_graph(trust_graph)

        mock_llm.add_response(json.dumps({
            "severity": "green",
            "deviation_description": "Standard",
            "business_impact": "None",
            "risk_score": {"severity": 1, "likelihood": 1},
        }))
        mock_llm.add_response(json.dumps({
            "severity": "green",
            "deviation_description": "Standard",
            "business_impact": "None",
            "risk_score": {"severity": 1, "likelihood": 1},
        }))
        mock_llm.add_response("No issues.")

        agent = ComplianceAgent(trust_graph, mock_llm)
        result = await agent.review(doc_id, sample_playbook)

        # At least one finding should have provenance facts
        findings_with_prov = [f for f in result.findings if f.provenance_facts]
        assert len(findings_with_prov) >= 1

    @pytest.mark.asyncio
    async def test_review_counts(self, trust_graph, mock_llm, sample_playbook):
        """ReviewResult has correct green/yellow/red counts."""
        from contractos.agents.compliance_agent import ComplianceAgent

        doc_id = _seed_graph(trust_graph)

        # Termination → GREEN
        mock_llm.add_response(json.dumps({
            "severity": "green",
            "deviation_description": "Standard",
            "business_impact": "None",
            "risk_score": {"severity": 1, "likelihood": 1},
        }))
        # Payment → GREEN
        mock_llm.add_response(json.dumps({
            "severity": "green",
            "deviation_description": "Standard",
            "business_impact": "None",
            "risk_score": {"severity": 1, "likelihood": 1},
        }))
        # Strategy
        mock_llm.add_response("Focus on liability.")

        agent = ComplianceAgent(trust_graph, mock_llm)
        result = await agent.review(doc_id, sample_playbook)

        total = result.green_count + result.yellow_count + result.red_count
        assert total == len(result.findings)
        assert total > 0

    @pytest.mark.asyncio
    async def test_nonexistent_document(self, trust_graph, mock_llm, sample_playbook):
        """Review of nonexistent document raises or returns empty."""
        from contractos.agents.compliance_agent import ComplianceAgent

        agent = ComplianceAgent(trust_graph, mock_llm)

        with pytest.raises(ValueError, match="not found"):
            await agent.review("nonexistent-doc", sample_playbook)
