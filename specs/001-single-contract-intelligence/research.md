# Research: Single-Contract Intelligence

**Phase 0 — Technology Decisions**

## 1. Document Parsing: Word (.docx)

### Decision: python-docx + custom table extractor

**Options evaluated:**
- **python-docx** — mature, well-maintained, handles paragraphs, tables,
  headers, styles. Does NOT handle embedded images or complex formatting.
- **docx2python** — extracts nested structures but less control over offsets.
- **mammoth** — converts to HTML; lossy for structural analysis.

**Decision rationale**: python-docx gives us direct access to the document XML
structure, which is essential for character offset tracking and structural path
generation. We need precise `char_start` / `char_end` for every fact.

**Custom work needed**: Table extraction with row/column metadata. python-docx
handles tables but we need to normalize multi-row headers, merged cells, and
nested tables into flat fact structures.

## 2. Document Parsing: PDF

### Decision: PyMuPDF (fitz) primary + pdfplumber for tables

**Options evaluated:**
- **PyMuPDF (fitz)** — fast, precise character positions, handles most PDFs.
  Table extraction is basic.
- **pdfplumber** — excellent table extraction, based on pdfminer. Slower but
  more accurate for tabular data.
- **camelot** — table-focused. Dependency-heavy (Ghostscript, OpenCV).
- **unstructured** — high-level, opinionated. Good for "just works" but less
  control over offsets.

**Decision rationale**: Use PyMuPDF for text extraction with character offsets,
and pdfplumber specifically for table extraction. This combination gives us
both speed and table accuracy.

**Known limitation**: Scanned PDFs (image-only) will not work. Phase 1 returns
a clear error message. OCR support is deferred to a future release.

## 3. Named Entity Recognition

### Decision: spaCy (en_core_web_lg) + custom contract patterns

**Options evaluated:**
- **spaCy** — fast, local, good base NER. Needs customization for contract
  entities (clause types, legal terms).
- **Stanza (Stanford NLP)** — more accurate in benchmarks but slower.
- **LLM-based extraction** — highest accuracy but expensive for bulk
  extraction and non-deterministic.

**Decision rationale**: spaCy for base NER (ORG, PERSON, DATE, MONEY, GPE)
plus custom pattern matchers for contract-specific entities (clause headings,
defined terms, section references). This keeps extraction deterministic and
fast, per FR-013.

**Custom patterns needed**:
- Definition clause patterns: `"X" shall mean Y`, `"X" refers to Y`
- Section reference patterns: `§12.1`, `Section 12.1`, `Article XII`
- Duration patterns: `thirty (30) days`, `ninety (90) calendar days`
- Renewal/termination patterns: specific clause type signatures

## 4. LLM Integration

### Decision: Claude (Anthropic SDK) as default; pluggable via interface

**Architecture**:
```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, context: list[str]) -> str: ...
    @abstractmethod
    async def classify(self, text: str, categories: list[str]) -> str: ...

class ClaudeProvider(LLMProvider):
    # Uses anthropic SDK
    # Model: claude-sonnet-4-20250514 (default, configurable)
```

**LLM is used for**:
- Clause classification (given extracted text, what type of clause?)
- Inference generation (given facts + bindings + query, what can we infer?)
- Answer synthesis (given facts + inferences, generate human-readable answer)
- Confidence scoring (given evidence strength, estimate confidence)

**LLM is NOT used for**:
- Fact extraction (deterministic tool)
- Binding resolution (deterministic pattern matching)
- Character offset computation (document parser)

## 5. Storage: TrustGraph

### Decision: SQLite with well-defined schema

**Options evaluated:**
- **SQLite** — zero-config, local, fast for single-user. Schema can be
  migrated to PostgreSQL later.
- **DuckDB** — analytical workloads, columnar storage. Overkill for Phase 1.
- **PostgreSQL** — full-featured but requires server. Phase 1 is local.
- **Neo4j/graph DB** — natural for TrustGraph but heavyweight for local.

**Decision rationale**: SQLite is the right choice for Phase 1 (local
deployment, single user). The schema uses explicit foreign keys and indexes
that translate directly to PostgreSQL when we scale. We do NOT use SQLite's
limited graph features — instead, facts, bindings, and inferences are stored
as typed rows with explicit relationship columns.

## 6. API Framework

### Decision: FastAPI

**Rationale**: Async-native, automatic OpenAPI docs, Pydantic integration
(same models used in the API and in the backend), lightweight. The Word
Add-in communicates with this server over localhost HTTP.

## 7. Word Copilot

### Decision: Office Web Add-in (taskpane) with React

**Architecture**: A sidebar Add-in built with the Office JavaScript API.
The sidebar communicates with the local FastAPI server over `localhost`.

**Why not a VSTO add-in or COM add-in?**: Office Web Add-ins work across
platforms (Windows + Mac), are easier to develop, and align with Microsoft's
current direction.

**Capabilities in Phase 1**:
- Display Q&A interface in sidebar
- Send current document context (filename, selection) to the backend
- Display answers with provenance (expandable fact references)
- Navigate to document locations (using Office JS API)

**Deferred to Phase 2+**:
- In-document annotations
- Inline suggestions
- Redline generation

## 8. Configuration

### Decision: YAML configuration with Pydantic validation

```yaml
# config/default.yaml
contractos:
  llm:
    provider: "claude"
    model: "claude-sonnet-4-20250514"
    api_key_env: "ANTHROPIC_API_KEY"
    max_tokens: 4096
    temperature: 0.1

  extraction:
    pipeline:
      - "docx_parser"
      - "pdf_parser"
    spacy_model: "en_core_web_lg"

  storage:
    backend: "sqlite"
    path: "~/.contractos/trustgraph.db"

  workspace:
    auto_persist: true
    session_history_limit: 100

  server:
    host: "127.0.0.1"
    port: 8742
    cors_origins: ["https://localhost"]

  logging:
    level: "INFO"
    audit_log: true
```

## 9. Testing Strategy

**Unit tests**: Each tool tested independently with fixture contracts.
- FactExtractor: verify entity counts, offset accuracy, determinism
- BindingResolver: verify definition capture, scope assignment
- InferenceEngine: verify fact references, confidence range
- TrustGraph: verify CRUD, query, type enforcement

**Integration tests**: DocumentAgent end-to-end with real contracts.
- Parse → extract → resolve → query → verify answer + provenance

**Benchmark**: COBench v0.1
- 20 annotated procurement contracts
- 100 questions with ground-truth answers
- Measures: fact extraction precision, Q&A accuracy, confidence calibration

## 10. Open Questions (Resolved)

| Question | Resolution |
|----------|-----------|
| Should clause classification use LLM or rules? | Hybrid: spaCy patterns for detection, LLM for classification of ambiguous cases |
| How to handle multi-page tables in PDF? | pdfplumber's table_settings with custom row merging |
| What confidence does the inference engine assign to "not found"? | No confidence score — "not found" is a fact about the search, not an inference |
| How does the Copilot handle slow responses (>5s)? | Streaming — partial results displayed as they arrive |
