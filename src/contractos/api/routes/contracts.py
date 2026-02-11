"""Contract upload, retrieval, and document intelligence endpoints."""

from __future__ import annotations

import hashlib
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from contractos.api.deps import AppState, get_state
from contractos.fabric.embedding_index import build_chunks_from_extraction
from contractos.models.document import Contract
from contractos.tools.binding_resolver import resolve_bindings
from contractos.tools.confidence import ConfidenceDisplay, confidence_label
from contractos.tools.fact_extractor import extract_from_file

router = APIRouter(prefix="/contracts", tags=["contracts"])


# ── Response Models ────────────────────────────────────────────────


class ContractResponse(BaseModel):
    """Response after uploading or retrieving a contract."""

    document_id: str
    title: str
    file_format: str
    parties: list[str]
    page_count: int
    word_count: int
    fact_count: int = 0
    clause_count: int = 0
    binding_count: int = 0
    status: str = "indexed"


class ContractListResponse(BaseModel):
    """Response for listing contracts in a workspace."""

    contracts: list[ContractResponse]
    total: int


class FactResponse(BaseModel):
    """A single extracted fact."""

    fact_id: str
    fact_type: str
    entity_type: str | None = None
    value: str
    document_id: str
    text_span: str
    char_start: int
    char_end: int
    location_hint: str
    structural_path: str


class ClauseResponse(BaseModel):
    """A classified clause."""

    clause_id: str
    clause_type: str
    heading: str
    section_number: str | None = None
    cross_reference_ids: list[str] = Field(default_factory=list)


class CrossReferenceResponse(BaseModel):
    """A cross-reference between clauses."""

    reference_id: str
    source_clause_id: str
    target_clause_id: str | None = None
    reference_text: str
    reference_type: str
    effect: str
    resolved: bool


class BindingResponse(BaseModel):
    """A resolved binding."""

    binding_id: str
    binding_type: str
    term: str
    resolves_to: str
    source_fact_id: str
    document_id: str
    scope: str


class GapResponse(BaseModel):
    """A missing mandatory fact for a clause."""

    clause_id: str
    clause_type: str
    fact_spec_name: str
    required: bool
    status: str


# ── Endpoints ──────────────────────────────────────────────────────


@router.post("/upload", response_model=ContractResponse, status_code=201)
async def upload_contract(
    file: UploadFile,
    state: Annotated[AppState, Depends(get_state)],
) -> ContractResponse:
    """Upload a contract document (docx or pdf) for indexing.

    Triggers the full extraction pipeline:
    1. Parse document → paragraphs, tables, headings
    2. Extract facts (patterns, table cells, aliases)
    3. Classify clauses from headings
    4. Extract cross-references
    5. Check mandatory fact slots
    6. Resolve bindings (definitions + aliases)
    7. Store everything in TrustGraph
    """
    if file.filename is None:
        raise HTTPException(status_code=400, detail="Filename required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("docx", "pdf"):
        raise HTTPException(
            status_code=400, detail=f"Unsupported format: {ext}. Use docx or pdf."
        )

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    doc_id = f"doc-{uuid.uuid4().hex[:12]}"
    now = datetime.now()

    # Write to temp file for parsing
    suffix = f".{ext}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Run extraction pipeline
        extraction = extract_from_file(tmp_path, doc_id)

        # Resolve bindings
        full_text = extraction.parsed_document.full_text if extraction.parsed_document else ""
        all_bindings = resolve_bindings(
            extraction.facts, extraction.bindings, full_text, doc_id
        )

        # Compute metadata from parsed document
        parsed = extraction.parsed_document
        page_count = 0
        word_count = 0
        parties: list[str] = []

        if parsed:
            word_count = len(parsed.full_text.split())
            # Extract party names from alias bindings
            for b in all_bindings:
                if b.binding_type.value == "alias" and b.resolves_to not in parties:
                    parties.append(b.resolves_to)

        # Store contract metadata
        contract = Contract(
            document_id=doc_id,
            title=file.filename.rsplit(".", 1)[0],
            file_path=f"uploads/{file.filename}",
            file_format=ext,
            file_hash=file_hash,
            parties=parties,
            page_count=page_count,
            word_count=word_count,
            indexed_at=now,
            last_parsed_at=now,
            extraction_version="0.1.0",
        )
        state.trust_graph.insert_contract(contract)

        # Store extracted entities
        state.trust_graph.insert_facts(extraction.facts)
        for binding in all_bindings:
            state.trust_graph.insert_binding(binding)
        for clause in extraction.clauses:
            state.trust_graph.insert_clause(clause)
        for xref in extraction.cross_references:
            state.trust_graph.insert_cross_reference(xref)
        for slot in extraction.clause_fact_slots:
            state.trust_graph.insert_clause_fact_slot(slot)

        # Build semantic vector index (FAISS + sentence-transformers)
        chunks = build_chunks_from_extraction(
            doc_id, extraction.facts, extraction.clauses, all_bindings
        )
        state.embedding_index.index_document(doc_id, chunks)

        return ContractResponse(
            document_id=doc_id,
            title=contract.title,
            file_format=ext,
            parties=parties,
            page_count=page_count,
            word_count=word_count,
            fact_count=len(extraction.facts),
            clause_count=len(extraction.clauses),
            binding_count=len(all_bindings),
            status="indexed",
        )
    except Exception as e:
        # Store contract with error status
        contract = Contract(
            document_id=doc_id,
            title=file.filename.rsplit(".", 1)[0],
            file_path=f"uploads/{file.filename}",
            file_format=ext,
            file_hash=file_hash,
            parties=[],
            page_count=0,
            word_count=0,
            indexed_at=now,
            last_parsed_at=now,
            extraction_version="0.1.0",
        )
        state.trust_graph.insert_contract(contract)
        return ContractResponse(
            document_id=doc_id,
            title=contract.title,
            file_format=ext,
            parties=[],
            page_count=0,
            word_count=0,
            fact_count=0,
            clause_count=0,
            binding_count=0,
            status=f"error: {e!s}",
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


class ClearAllResponse(BaseModel):
    """Response for clearing all data."""

    cleared_contracts: int
    cleared_tables: dict[str, int]
    message: str


@router.get("", response_model=list[ContractResponse])
async def list_contracts(
    state: Annotated[AppState, Depends(get_state)],
) -> list[ContractResponse]:
    """List all indexed contracts."""
    contracts = state.trust_graph.list_contracts()
    result = []
    for c in contracts:
        fact_count = state.trust_graph.count_facts(c.document_id)
        clauses = state.trust_graph.get_clauses_by_document(c.document_id)
        bindings = state.trust_graph.get_bindings_by_document(c.document_id)
        result.append(ContractResponse(
            document_id=c.document_id,
            title=c.title,
            file_format=c.file_format,
            parties=c.parties,
            page_count=c.page_count,
            word_count=c.word_count,
            fact_count=fact_count,
            clause_count=len(clauses),
            binding_count=len(bindings),
            status="indexed",
        ))
    return result


@router.delete("/clear", response_model=ClearAllResponse)
async def clear_all_contracts(
    state: Annotated[AppState, Depends(get_state)],
) -> ClearAllResponse:
    """Clear ALL uploaded contracts, facts, sessions, and FAISS indices.

    This is a destructive operation — all data is permanently deleted.
    """
    # Count contracts before clearing
    contracts = state.trust_graph.list_contracts()
    contract_count = len(contracts)

    # Remove FAISS indices for each document
    for c in contracts:
        state.embedding_index.remove_document(c.document_id)

    # Clear all SQLite data
    counts = state.trust_graph.clear_all_data()

    return ClearAllResponse(
        cleared_contracts=contract_count,
        cleared_tables=counts,
        message=f"Cleared {contract_count} contracts and all associated data",
    )


@router.get("/{document_id}", response_model=ContractResponse)
async def get_contract(
    document_id: str,
    state: Annotated[AppState, Depends(get_state)],
) -> ContractResponse:
    """Retrieve metadata for an indexed contract."""
    contract = state.trust_graph.get_contract(document_id)
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Contract {document_id} not found")
    fact_count = state.trust_graph.count_facts(document_id)
    clauses = state.trust_graph.get_clauses_by_document(document_id)
    bindings = state.trust_graph.get_bindings_by_document(document_id)
    return ContractResponse(
        document_id=contract.document_id,
        title=contract.title,
        file_format=contract.file_format,
        parties=contract.parties,
        page_count=contract.page_count,
        word_count=contract.word_count,
        fact_count=fact_count,
        clause_count=len(clauses),
        binding_count=len(bindings),
        status="indexed",
    )


@router.get("/{document_id}/facts", response_model=list[FactResponse])
async def get_facts(
    document_id: str,
    state: Annotated[AppState, Depends(get_state)],
    fact_type: str | None = None,
    entity_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[FactResponse]:
    """Retrieve extracted facts for a contract with optional filters."""
    contract = state.trust_graph.get_contract(document_id)
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Contract {document_id} not found")

    facts = state.trust_graph.get_facts_by_document(
        document_id, fact_type=fact_type, entity_type=entity_type
    )

    # Apply pagination
    paginated = facts[offset : offset + limit]

    return [
        FactResponse(
            fact_id=f.fact_id,
            fact_type=f.fact_type.value if hasattr(f.fact_type, "value") else str(f.fact_type),
            entity_type=f.entity_type.value if f.entity_type and hasattr(f.entity_type, "value") else None,
            value=f.value,
            document_id=f.evidence.document_id,
            text_span=f.evidence.text_span,
            char_start=f.evidence.char_start,
            char_end=f.evidence.char_end,
            location_hint=f.evidence.location_hint,
            structural_path=f.evidence.structural_path,
        )
        for f in paginated
    ]


@router.get("/{document_id}/clauses", response_model=list[ClauseResponse])
async def get_clauses(
    document_id: str,
    state: Annotated[AppState, Depends(get_state)],
    clause_type: str | None = None,
) -> list[ClauseResponse]:
    """Retrieve classified clauses for a contract."""
    contract = state.trust_graph.get_contract(document_id)
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Contract {document_id} not found")

    clauses = state.trust_graph.get_clauses_by_document(document_id, clause_type=clause_type)

    return [
        ClauseResponse(
            clause_id=c.clause_id,
            clause_type=c.clause_type.value if hasattr(c.clause_type, "value") else str(c.clause_type),
            heading=c.heading,
            section_number=c.section_number,
            cross_reference_ids=c.cross_reference_ids,
        )
        for c in clauses
    ]


@router.get("/{document_id}/bindings", response_model=list[BindingResponse])
async def get_bindings(
    document_id: str,
    state: Annotated[AppState, Depends(get_state)],
) -> list[BindingResponse]:
    """Retrieve all bindings (definitions + aliases) for a contract."""
    contract = state.trust_graph.get_contract(document_id)
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Contract {document_id} not found")

    bindings = state.trust_graph.get_bindings_by_document(document_id)

    return [
        BindingResponse(
            binding_id=b.binding_id,
            binding_type=b.binding_type.value if hasattr(b.binding_type, "value") else str(b.binding_type),
            term=b.term,
            resolves_to=b.resolves_to,
            source_fact_id=b.source_fact_id,
            document_id=b.document_id,
            scope=b.scope.value if hasattr(b.scope, "value") else str(b.scope),
        )
        for b in bindings
    ]


class GraphNodeResponse(BaseModel):
    """A node in the TrustGraph context visualization."""

    id: str
    type: str  # "contract", "clause", "fact", "binding", "cross_reference"
    label: str
    metadata: dict = Field(default_factory=dict)


class GraphEdgeResponse(BaseModel):
    """An edge in the TrustGraph context visualization."""

    source: str
    target: str
    relationship: str  # "contains", "references", "binds_to", "cross_references"
    label: str = ""


class TrustGraphResponse(BaseModel):
    """Full TrustGraph context for a document — nodes + edges."""

    document_id: str
    title: str
    summary: dict
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]


@router.get("/{document_id}/graph", response_model=TrustGraphResponse)
async def get_trust_graph(
    document_id: str,
    state: Annotated[AppState, Depends(get_state)],
) -> TrustGraphResponse:
    """Get the full TrustGraph context for a document.

    Returns a graph structure with nodes (contract, clauses, facts, bindings,
    cross-references) and edges (containment, references, bindings).
    This powers the TrustGraph visualization.
    """
    contract = state.trust_graph.get_contract(document_id)
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Contract {document_id} not found")

    facts = state.trust_graph.get_facts_by_document(document_id)
    clauses = state.trust_graph.get_clauses_by_document(document_id)
    bindings = state.trust_graph.get_bindings_by_document(document_id)
    xrefs = state.trust_graph.get_cross_references_by_document(document_id)

    nodes: list[GraphNodeResponse] = []
    edges: list[GraphEdgeResponse] = []

    # Count by type for summary
    fact_type_counts: dict[str, int] = {}
    for f in facts:
        t = f.fact_type.value if hasattr(f.fact_type, "value") else str(f.fact_type)
        fact_type_counts[t] = fact_type_counts.get(t, 0) + 1

    clause_type_counts: dict[str, int] = {}
    for c in clauses:
        t = c.clause_type.value if hasattr(c.clause_type, "value") else str(c.clause_type)
        clause_type_counts[t] = clause_type_counts.get(t, 0) + 1

    binding_type_counts: dict[str, int] = {}
    for b in bindings:
        t = b.binding_type.value if hasattr(b.binding_type, "value") else str(b.binding_type)
        binding_type_counts[t] = binding_type_counts.get(t, 0) + 1

    summary = {
        "total_facts": len(facts),
        "total_clauses": len(clauses),
        "total_bindings": len(bindings),
        "total_cross_references": len(xrefs),
        "fact_types": fact_type_counts,
        "clause_types": clause_type_counts,
        "binding_types": binding_type_counts,
    }

    # Contract node (root)
    nodes.append(GraphNodeResponse(
        id=document_id,
        type="contract",
        label=contract.title,
        metadata={
            "file_format": contract.file_format,
            "word_count": contract.word_count,
            "parties": contract.parties,
            "file_hash": contract.file_hash,
        },
    ))

    # Clause nodes + edges to contract
    for c in clauses:
        nodes.append(GraphNodeResponse(
            id=c.clause_id,
            type="clause",
            label=c.heading,
            metadata={
                "clause_type": c.clause_type.value if hasattr(c.clause_type, "value") else str(c.clause_type),
                "section_number": c.section_number,
                "contained_fact_count": len(c.contained_fact_ids),
                "cross_reference_count": len(c.cross_reference_ids),
            },
        ))
        edges.append(GraphEdgeResponse(
            source=document_id,
            target=c.clause_id,
            relationship="contains",
            label=c.clause_type.value if hasattr(c.clause_type, "value") else "",
        ))

        # Edges from clause to its contained facts
        for fid in c.contained_fact_ids:
            edges.append(GraphEdgeResponse(
                source=c.clause_id,
                target=fid,
                relationship="contains",
                label="clause_text",
            ))

    # Fact nodes (limit to non-clause_text for readability, include clause_text count)
    fact_ids_in_graph = set()
    for f in facts:
        ft = f.fact_type.value if hasattr(f.fact_type, "value") else str(f.fact_type)
        # Include all fact types in the graph
        nodes.append(GraphNodeResponse(
            id=f.fact_id,
            type="fact",
            label=f.value[:80] + ("..." if len(f.value) > 80 else ""),
            metadata={
                "fact_type": ft,
                "entity_type": f.entity_type.value if f.entity_type and hasattr(f.entity_type, "value") else None,
                "char_start": f.evidence.char_start,
                "char_end": f.evidence.char_end,
                "location_hint": f.evidence.location_hint,
            },
        ))
        fact_ids_in_graph.add(f.fact_id)
        edges.append(GraphEdgeResponse(
            source=document_id,
            target=f.fact_id,
            relationship="contains",
            label=ft,
        ))

    # Binding nodes + edges
    for b in bindings:
        nodes.append(GraphNodeResponse(
            id=b.binding_id,
            type="binding",
            label=f"{b.term} → {b.resolves_to[:50]}",
            metadata={
                "binding_type": b.binding_type.value if hasattr(b.binding_type, "value") else str(b.binding_type),
                "term": b.term,
                "resolves_to": b.resolves_to,
                "scope": b.scope.value if hasattr(b.scope, "value") else str(b.scope),
            },
        ))
        # Edge from source fact to binding
        if b.source_fact_id and b.source_fact_id in fact_ids_in_graph:
            edges.append(GraphEdgeResponse(
                source=b.source_fact_id,
                target=b.binding_id,
                relationship="binds_to",
                label=b.term,
            ))
        # Edge from binding to document
        edges.append(GraphEdgeResponse(
            source=document_id,
            target=b.binding_id,
            relationship="defines",
            label=b.term,
        ))

    # Cross-reference nodes + edges
    for x in xrefs:
        nodes.append(GraphNodeResponse(
            id=x.reference_id,
            type="cross_reference",
            label=f"→ {x.target_reference}",
            metadata={
                "reference_type": x.reference_type.value if hasattr(x.reference_type, "value") else str(x.reference_type),
                "effect": x.effect.value if hasattr(x.effect, "value") else str(x.effect),
                "context": x.context[:100],
                "resolved": x.resolved,
            },
        ))
        # Edge from source clause to cross-reference
        edges.append(GraphEdgeResponse(
            source=x.source_clause_id,
            target=x.reference_id,
            relationship="cross_references",
            label=x.effect.value if hasattr(x.effect, "value") else "",
        ))
        # Edge to target clause if resolved
        if x.target_clause_id:
            edges.append(GraphEdgeResponse(
                source=x.reference_id,
                target=x.target_clause_id,
                relationship="references",
                label=x.target_reference,
            ))

    return TrustGraphResponse(
        document_id=document_id,
        title=contract.title,
        summary=summary,
        nodes=nodes,
        edges=edges,
    )


@router.get("/{document_id}/clauses/gaps", response_model=list[GapResponse])
async def get_clause_gaps(
    document_id: str,
    state: Annotated[AppState, Depends(get_state)],
) -> list[GapResponse]:
    """Retrieve missing mandatory facts across all clauses in a contract."""
    contract = state.trust_graph.get_contract(document_id)
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Contract {document_id} not found")

    missing_slots = state.trust_graph.get_missing_slots_by_document(document_id)
    clauses = state.trust_graph.get_clauses_by_document(document_id)
    clause_lookup = {c.clause_id: c for c in clauses}

    return [
        GapResponse(
            clause_id=s.clause_id,
            clause_type=(
                clause_lookup[s.clause_id].clause_type.value
                if s.clause_id in clause_lookup
                and hasattr(clause_lookup[s.clause_id].clause_type, "value")
                else "unknown"
            ),
            fact_spec_name=s.fact_spec_name,
            required=s.required,
            status=s.status.value if hasattr(s.status, "value") else str(s.status),
        )
        for s in missing_slots
    ]
