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

## 4. Clause Structure Analysis

### Decision: Hybrid pattern matching + LLM classification with configurable type registry

Contracts are not flat text — they are structured into clauses, and each
clause has internal structure: cross-references to other sections, mandatory
facts (e.g., a termination clause should have a notice period), and entity
aliasing patterns.

**Clause identification approach**:
1. **Heading-based detection** (deterministic): Parse section headings and
   numbering patterns (§12.1, Article XII, Section 3.2.1) to identify clause
   boundaries. This is the primary method and covers ~80% of clauses.
2. **LLM-assisted classification** (non-deterministic): For clauses with
   ambiguous headings or no headings, use LLM to classify the clause type
   based on content. Confidence score attached.

**Cross-reference extraction approach**:
- Regex patterns for section references: `§\d+(\.\d+)*`, `Section \d+`,
  `clause \d+(\.\d+)*(\([a-z]\))?`, `Appendix [A-Z]`, `Schedule [A-Z0-9]+`
- Resolution: Match extracted references to known clause section_numbers
  within the same document. Unresolvable references flagged but not guessed.
- Effect classification: LLM-assisted — given the surrounding context, what
  is the effect of this reference? (modifies, overrides, conditions, etc.)

**Entity aliasing detection**:
- Regex patterns for common alias introductions:
  - `"(.+?),?\s+hereinafter\s+referred\s+to\s+as\s+'(.+?)'"`
  - `"(.+?)\s+\(the\s+'(.+?)'\)"`
  - `"(.+?),?\s+hereafter\s+'(.+?)'"`
- These produce Binding records (same as definition resolution).

**Mandatory fact extraction per clause type**:
- The Clause Type Registry defines expected facts per type (see truth-model.md
  §1b). After classifying a clause, the extractor searches within the clause
  for the expected entity types.
- Missing mandatory facts are flagged as completeness gaps (inferences, not
  errors — the clause may intentionally omit them).

**Registry configurability**:
- Default registry ships with 14 clause types and their mandatory/optional
  fact schemas (see truth-model.md).
- Organizations can extend via `config/clause_types.yaml` — add custom types,
  modify mandatory facts, add industry-specific clause types.

**Open question resolved**: Should cross-reference resolution be eager or lazy?
→ **Eager within the same document** (resolve all internal references during
parsing). Lazy for cross-document references (deferred to Phase 2 when
Contract Graph is available).

## 5. LLM Integration

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

## 6. Storage: TrustGraph

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

## 7. API Framework

### Decision: FastAPI

**Rationale**: Async-native, automatic OpenAPI docs, Pydantic integration
(same models used in the API and in the backend), lightweight. The Word
Add-in communicates with this server over localhost HTTP.

## 8. Word Copilot

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

## 9. Configuration

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

  clause_types:
    registry: "config/clause_types.yaml"  # Configurable per organization
    custom_types_enabled: true

  logging:
    level: "INFO"
    audit_log: true
```

## 10. Testing Strategy — TDD

All development follows **Test-Driven Development (TDD)**: Red → Green →
Refactor. Tests are written before implementation. No feature is complete
until all its tests pass.

### Test Categories

| Category | Location | Scope | Dependencies |
|----------|----------|-------|-------------|
| **Unit tests** | `tests/unit/` | Single module in isolation | Mock all externals (LLM, DB, file system) |
| **Integration tests** | `tests/integration/` | Multiple modules together | Real SQLite (in-memory), real parsers, mock LLM |
| **Contract tests** | `tests/contract/` | API endpoints vs. spec | FastAPI TestClient, mock backend |
| **Benchmark tests** | `tests/benchmark/` | Accuracy & performance | Real contracts, real LLM (on demand) |

### Test Infrastructure

- **pytest** with pytest-asyncio, pytest-cov
- **respx** for HTTP mocking (LLM API calls)
- **factory-boy** for test data factories (Fact, Binding, Inference, etc.)
- **Test fixtures**: Manually crafted contracts with known entities in
  `tests/fixtures/`
- **LLM mock**: Deterministic mock provider in `tests/mocks/llm_mock.py`
  that returns known responses for known prompts
- **Coverage threshold**: 90% enforced in CI

### Test Counts (per tasks.md)

| Phase | Unit | Integration | Contract | Total |
|-------|------|------------|----------|-------|
| Foundation | 14 | 0 | 1 | 15 |
| US1: Extraction | 9 | 2 | 1 | 12 |
| US2: Bindings | 2 | 1 | 1 | 4 |
| US3: Q&A | 6 | 3 | 1 | 10 |
| US4: Provenance | 2 | 1 | 1 | 4 |
| US5: Workspace | 2 | 2 | 1 | 5 |
| Copilot | 3 | 1 | 0 | 4 |
| Polish | 2 | 1 | 0 | 3 |
| **Total** | **40** | **11** | **6** | **57** |

### Benchmark: COBench v0.1

- 20 annotated procurement contracts
- 100 questions with ground-truth answers
- Measures: Precision@N, Recall@N, MRR, NDCG, confidence calibration
- Not part of CI — run on demand and before releases

## 11. Open Questions (Resolved)

| Question | Resolution |
|----------|-----------|
| Should clause classification use LLM or rules? | Hybrid: spaCy patterns for detection, LLM for classification of ambiguous cases |
| How to handle multi-page tables in PDF? | pdfplumber's table_settings with custom row merging |
| What confidence does the inference engine assign to "not found"? | No confidence score — "not found" is a fact about the search, not an inference |
| How does the Copilot handle slow responses (>5s)? | Streaming — partial results displayed as they arrive |
