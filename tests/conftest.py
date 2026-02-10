"""Shared test fixtures for ContractOS."""

from __future__ import annotations

from datetime import datetime

import pytest

from contractos.models.fact import EntityType, Fact, FactEvidence, FactType
from contractos.models.binding import Binding, BindingScope, BindingType
from contractos.models.inference import Inference, InferenceType
from contractos.models.clause import (
    Clause,
    ClauseTypeEnum,
    CrossReference,
    ReferenceEffect,
    ReferenceType,
)
from contractos.models.provenance import ProvenanceChain, ProvenanceNode
from contractos.models.query import Query, QueryResult, QueryScope
from contractos.models.workspace import ReasoningSession, SessionStatus, Workspace

NOW = datetime(2025, 2, 9, 12, 0, 0)


@pytest.fixture
def sample_evidence() -> FactEvidence:
    return FactEvidence(
        document_id="doc-001",
        text_span="Net 90 from invoice date",
        char_start=1203,
        char_end=1227,
        location_hint="§5.2, paragraph 1",
        structural_path="body > section[5] > para[1]",
    )


@pytest.fixture
def sample_fact(sample_evidence: FactEvidence) -> Fact:
    return Fact(
        fact_id="f-001",
        fact_type=FactType.TEXT_SPAN,
        value="Net 90 from invoice date",
        evidence=sample_evidence,
        extraction_method="docx_parser_v1",
        extracted_at=NOW,
    )


@pytest.fixture
def sample_entity_fact() -> Fact:
    return Fact(
        fact_id="f-002",
        fact_type=FactType.ENTITY,
        entity_type=EntityType.PARTY,
        value="Dell Technologies Inc",
        evidence=FactEvidence(
            document_id="doc-001",
            text_span='Dell Technologies Inc ("Supplier")',
            char_start=245,
            char_end=289,
            location_hint="§1.1, paragraph 1",
            structural_path="body > section[1] > para[1]",
        ),
        extraction_method="docx_parser_v1",
        extracted_at=NOW,
    )


@pytest.fixture
def sample_binding() -> Binding:
    return Binding(
        binding_id="b-001",
        binding_type=BindingType.DEFINITION,
        term="Supplier",
        resolves_to="Dell Technologies Inc and its affiliates",
        source_fact_id="f-010",
        document_id="doc-001",
        scope=BindingScope.CONTRACT,
    )


@pytest.fixture
def sample_inference() -> Inference:
    return Inference(
        inference_id="i-001",
        inference_type=InferenceType.OBLIGATION,
        claim="This contract includes a maintenance obligation for IT equipment",
        supporting_fact_ids=["f-001", "f-002"],
        reasoning_chain="§7.3 describes support obligations. Schedule A lists Dell Inspiron.",
        confidence=0.92,
        confidence_basis="Strong evidence: direct clause text + product listing",
        generated_by="document_agent_v1",
        generated_at=NOW,
        document_id="doc-001",
    )


@pytest.fixture
def sample_clause() -> Clause:
    return Clause(
        clause_id="c-001",
        document_id="doc-001",
        clause_type=ClauseTypeEnum.TERMINATION,
        heading="12.1 Termination",
        section_number="12.1",
        fact_id="f-020",
        contained_fact_ids=["f-021", "f-022"],
        cross_reference_ids=["xr-001"],
        classification_method="pattern_match",
    )


@pytest.fixture
def sample_cross_reference() -> CrossReference:
    return CrossReference(
        reference_id="xr-001",
        source_clause_id="c-001",
        target_reference="section 3.2.1",
        reference_type=ReferenceType.SECTION_REF,
        effect=ReferenceEffect.CONDITIONS,
        context="the notice period as mentioned in section 3.2.1",
        source_fact_id="f-025",
    )


@pytest.fixture
def sample_provenance() -> ProvenanceChain:
    return ProvenanceChain(
        nodes=[
            ProvenanceNode(
                node_type="fact",
                reference_id="f-001",
                summary="§5.2 states 'Net 90 from invoice date'",
                document_location="§5.2, characters 1203-1227",
            ),
        ],
        reasoning_summary="Payment terms found directly in §5.2.",
    )


@pytest.fixture
def sample_query() -> Query:
    return Query(
        query_id="q-001",
        text="What are the payment terms?",
        scope=QueryScope.SINGLE_DOCUMENT,
        target_document_ids=["doc-001"],
        submitted_at=NOW,
    )


@pytest.fixture
def sample_query_result(sample_provenance: ProvenanceChain) -> QueryResult:
    return QueryResult(
        result_id="r-001",
        query_id="q-001",
        answer="Net 90 from invoice date, per §5.2.",
        answer_type="fact",
        confidence=None,
        provenance=sample_provenance,
        facts_referenced=["f-001"],
        generated_at=NOW,
        generation_time_ms=1200,
    )


@pytest.fixture
def sample_workspace() -> Workspace:
    return Workspace(
        workspace_id="w-001",
        name="Dell Contracts Review",
        indexed_documents=["doc-001"],
        created_at=NOW,
        last_accessed_at=NOW,
    )


@pytest.fixture
def sample_session() -> ReasoningSession:
    return ReasoningSession(
        session_id="s-001",
        workspace_id="w-001",
        query_text="What are the payment terms?",
        query_scope="single_document",
        target_document_ids=["doc-001"],
        status=SessionStatus.ACTIVE,
        started_at=NOW,
    )
