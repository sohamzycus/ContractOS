"""Unit tests for NDATriageAgent — T224.

TDD Red: Write tests FIRST, verify they FAIL, then implement agent.
"""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from contractos.fabric.trust_graph import TrustGraph
from contractos.llm.provider import MockLLMProvider
from contractos.models.clause import Clause, ClauseTypeEnum
from contractos.models.fact import Fact, FactEvidence, FactType


@pytest.fixture
def trust_graph():
    return TrustGraph(":memory:")


@pytest.fixture
def mock_llm():
    return MockLLMProvider()


def _seed_nda(graph: TrustGraph, doc_id: str = "nda-001"):
    """Seed a standard NDA into TrustGraph."""
    from contractos.models.document import Contract

    contract = Contract(
        document_id=doc_id,
        title="Mutual Non-Disclosure Agreement",
        file_path="/tmp/nda.pdf",
        file_format="pdf",
        file_hash="nda123",
        word_count=3000,
        page_count=5,
        indexed_at=datetime(2026, 1, 1),
        last_parsed_at=datetime(2026, 1, 1),
        extraction_version="v1",
    )
    graph.insert_contract(contract)

    # Confidentiality clause with standard carveouts
    fact_conf = Fact(
        fact_id="f-conf-001",
        fact_type=FactType.TEXT_SPAN,
        value="Each party agrees to maintain the confidentiality of all Confidential Information. "
              "Confidential Information does not include information that: (a) is or becomes publicly available "
              "through no fault of the receiving party; (b) was in the receiving party's possession prior to "
              "disclosure; (c) is independently developed; (d) is received from a third party without "
              "restriction; (e) is required to be disclosed by law or court order.",
        evidence=FactEvidence(
            document_id=doc_id,
            text_span="Each party agrees to maintain the confidentiality...",
            char_start=500,
            char_end=900,
            location_hint="§2.1",
            structural_path="body > section[2] > para[1]",
        ),
        extraction_method="pattern",
        extracted_at=datetime(2026, 1, 1),
    )
    graph.insert_fact(fact_conf)

    clause_conf = Clause(
        clause_id="c-conf-001",
        document_id=doc_id,
        clause_type=ClauseTypeEnum.CONFIDENTIALITY,
        heading="2.1 Confidentiality Obligations",
        section_number="2.1",
        fact_id="f-conf-001",
        contained_fact_ids=["f-conf-001"],
        classification_method="pattern_match",
    )
    graph.insert_clause(clause_conf)

    # Term/duration fact
    fact_term = Fact(
        fact_id="f-term-001",
        fact_type=FactType.TEXT_SPAN,
        value="This Agreement shall remain in effect for a period of two (2) years from the Effective Date.",
        evidence=FactEvidence(
            document_id=doc_id,
            text_span="This Agreement shall remain in effect for a period of two (2) years...",
            char_start=1200,
            char_end=1300,
            location_hint="§5.1",
            structural_path="body > section[5] > para[1]",
        ),
        extraction_method="pattern",
        extracted_at=datetime(2026, 1, 1),
    )
    graph.insert_fact(fact_term)

    clause_term = Clause(
        clause_id="c-term-001",
        document_id=doc_id,
        clause_type=ClauseTypeEnum.TERMINATION,
        heading="5.1 Term",
        section_number="5.1",
        fact_id="f-term-001",
        contained_fact_ids=["f-term-001"],
        classification_method="pattern_match",
    )
    graph.insert_clause(clause_term)

    # Governing law
    fact_gov = Fact(
        fact_id="f-gov-001",
        fact_type=FactType.TEXT_SPAN,
        value="This Agreement shall be governed by the laws of the State of Delaware.",
        evidence=FactEvidence(
            document_id=doc_id,
            text_span="This Agreement shall be governed by the laws of the State of Delaware.",
            char_start=1500,
            char_end=1570,
            location_hint="§7.1",
            structural_path="body > section[7] > para[1]",
        ),
        extraction_method="pattern",
        extracted_at=datetime(2026, 1, 1),
    )
    graph.insert_fact(fact_gov)

    clause_gov = Clause(
        clause_id="c-gov-001",
        document_id=doc_id,
        clause_type=ClauseTypeEnum.GOVERNING_LAW,
        heading="7.1 Governing Law",
        section_number="7.1",
        fact_id="f-gov-001",
        contained_fact_ids=["f-gov-001"],
        classification_method="pattern_match",
    )
    graph.insert_clause(clause_gov)

    return doc_id


class TestNDATriageAgent:
    """Test NDATriageAgent.triage()."""

    @pytest.mark.asyncio
    async def test_triage_returns_triage_result(self, trust_graph, mock_llm):
        from contractos.agents.nda_triage_agent import NDATriageAgent
        from contractos.models.triage import TriageResult

        doc_id = _seed_nda(trust_graph)

        # LLM responses for hybrid/llm_only checklist items
        for _ in range(10):
            mock_llm.add_response(json.dumps({
                "status": "pass",
                "finding": "Meets criteria",
                "evidence": "Standard language found",
            }))

        agent = NDATriageAgent(trust_graph, mock_llm)
        result = await agent.triage(doc_id)

        assert isinstance(result, TriageResult)
        assert result.document_id == doc_id
        assert len(result.checklist_results) > 0

    @pytest.mark.asyncio
    async def test_all_pass_is_green(self, trust_graph, mock_llm):
        """All checklist items PASS → GREEN classification."""
        from contractos.agents.nda_triage_agent import NDATriageAgent
        from contractos.models.triage import TriageLevel

        doc_id = _seed_nda(trust_graph)

        for _ in range(10):
            mock_llm.add_response(json.dumps({
                "status": "pass",
                "finding": "Meets criteria",
                "evidence": "Standard language",
            }))

        agent = NDATriageAgent(trust_graph, mock_llm)
        result = await agent.triage(doc_id)

        assert result.classification.level == TriageLevel.GREEN

    @pytest.mark.asyncio
    async def test_non_critical_fail_is_yellow(self, trust_graph, mock_llm):
        """One non-critical FAIL → YELLOW."""
        from contractos.agents.nda_triage_agent import NDATriageAgent
        from contractos.models.triage import TriageLevel

        doc_id = _seed_nda(trust_graph)

        # First item fails, rest pass
        mock_llm.add_response(json.dumps({
            "status": "fail",
            "finding": "Definition scope too broad",
            "evidence": "Confidential Information includes...",
        }))
        for _ in range(9):
            mock_llm.add_response(json.dumps({
                "status": "pass",
                "finding": "Meets criteria",
                "evidence": "Standard",
            }))

        agent = NDATriageAgent(trust_graph, mock_llm)
        result = await agent.triage(doc_id)

        assert result.classification.level in (TriageLevel.YELLOW, TriageLevel.RED)
        assert result.fail_count >= 1

    @pytest.mark.asyncio
    async def test_checklist_has_items(self, trust_graph, mock_llm):
        """Triage evaluates multiple checklist items."""
        from contractos.agents.nda_triage_agent import NDATriageAgent

        doc_id = _seed_nda(trust_graph)

        for _ in range(10):
            mock_llm.add_response(json.dumps({
                "status": "pass",
                "finding": "OK",
                "evidence": "Found",
            }))

        agent = NDATriageAgent(trust_graph, mock_llm)
        result = await agent.triage(doc_id)

        assert len(result.checklist_results) >= 5

    @pytest.mark.asyncio
    async def test_nonexistent_document_raises(self, trust_graph, mock_llm):
        from contractos.agents.nda_triage_agent import NDATriageAgent

        agent = NDATriageAgent(trust_graph, mock_llm)

        with pytest.raises(ValueError, match="not found"):
            await agent.triage("nonexistent-doc")

    @pytest.mark.asyncio
    async def test_triage_has_classification_with_routing(self, trust_graph, mock_llm):
        """Classification includes routing and timeline."""
        from contractos.agents.nda_triage_agent import NDATriageAgent

        doc_id = _seed_nda(trust_graph)

        for _ in range(10):
            mock_llm.add_response(json.dumps({
                "status": "pass",
                "finding": "OK",
                "evidence": "Found",
            }))

        agent = NDATriageAgent(trust_graph, mock_llm)
        result = await agent.triage(doc_id)

        assert result.classification.routing != ""
        assert result.classification.timeline != ""
