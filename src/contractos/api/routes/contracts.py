"""Contract upload and retrieval endpoints."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field

from contractos.api.deps import AppState, get_state
from contractos.models.document import Contract

router = APIRouter(prefix="/contracts", tags=["contracts"])


class ContractResponse(BaseModel):
    """Response after uploading or retrieving a contract."""

    document_id: str
    title: str
    file_format: str
    parties: list[str]
    page_count: int
    word_count: int
    fact_count: int = 0


class ContractListResponse(BaseModel):
    """Response for listing contracts in a workspace."""

    contracts: list[ContractResponse]
    total: int


@router.post("/upload", response_model=ContractResponse, status_code=201)
async def upload_contract(
    file: UploadFile,
    state: Annotated[AppState, Depends(get_state)],
) -> ContractResponse:
    """Upload a contract document (docx or pdf) for indexing."""
    if file.filename is None:
        raise HTTPException(status_code=400, detail="Filename required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("docx", "pdf"):
        raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}. Use docx or pdf.")

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    doc_id = f"doc-{uuid.uuid4().hex[:12]}"
    now = datetime.now()

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

    # TODO: Phase 3 will trigger async fact extraction here

    return ContractResponse(
        document_id=doc_id,
        title=contract.title,
        file_format=ext,
        parties=[],
        page_count=0,
        word_count=0,
        fact_count=0,
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
    return ContractResponse(
        document_id=contract.document_id,
        title=contract.title,
        file_format=contract.file_format,
        parties=contract.parties,
        page_count=contract.page_count,
        word_count=contract.word_count,
        fact_count=fact_count,
    )
