# Data Model: Single-Contract Intelligence

**Phase 1 — Entity Definitions and Relationships**

## Entity Relationship Overview

```
Contract ──── 1:N ──── Fact
    │                    │
    │                    └── 1:N ── FactEvidence
    │
    ├── 1:N ──── Binding
    │               │
    │               └── M:1 ── Fact (source_fact)
    │
    ├── 1:N ──── Inference
    │               │
    │               ├── M:N ── Fact (supporting_facts)
    │               └── M:N ── Binding (supporting_bindings)
    │
    └── 1:N ──── ReasoningSession
                    │
                    ├── 1:1 ── Query
                    └── 1:1 ── QueryResult
                                  │
                                  ├── 1:N ── Fact (referenced)
                                  ├── 1:N ── Inference (generated)
                                  └── 1:1 ── ProvenanceChain

Workspace ── 1:N ── Contract (indexed_documents)
    │
    └── 1:N ──── ReasoningSession
```

---

## Core Entities

### Contract

```python
class Contract(BaseModel):
    """Metadata for an indexed contract document."""
    document_id: str             # UUID, globally unique
    title: str                   # Extracted or filename-derived
    file_path: str               # Local path to the source document
    file_format: Literal["docx", "pdf"]
    file_hash: str               # SHA-256 of file contents (change detection)
    parties: list[str]           # Extracted party names
    effective_date: date | None  # If extractable
    page_count: int
    word_count: int
    indexed_at: datetime
    last_parsed_at: datetime
    extraction_version: str      # Version of extraction pipeline
```

### Fact

```python
class FactType(str, Enum):
    TEXT_SPAN = "text_span"
    ENTITY = "entity"
    CLAUSE = "clause"
    TABLE_CELL = "table_cell"
    HEADING = "heading"
    METADATA = "metadata"
    STRUCTURAL = "structural"

class EntityType(str, Enum):
    PARTY = "party"
    DATE = "date"
    MONEY = "money"
    PRODUCT = "product"
    LOCATION = "location"
    DURATION = "duration"
    SECTION_REF = "section_ref"

class FactEvidence(BaseModel):
    """Precise location of a fact in a document."""
    document_id: str
    text_span: str               # Exact text
    char_start: int              # Start offset
    char_end: int                # End offset
    location_hint: str           # Human-readable: "§5.2, paragraph 3"
    structural_path: str         # Machine-readable: "body > section[5] > para[3]"
    page_number: int | None      # For PDFs

class Fact(BaseModel):
    """An immutable, source-addressable claim extracted from document text."""
    fact_id: str                 # UUID
    fact_type: FactType
    entity_type: EntityType | None  # Only if fact_type == ENTITY
    value: str                   # The extracted content
    evidence: FactEvidence
    extraction_method: str       # "docx_parser_v1", "pdf_parser_v1"
    extracted_at: datetime
```

### Binding

```python
class BindingType(str, Enum):
    DEFINITION = "definition"
    ASSIGNMENT = "assignment"
    INCORPORATION = "incorporation"
    DELEGATION = "delegation"
    SCOPE_LIMITATION = "scope_limitation"

class BindingScope(str, Enum):
    CONTRACT = "contract"
    CONTRACT_FAMILY = "contract_family"  # Phase 2
    REPOSITORY = "repository"            # Phase 3

class Binding(BaseModel):
    """An explicitly stated semantic mapping in a contract."""
    binding_id: str              # UUID
    binding_type: BindingType
    term: str                    # The defined term
    resolves_to: str             # What it resolves to
    source_fact_id: str          # FK → Fact (the definition clause)
    document_id: str             # Which document this binding comes from
    scope: BindingScope          # Default: CONTRACT in Phase 1
    is_overridden_by: str | None # FK → Binding (if superseded)
```

### Inference

```python
class InferenceType(str, Enum):
    OBLIGATION = "obligation"
    COVERAGE = "coverage"
    SIMILARITY = "similarity"
    ENTITY_RESOLUTION = "entity_resolution"
    SCOPE_DETERMINATION = "scope_determination"
    NEGATION = "negation"        # "This contract does NOT contain X"

class Inference(BaseModel):
    """A probabilistic derived claim combining facts and bindings."""
    inference_id: str            # UUID
    inference_type: InferenceType
    claim: str                   # Human-readable statement
    supporting_fact_ids: list[str]     # FK → Fact
    supporting_binding_ids: list[str]  # FK → Binding
    reasoning_chain: str         # Step-by-step explanation
    confidence: float            # 0.0 – 1.0
    confidence_basis: str        # Why this confidence level
    generated_by: str            # "document_agent_v1"
    generated_at: datetime
    document_id: str             # Which document(s) this inference is about
    query_id: str | None         # Which query generated this inference
```

### Opinion (Phase 1: schema only, not generated)

```python
class OpinionType(str, Enum):
    RISK_ASSESSMENT = "risk_assessment"
    COMPLIANCE_CHECK = "compliance_check"
    BENCHMARK_COMPARISON = "benchmark_comparison"
    RECOMMENDATION = "recommendation"

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class Opinion(BaseModel):
    """A contextual judgment — never persisted as truth."""
    opinion_id: str
    opinion_type: OpinionType
    judgment: str
    supporting_inference_ids: list[str]
    supporting_fact_ids: list[str]
    role_context: str
    severity: Severity
    generated_at: datetime
    # Not persisted in TrustGraph — computed on demand
```

---

## Workspace & Session Entities

### Workspace

```python
class Workspace(BaseModel):
    """Persistent user context for ContractOS."""
    workspace_id: str            # UUID
    name: str                    # User-assigned or auto-generated
    indexed_documents: list[str] # document_ids
    created_at: datetime
    last_accessed_at: datetime
    settings: dict               # User preferences
```

### ReasoningSession

```python
class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"

class ReasoningSession(BaseModel):
    """A single query lifecycle."""
    session_id: str              # UUID
    workspace_id: str            # FK → Workspace
    query: "Query"
    result: "QueryResult | None"
    status: SessionStatus
    started_at: datetime
    completed_at: datetime | None
    document_ids: list[str]      # Which documents were in scope
```

### Query & QueryResult

```python
class QueryScope(str, Enum):
    SINGLE_DOCUMENT = "single_document"
    DOCUMENT_FAMILY = "document_family"  # Phase 2
    REPOSITORY = "repository"            # Phase 3

class Query(BaseModel):
    """A user's natural language question."""
    query_id: str                # UUID
    text: str                    # Raw question text
    scope: QueryScope
    target_document_ids: list[str]  # Which documents to query
    submitted_at: datetime

class ProvenanceNode(BaseModel):
    """A single node in the provenance chain."""
    node_type: Literal["fact", "binding", "inference", "external", "reasoning"]
    reference_id: str            # FK → Fact, Binding, or Inference
    summary: str                 # Human-readable summary
    document_location: str | None  # Where in the document (for facts)

class ProvenanceChain(BaseModel):
    """Full evidence chain for an answer."""
    nodes: list[ProvenanceNode]
    reasoning_summary: str       # Plain-English explanation

class QueryResult(BaseModel):
    """The answer to a query with full provenance."""
    result_id: str               # UUID
    query_id: str                # FK → Query
    answer: str                  # Human-readable answer
    answer_type: Literal["fact", "binding", "inference", "not_found"]
    confidence: float | None     # None for facts and not_found
    provenance: ProvenanceChain
    facts_referenced: list[str]  # fact_ids
    bindings_used: list[str]     # binding_ids
    inferences_generated: list[str]  # inference_ids
    generated_at: datetime
    generation_time_ms: int      # How long it took
```

---

## SQLite Schema

```sql
-- TrustGraph tables

CREATE TABLE contracts (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_format TEXT NOT NULL CHECK (file_format IN ('docx', 'pdf')),
    file_hash TEXT NOT NULL,
    parties TEXT NOT NULL,          -- JSON array
    effective_date TEXT,            -- ISO date
    page_count INTEGER NOT NULL,
    word_count INTEGER NOT NULL,
    indexed_at TEXT NOT NULL,       -- ISO datetime
    last_parsed_at TEXT NOT NULL,
    extraction_version TEXT NOT NULL
);

CREATE TABLE facts (
    fact_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES contracts(document_id),
    fact_type TEXT NOT NULL,
    entity_type TEXT,
    value TEXT NOT NULL,
    text_span TEXT NOT NULL,
    char_start INTEGER NOT NULL,
    char_end INTEGER NOT NULL,
    location_hint TEXT NOT NULL,
    structural_path TEXT NOT NULL,
    page_number INTEGER,
    extraction_method TEXT NOT NULL,
    extracted_at TEXT NOT NULL
);

CREATE INDEX idx_facts_document ON facts(document_id);
CREATE INDEX idx_facts_type ON facts(fact_type);
CREATE INDEX idx_facts_entity_type ON facts(entity_type);
CREATE INDEX idx_facts_value ON facts(value);

CREATE TABLE bindings (
    binding_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES contracts(document_id),
    binding_type TEXT NOT NULL,
    term TEXT NOT NULL,
    resolves_to TEXT NOT NULL,
    source_fact_id TEXT NOT NULL REFERENCES facts(fact_id),
    scope TEXT NOT NULL DEFAULT 'contract',
    is_overridden_by TEXT REFERENCES bindings(binding_id)
);

CREATE INDEX idx_bindings_document ON bindings(document_id);
CREATE INDEX idx_bindings_term ON bindings(term);

CREATE TABLE inferences (
    inference_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    inference_type TEXT NOT NULL,
    claim TEXT NOT NULL,
    supporting_fact_ids TEXT NOT NULL,    -- JSON array
    supporting_binding_ids TEXT NOT NULL, -- JSON array
    reasoning_chain TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    confidence_basis TEXT NOT NULL,
    generated_by TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    query_id TEXT
);

CREATE INDEX idx_inferences_document ON inferences(document_id);
CREATE INDEX idx_inferences_confidence ON inferences(confidence);

-- Workspace tables

CREATE TABLE workspaces (
    workspace_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    indexed_documents TEXT NOT NULL, -- JSON array of document_ids
    created_at TEXT NOT NULL,
    last_accessed_at TEXT NOT NULL,
    settings TEXT NOT NULL DEFAULT '{}'  -- JSON
);

CREATE TABLE reasoning_sessions (
    session_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
    query_text TEXT NOT NULL,
    query_scope TEXT NOT NULL,
    target_document_ids TEXT NOT NULL, -- JSON array
    answer TEXT,
    answer_type TEXT,
    confidence REAL,
    provenance TEXT,                   -- JSON (ProvenanceChain)
    facts_referenced TEXT,            -- JSON array
    bindings_used TEXT,               -- JSON array
    inferences_generated TEXT,        -- JSON array
    status TEXT NOT NULL DEFAULT 'active',
    started_at TEXT NOT NULL,
    completed_at TEXT,
    generation_time_ms INTEGER
);

CREATE INDEX idx_sessions_workspace ON reasoning_sessions(workspace_id);
CREATE INDEX idx_sessions_status ON reasoning_sessions(status);
```

---

## Relationships Summary

| From | To | Relationship | Cardinality |
|------|-----|-------------|-------------|
| Contract | Fact | contains | 1:N |
| Contract | Binding | defines | 1:N |
| Binding | Fact | grounded by | M:1 |
| Inference | Fact | supported by | M:N |
| Inference | Binding | uses | M:N |
| Workspace | Contract | indexes | M:N |
| Workspace | ReasoningSession | contains | 1:N |
| ReasoningSession | QueryResult | produces | 1:1 |
| QueryResult | ProvenanceChain | includes | 1:1 |
| ProvenanceChain | ProvenanceNode | composed of | 1:N |
