# API Contract: ContractOS Local Server

**Base URL**: `http://127.0.0.1:8742/api/v1`
**Protocol**: HTTP/REST + SSE (Server-Sent Events for streaming)
**Auth**: None (localhost only in Phase 1)

---

## Document Endpoints

### POST /documents

Upload and parse a contract document.

**Request**:
```
Content-Type: multipart/form-data

file: <binary>             # .docx or .pdf file
workspace_id: string       # optional — auto-creates if absent
```

**Response** (202 Accepted):
```json
{
  "document_id": "d-550e8400-e29b-41d4-a716-446655440000",
  "status": "parsing",
  "workspace_id": "w-123",
  "estimated_time_seconds": 15
}
```

**Errors**:
- 400: Unsupported file format
- 413: File too large (>50MB)
- 422: Corrupted or unreadable file

### GET /documents/{document_id}

Get document metadata and parsing status.

**Response** (200 OK):
```json
{
  "document_id": "d-550e8400",
  "title": "Dell IT Services Agreement 2024",
  "file_format": "docx",
  "parties": ["ClientCo Ltd", "Dell Technologies Inc"],
  "effective_date": "2024-01-15",
  "page_count": 32,
  "word_count": 14520,
  "status": "indexed",
  "fact_count": 247,
  "binding_count": 18,
  "indexed_at": "2025-02-09T10:30:00Z"
}
```

### GET /documents/{document_id}/facts

List all facts extracted from a document.

**Query parameters**:
- `fact_type` (optional): Filter by type (entity, clause, table_cell, etc.)
- `entity_type` (optional): Filter by entity type (party, date, money, etc.)
- `limit` (optional): Pagination limit (default 100)
- `offset` (optional): Pagination offset

**Response** (200 OK):
```json
{
  "document_id": "d-550e8400",
  "facts": [
    {
      "fact_id": "f-001",
      "fact_type": "entity",
      "entity_type": "party",
      "value": "Dell Technologies Inc",
      "evidence": {
        "text_span": "Dell Technologies Inc (\"Supplier\")",
        "char_start": 245,
        "char_end": 289,
        "location_hint": "§1.1, paragraph 1",
        "structural_path": "body > section[1] > para[1]"
      }
    }
  ],
  "total": 247,
  "limit": 100,
  "offset": 0
}
```

### GET /documents/{document_id}/bindings

List all bindings resolved in a document.

**Response** (200 OK):
```json
{
  "document_id": "d-550e8400",
  "bindings": [
    {
      "binding_id": "b-001",
      "binding_type": "definition",
      "term": "Supplier",
      "resolves_to": "Dell Technologies Inc and its affiliates",
      "source_fact_id": "f-012",
      "scope": "contract"
    }
  ],
  "total": 18
}
```

---

## Query Endpoints

### POST /query

Ask a question about a document.

**Request**:
```json
{
  "text": "Does this contract indemnify the buyer for data breach?",
  "document_ids": ["d-550e8400"],
  "workspace_id": "w-123",
  "stream": true
}
```

**Response** (if `stream: false`, 200 OK):
```json
{
  "session_id": "s-789",
  "answer": "Yes. §12.1 establishes an indemnification obligation...",
  "answer_type": "inference",
  "confidence": 0.85,
  "provenance": {
    "nodes": [
      {
        "node_type": "fact",
        "reference_id": "f-089",
        "summary": "§12.1 contains indemnification clause covering 'losses arising from unauthorized access to Confidential Information'",
        "document_location": "§12.1, characters 8901-9234"
      },
      {
        "node_type": "binding",
        "reference_id": "b-008",
        "summary": "'Confidential Information' defined in §1.8 as including 'all data shared under this Agreement'",
        "document_location": "§1.8"
      },
      {
        "node_type": "inference",
        "reference_id": "i-001",
        "summary": "Data breach is a form of unauthorized access to confidential information; therefore §12.1's indemnification applies",
        "document_location": null
      }
    ],
    "reasoning_summary": "§12.1 indemnifies against 'losses arising from unauthorized access to Confidential Information'. §1.8 defines Confidential Information broadly. A data breach constitutes unauthorized access to such information. Therefore, the indemnification clause covers data breach scenarios."
  },
  "generation_time_ms": 3200
}
```

**Response** (if `stream: true`, 200 OK, SSE):
```
event: status
data: {"phase": "searching_facts", "message": "Searching TrustGraph..."}

event: partial
data: {"answer_so_far": "Yes. §12.1 establishes..."}

event: provenance
data: {"node": {"node_type": "fact", "reference_id": "f-089", ...}}

event: complete
data: {"session_id": "s-789", "answer": "...", "confidence": 0.85, ...}
```

**Errors**:
- 400: Empty query or missing document_ids
- 404: Document not found or not indexed
- 503: LLM service unavailable (facts/bindings still accessible)

### GET /query/sessions/{session_id}

Retrieve a previous reasoning session.

**Response** (200 OK): Same structure as POST /query (non-streaming).

---

## Workspace Endpoints

### POST /workspaces

Create a new workspace.

**Request**:
```json
{
  "name": "Dell Contracts Review"
}
```

**Response** (201 Created):
```json
{
  "workspace_id": "w-123",
  "name": "Dell Contracts Review",
  "indexed_documents": [],
  "created_at": "2025-02-09T10:00:00Z"
}
```

### GET /workspaces/{workspace_id}

Get workspace details including indexed documents and session history.

**Response** (200 OK):
```json
{
  "workspace_id": "w-123",
  "name": "Dell Contracts Review",
  "indexed_documents": [
    {
      "document_id": "d-550e8400",
      "title": "Dell IT Services Agreement 2024",
      "status": "indexed"
    }
  ],
  "recent_sessions": [
    {
      "session_id": "s-789",
      "query_text": "Does this contract indemnify...",
      "answer_summary": "Yes. §12.1 establishes...",
      "confidence": 0.85,
      "completed_at": "2025-02-09T10:35:00Z"
    }
  ],
  "created_at": "2025-02-09T10:00:00Z",
  "last_accessed_at": "2025-02-09T10:35:00Z"
}
```

---

## Health & Config

### GET /health

**Response** (200 OK):
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "llm_provider": "claude",
  "llm_status": "connected",
  "storage": "sqlite",
  "documents_indexed": 3,
  "uptime_seconds": 3600
}
```

### GET /config

**Response** (200 OK):
```json
{
  "llm_provider": "claude",
  "llm_model": "claude-sonnet-4-20250514",
  "extraction_pipeline": ["docx_parser", "pdf_parser"],
  "storage_backend": "sqlite",
  "max_document_pages": 200
}
```
