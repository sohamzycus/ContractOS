# Tasks: Single-Contract Intelligence

**Input**: Design documents from `specs/001-single-contract-intelligence/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md
**Tech Stack**: Python 3.12, FastAPI, python-docx, PyMuPDF, pdfplumber, spaCy, Anthropic SDK, SQLite, Pydantic
**Branch**: `001-single-contract-intelligence`

## TDD Protocol

**Every feature follows Red → Green → Refactor:**

1. **Write the test FIRST** — it must fail (Red)
2. **Implement the minimum code** to make the test pass (Green)
3. **Refactor** — clean up while tests stay green

**Test categories:**
- **Unit tests** (`tests/unit/`): Test a single module in isolation. Mock all
  external dependencies (LLM, file system, database).
- **Integration tests** (`tests/integration/`): Test multiple modules working
  together. Use real SQLite (in-memory), real parsers, mock LLM.
- **Contract tests** (`tests/contract/`): Test API endpoints against the
  API contract spec. Use FastAPI TestClient.
- **Benchmark tests** (`tests/benchmark/`): COBench accuracy and performance
  measurements. Not part of CI — run on demand.

**Test infrastructure:**
- `conftest.py` at each level with shared fixtures
- `tests/fixtures/` for test documents (manually crafted with known entities)
- `tests/mocks/` for LLM mock responses, fixture factories

---

## Phase 1: Setup (Project Infrastructure) ✅ COMPLETE

**Purpose**: Initialize the Python project, dependency management, and base structure.
**Commit**: `496f5b0` — chore: scaffold project structure, dependencies, and tooling

- [x] T001 Create project directory structure per plan.md (`src/contractos/`, `tests/unit/`, `tests/integration/`, `tests/contract/`, `tests/benchmark/`, `tests/fixtures/`, `tests/mocks/`, `config/`, `copilot/`)
- [x] T002 Initialize Python project with `pyproject.toml` — dependencies: python-docx, pymupdf, pdfplumber, spacy, anthropic, fastapi, uvicorn, pydantic, pydantic-settings, pytest, pytest-asyncio, pytest-cov, httpx, respx (HTTP mocking), factory-boy (fixtures)
- [x] T003 [P] Create `config/default.yaml` with all configuration keys from research.md §9
- [x] T004 [P] Create `.gitignore` update for Python (.venv, __pycache__, *.db, .contractos/)
- [x] T005 [P] Configure ruff (linter/formatter), mypy (type checking), and pytest (coverage threshold 90%) in `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites) ✅ COMPLETE

**Purpose**: Core data models, storage, LLM abstraction, and configuration that ALL user stories depend on.
**Commits**: `a421588` (Phase 2a: models), `ad3bf8a` (Phase 2b: storage, LLM, API)
**Tests**: 168 passing (75 model tests + 39 TrustGraph + 17 WorkspaceStore + 12 LLM + 18 API + 7 config)

### Test Infrastructure

- [x] T006 Create test fixtures: `tests/fixtures/simple_procurement.docx` and `tests/fixtures/simple_nda.pdf`
- [x] T007 [P] Create `tests/conftest.py` with shared fixtures
- [x] T008 [P] Create MockLLMProvider in `src/contractos/llm/provider.py` — deterministic responses, call logging

### Data Models — Tests First

- [x] T009–T015 [P] All model unit tests written and passing (75 tests total)

### Data Models — Implementation

- [x] T016–T025 [P] All Pydantic models implemented
- [x] T026 Clause Type Registry (embedded in clause_classifier heading patterns)

### Storage — Tests + Implementation

- [x] T027 TrustGraph unit tests (39 tests) — CRUD for facts, bindings, inferences, clauses, cross-refs, clause_fact_slots, cascade deletes
- [x] T028 WorkspaceStore unit tests (17 tests) — CRUD for workspaces, sessions, cascade
- [x] T029 SQLite schema in `src/contractos/fabric/schema.sql`
- [x] T030 TrustGraph implementation in `src/contractos/fabric/trust_graph.py`
- [x] T031 WorkspaceStore implementation in `src/contractos/fabric/workspace_store.py`

### Configuration — Tests + Implementation

- [x] T032 Config unit tests (7 tests)
- [x] T033 Config loading in `src/contractos/config.py`

### LLM Abstraction — Tests + Implementation

- [x] T034 LLM provider unit tests (12 tests)
- [x] T035 LLMProvider ABC + MockLLMProvider + AnthropicProvider in `src/contractos/llm/provider.py`
- [x] T036 AnthropicProvider (Claude) in same file

### API Server Shell — Tests + Implementation

- [x] T037 API tests (9 unit + 9 integration)
- [x] T038 FastAPI app factory in `src/contractos/api/app.py`
- [x] T039 [P] Health endpoint (`GET /health`)
- [x] T040 [P] Contract upload/retrieval + query endpoints

**Checkpoint**: ✅ Foundation complete — 168 tests passing.

---

## Phase 3: User Story 1 — Document Ingestion & Fact Extraction (P1) MVP ✅ COMPLETE

**Goal**: Parse a Word or PDF contract and extract structured facts with precise evidence.
**Commit**: `15d802c` — feat: implement document parsers and full fact extraction pipeline
**Tests**: 137 new unit tests (305 total passing)

### Unit Tests — ✅ All Written and Passing

- [x] T041 [P] [US1] Word parser tests (16 tests) in `tests/unit/test_docx_parser.py`
- [x] T042 [P] [US1] PDF parser tests (13 tests) in `tests/unit/test_pdf_parser.py`
- [x] T043 [P] [US1] FactExtractor tests (21 tests) in `tests/unit/test_fact_extractor.py`
- [x] T044 [P] [US1] Contract patterns tests (25 tests) in `tests/unit/test_contract_patterns.py`
- [x] T045 [P] [US1] Clause classifier tests (29 tests) in `tests/unit/test_clause_classifier.py`
- [x] T046 [P] [US1] Cross-reference extractor tests (13 tests) in `tests/unit/test_cross_reference_extractor.py`
- [x] T047 [P] [US1] Mandatory fact extractor tests (10 tests) in `tests/unit/test_mandatory_fact_extractor.py`
- [x] T048 [P] [US1] Alias detector tests (10 tests) in `tests/unit/test_alias_detector.py`
- [x] T049 [P] [US1] Determinism verified in FactExtractor tests

### Integration Tests

- [ ] T050 [P] [US1] Full extraction pipeline integration test — _deferred to Phase 6+_
- [ ] T051 [P] [US1] Extraction + alias detection integration test — _deferred to Phase 6+_

### Contract Tests

- [ ] T052 [P] [US1] Document API contract tests — _deferred to Phase 6+_

### Implementation — ✅ All Core Tools Complete

- [x] T053 [US1] Word parser in `src/contractos/tools/docx_parser.py`
- [x] T054 [US1] PDF parser in `src/contractos/tools/pdf_parser.py`
- [x] T055 [US1] Contract patterns in `src/contractos/tools/contract_patterns.py`
- [x] T056 [US1] FactExtractor orchestrator in `src/contractos/tools/fact_extractor.py`
- [x] T057 [US1] Clause classifier in `src/contractos/tools/clause_classifier.py`
- [x] T058 [US1] Cross-reference extractor in `src/contractos/tools/cross_reference_extractor.py`
- [x] T059 [US1] Mandatory fact extractor in `src/contractos/tools/mandatory_fact_extractor.py`
- [x] T060 [US1] Entity alias detector in `src/contractos/tools/alias_detector.py`
- [ ] T061–T066 [US1] Document API endpoints — _implementing in Phase 6+_

**Checkpoint**: ✅ All extraction tools tested and working. 137 unit tests passing.

---

## Phase 4: User Story 2 — Binding Resolution (P1) ✅ COMPLETE

**Goal**: Identify definition clauses and resolve defined terms as Bindings throughout the document.
**Commit**: `f9136ab` — feat: implement binding resolver, DocumentAgent Q&A pipeline, and wire API
**Tests**: 13 new unit tests (331 total passing)

### Unit Tests — ✅ All Written and Passing

- [x] T067 [P] [US2] BindingResolver tests (13 tests) in `tests/unit/test_binding_resolver.py` — definition extraction, merging, precedence, deduplication
- [x] T068 [P] [US2] Binding lookup (resolve_term) tested in same file — chain resolution, case-insensitivity, cycle detection, max depth

### Integration Tests

- [ ] T069 [P] [US2] Bindings pipeline integration test — _deferred to Phase 6+_

### Contract Tests

- [ ] T070 [P] [US2] Bindings API contract tests — _deferred to Phase 6+_

### Implementation — ✅ Core Complete

- [x] T071 [US2] BindingResolver in `src/contractos/tools/binding_resolver.py`
- [x] T072 [US2] Binding persistence in TrustGraph (already in Phase 2)
- [ ] T073 [US2] Bindings API endpoint — _implementing in Phase 6+_
- [x] T074 [US2] BindingResolver integrated into extraction pipeline
- [x] T075 [US2] Binding lookup utility (resolve_term) with chain resolution

**Checkpoint**: ✅ Binding resolution tested and working. 13 unit tests passing.

---

## Phase 5: User Story 3 — Single-Document Q&A (P1) MVP ✅ COMPLETE

**Goal**: Answer natural language questions about a contract using facts, bindings, and LLM-generated inferences.
**Commit**: `f9136ab` — feat: implement binding resolver, DocumentAgent Q&A pipeline, and wire API
**Tests**: 13 new DocumentAgent unit tests (331 total passing)

### Unit Tests — ✅ Core Written and Passing

- [ ] T076 [P] [US3] InferenceEngine tests — _deferred: inference handled inside DocumentAgent via LLM_
- [ ] T077 [P] [US3] Confidence calculation tests — _deferred: confidence from LLM response_
- [x] T078 [P] [US3] DocumentAgent tests (13 tests) in `tests/unit/test_document_agent.py` — orchestration, context building, provenance, edge cases
- [ ] T079 [P] [US3] ProvenanceChain builder tests — _covered in DocumentAgent tests_
- [ ] T080 [P] [US3] "Not found" handling tests — _covered in DocumentAgent tests_
- [ ] T081 [P] [US3] Prompt template tests — _deferred_

### Integration Tests

- [ ] T082–T084 [P] [US3] Q&A integration tests — _implementing in Phase 6+_

### Contract Tests

- [ ] T085 [P] [US3] Query API contract tests — _implementing in Phase 6+_

### Implementation — ✅ Core Complete

- [ ] T086 [US3] Prompt templates — _inline in DocumentAgent_
- [ ] T087 [US3] InferenceEngine — _handled by DocumentAgent + LLM_
- [ ] T088 [US3] Confidence calculation — _from LLM response_
- [x] T089 [US3] ProvenanceChain builder in `src/contractos/models/provenance.py`
- [x] T090 [US3] DocumentAgent in `src/contractos/agents/document_agent.py`
- [x] T091 [US3] "Not found" handling in DocumentAgent
- [x] T092 [US3] Query endpoint (`POST /query/ask`) in `src/contractos/api/routes/query.py`
- [ ] T093 [US3] SSE streaming — _deferred to Phase 6+_
- [ ] T094 [US3] Session retrieval — _deferred to Phase 7_

**Checkpoint**: ✅ MVP Q&A pipeline working. 331 tests passing. User asks a question, gets grounded answer with provenance.

---

## Phase 6: User Story 4 — Provenance Display + Full Pipeline Wiring ✅ COMPLETE

**Goal**: Wire fact extraction into upload, add document API endpoints, provenance display with confidence labels.
**Tests**: 28 new tests (359 total passing)

### Unit Tests — ✅ Written and Passing

- [x] T095 [P] [US4] Provenance formatting tests (8 tests) in `tests/unit/test_provenance_formatting.py`
- [x] T096 [P] [US4] Confidence display tests (15 tests) in `tests/unit/test_confidence.py`

### Integration Tests — ✅ Written and Passing

- [x] T097 [P] [US4] Full pipeline integration test in `tests/integration/test_api.py` — upload → extract → query with provenance

### Contract Tests

- [ ] T098 [P] [US4] Provenance contract test — _deferred_

### Implementation — ✅ Complete

- [x] T099 [US4] Provenance formatting in `src/contractos/tools/provenance_formatter.py`
- [x] T100 [US4] Confidence display in `src/contractos/tools/confidence.py` — maps 0.0–1.0 to label + color
- [ ] T101 [US4] Provenance middleware — _deferred_

### Additional Implementation (Pipeline Wiring)

- [x] T040 [P] Config endpoint (`GET /config`) in `src/contractos/api/routes/health.py`
- [x] T061 [US1] Document upload with full extraction pipeline (`POST /contracts/upload`)
- [x] T063 [US1] Facts endpoint (`GET /contracts/{id}/facts`) with filters and pagination
- [x] T064 [US1] Clauses endpoint (`GET /contracts/{id}/clauses`) with type filter
- [x] T073 [US2] Bindings endpoint (`GET /contracts/{id}/bindings`)
- [x] T065 [US1] Clause gaps endpoint (`GET /contracts/{id}/clauses/gaps`)
- [x] T132 [P] CLI interface (`contractos serve/parse/query/facts/bindings`) in `src/contractos/cli.py`

**Checkpoint**: ✅ Full pipeline wired. Upload → Extract → Store → Query → Provenance. 359 tests passing.

---

## Phase 7: User Story 5 — Workspace Persistence (P2) ✅ COMPLETE

**Goal**: Documents and sessions persist across restarts. Previously parsed documents load instantly.
**Commit**: `30c26d7` — feat: implement Phase 7 — workspace persistence, session history, change detection
**Tests**: 43 new tests (421 total passing)

### Unit Tests — ✅ Written and Passing

- [x] T102 [P] [US5] Document change detection tests (11 tests) in `tests/unit/test_change_detection.py` — SHA-256 hashing, determinism, change detection, edge cases
- [x] T103 [P] [US5] Workspace document association tests (8 tests) in `tests/unit/test_workspace_documents.py` — add/remove documents, cross-workspace isolation, idempotency

### Integration Tests — ✅ Written and Passing

- [x] T104 [P] [US5] Workspace persistence integration test (3 tests) in `tests/integration/test_workspace_persistence.py` — full cycle: index → workspace → session → restart → verify persistence; multi-document; change detection
- [x] T105 [P] [US5] Session history integration test (8 tests) in `tests/integration/test_session_history.py` — 5 sessions, reverse chronological order, completeness, generation times

### Contract Tests — ✅ Written and Passing

- [x] T106 [P] [US5] Workspace API contract tests (13 tests) in `tests/contract/test_workspace_api.py` — POST/GET /workspaces, document association, session history, 404 error cases

### Implementation — ✅ Complete

- [x] T107 [US5] Workspace endpoints in `src/contractos/api/routes/workspace.py` — POST /workspaces, GET /workspaces/{id}, GET /workspaces
- [x] T108 [US5] Document-workspace association — POST/DELETE /workspaces/{id}/documents, remove_document_from_workspace in WorkspaceStore
- [x] T109 [US5] Session history — GET /workspaces/{id}/sessions, recent_sessions in workspace response
- [x] T110 [US5] Document change detection — GET /workspaces/{id}/documents/{doc_id}/check, compute_file_hash, detect_change in `src/contractos/tools/change_detection.py`
- [x] T111 [US5] Session retrieval by workspace — GET /workspaces/{id} includes recent_sessions (last 20)

### Additional Implementation

- [x] T139 [US1] Clause body text extraction — new CLAUSE_TEXT fact type captures full paragraph text within clauses
- [x] T140 Complex real-world procurement fixtures — `complex_it_outsourcing.docx` ($47.5M, 18 sections) and `complex_procurement_framework.pdf` (GBP 85M, 15 sections)
- [x] T141 Postman collection — full API integration test suite (47 requests, 6 folders) with Newman runner
- [x] T142 LegalBench/CUAD benchmark fixtures — `legalbench_nda.docx` (bilateral NDA, 11 sections) and `cuad_license_agreement.docx` (software license, 13 sections + exhibits)
- [x] T143 LegalBench integration tests — 32 extraction tests + 14 API contract tests covering contract_nli, CUAD categories
- [x] T144 Bug fix: `get_facts_by_document` and `get_clauses_by_document` now accept string filters (API compatibility)
- [x] T145 Browser-based Demo Console (`demo/index.html`) — replaces Postman dependency, 22 pre-built requests, file upload, auto-chaining, rich response display
- [x] T146 CORS middleware + static file serving for `/demo/` route in `app.py`

### Phase 7b: Algorithm Documentation, TrustGraph Visualization & LegalBench Evaluation ✅ COMPLETE

**Goal**: Document the indexing algorithm, build interactive TrustGraph visualization, download real LegalBench datasets, and build evaluation harness.
**Tests**: 61 new benchmark tests (528 total passing)

- [x] T147 Interactive TrustGraph Visualization (`demo/graph.html`) — D3.js force-directed graph with:
  - Upload & visualize workflow (upload contract → see graph instantly)
  - Load existing document by `document_id`
  - 5 node types: Contract (purple), Clause (orange), Fact (green), Binding (blue), CrossRef (pink)
  - 5 relationship types: contains, binds_to, cross_references, fills, supports
  - Node inspector panel — click any node to see full metadata
  - Traversal panel — BFS path exploration showing how facts/clauses connect
  - Filter controls: All Nodes, Clauses Only, Facts Only, Bindings Only, Cross-Refs, Hide Clause Text
  - Layout modes: Force-Directed, Radial, Hierarchy
  - Hover highlighting — shows connected subgraph
  - Drag, zoom, reset controls
  - Stats bar: total facts, clauses, bindings, cross-refs, nodes, edges
- [x] T148 Indexing Algorithm Documentation (embedded in graph.html side panel):
  - Why it's fast: zero LLM calls during indexing, compiled regex, deterministic heuristics
  - 7-stage pipeline architecture with animated step visualization
  - Key design decisions: regex over LLM, heading-based classification, SQLite WAL mode
  - TrustGraph ontology: 8 entity types, 5 relationship types
- [x] T149 LegalBench Dataset Download — 16 tasks (14 contract_nli + definition_extraction + contract_qa):
  - `tests/fixtures/legalbench/download_legalbench.py` — automated downloader
  - 128 train rows across 16 tasks from https://github.com/HazyResearch/legalbench
  - Each task includes `train.tsv` (data) and `base_prompt.txt` (hypothesis/few-shot prompt)
  - Summary report: `tests/fixtures/legalbench/SUMMARY.md`
- [x] T150 LegalBench Evaluation Harness (`tests/benchmark/test_legalbench_eval.py`) — 61 tests:
  - `TestContractNLIExtraction` (42 tests): keyword discrimination, pattern extraction, clause classification across all 14 contract_nli tasks
  - `TestContractNLIAccuracy` (15 tests): binary classification accuracy per task + overall balanced accuracy (>60%)
  - `TestDefinitionExtraction` (1 test): definition extraction from legal opinions
  - `TestContractQA` (1 test): clause-level question answering accuracy
  - `TestExtractionCoverage` (2 tests): pattern coverage across all texts, alias detection on NDA clauses
  - Keyword-to-hypothesis mapping for all 14 contract_nli tasks
  - Metrics: accuracy, balanced accuracy, coverage, pattern type diversity

**Checkpoint**: ✅ TrustGraph visualization live at `/demo/graph.html`. Algorithm documented. 16 LegalBench datasets downloaded. 61 benchmark tests passing. **528 tests total.**

---

### Phase 7c: FAISS Vector Indexing & Provenance Visualization ✅ COMPLETE

**Goal**: Replace naive full-scan retrieval with industry-standard FAISS semantic vector search. Enhance TrustGraph visualization with query provenance overlay.
**Tests**: 18 new embedding tests (546 total passing)

- [x] T151 Add `sentence-transformers` + `faiss-cpu` + `numpy` dependencies to `pyproject.toml`
- [x] T152 Build `EmbeddingIndex` (`src/contractos/fabric/embedding_index.py`):
  - FAISS IndexFlatIP (inner product on L2-normalized = cosine similarity)
  - `all-MiniLM-L6-v2` sentence-transformer model (384-dim, 80MB, local inference)
  - Lazy model loading (singleton) — loads on first use
  - Mock fallback when sentence-transformers not installed
  - Per-document FAISS index stored in memory
  - `index_document()` — batch embed all chunks (facts, clauses, bindings)
  - `search()` — top-k nearest neighbors with chunk_type filtering
  - `build_chunks_from_extraction()` — converts extraction results to IndexedChunks
- [x] T153 Unit tests for EmbeddingIndex (`tests/unit/test_embedding_index.py`) — 18 tests:
  - `TestEmbeddingIndexCreation` (5 tests): create, index, multi-doc, remove
  - `TestEmbeddingSearch` (8 tests): results, scores, ordering, top-k, type filtering, semantic relevance (payment, termination, parties)
  - `TestBuildChunksFromExtraction` (5 tests): facts, clauses, bindings, short-skip, combined
- [x] T154 Integrate embedding index into upload pipeline (`contracts.py`):
  - After TrustGraph storage, build chunks and index in FAISS
  - `AppState` now holds `EmbeddingIndex` instance
- [x] T155 Upgrade `DocumentAgent` to use FAISS semantic retrieval:
  - When embedding index available: FAISS top-30 → retrieve relevant Fact objects → ordered by similarity
  - Fallback to full-scan when no embedding index (backward compatible)
  - Context now annotated with retrieval method
  - `QueryResult.retrieval_method` field: `"faiss_semantic"` or `"full_scan"`
  - API response includes `retrieval_method` for transparency
- [x] T156 TrustGraph Provenance Visualization (`demo/graph.html`):
  - Q&A panel in side panel — ask questions directly from the graph view
  - Provenance chain display: fact nodes, inference nodes, reasoning summary
  - Click provenance node → highlights it on the graph with yellow ring
  - After Q&A: referenced facts highlighted on graph (white ring, others dimmed)
  - Retrieval method badge: "FAISS Semantic" (green) or "Full Scan" (orange)
  - Demo console also shows retrieval method in Q&A responses

**Checkpoint**: ✅ FAISS vector indexing operational. Semantic retrieval replaces full-scan. Provenance visible on TrustGraph. **546 tests total.**

---

### Phase 7d: TrustGraph Branding, Chat Persistence, Multi-Doc & D3 Cleanup ✅ COMPLETE

**Goal**: Make TrustGraph concept prominent. Add chat persistence. Enable multi-document queries. Clean up D3 provenance visualization.
**Tests**: 7 new tests (553 total passing)

- [x] T157 TrustGraph branding & explanation (`demo/graph.html`):
  - Empty state explains TrustGraph as "graph-powered context harness" with entity flow diagram
  - Full ontology documentation: 8 entity types, 5 relationship types with color-coded legend
  - Links to TrustGraph.ai as inspiration for graph-powered AI context
  - Header shows "TrustGraph" badge alongside ContractOS branding
- [x] T158 D3.js visualization cleanup — cleaner provenance display:
  - Provenance edges animate in sequentially (150ms stagger per edge)
  - Cited fact nodes pulse with expanding radius animation
  - Provenance edges use 8,4 dash pattern with 0.85 opacity fade-in
  - Non-relevant nodes dimmed to 12% for clearer focus
- [x] T159 Query/chat persistence (`src/contractos/api/routes/query.py`):
  - Every Q&A persisted as `reasoning_session` in SQLite via `WorkspaceStore`
  - Default workspace auto-created (`w-default`)
  - `session_id` returned in every `QueryResponse`
  - New `GET /query/history` endpoint — returns chat history (most recent first)
  - Chat history panel in graph.html — shows past questions with status, confidence, timing
  - Click history item to replay the question
- [x] T160 Multi-document answer support:
  - `QueryRequest` now accepts `document_ids` (list) in addition to `document_id` (singular)
  - `DocumentAgent.answer()` iterates all target documents, merges FAISS results
  - Context labels facts with source document title for multi-doc queries
  - Scope selector in graph.html: "Current Document" or "All Uploaded Documents"
  - `uploadedDocIds` tracks all uploaded documents across the session
  - `QueryResponse.document_ids` shows which documents were queried
- [x] T161 Tests for persistence & multi-doc (`tests/unit/test_query_persistence.py`) — 7 tests:
  - `TestQueryPersistence` (3 tests): session_id in response, history retrieval, answers in history
  - `TestMultiDocumentQuery` (4 tests): multi-doc query, backward compat, 404, 400

**Checkpoint**: ✅ TrustGraph branding prominent. Chat persisted. Multi-doc queries working. D3 provenance animated. **553 tests total.**

---

### Phase 7e: Chat History View, Clear All, HuggingFace Multi-Doc ✅ COMPLETE

**Goal**: Full chat history visibility, clear uploaded files & history, multi-document analysis with real HuggingFace-sourced contracts.
**Tests**: 15 new tests (568 total passing)

- [x] T162 Chat history visibility — full Q&A display in both UIs:
  - `demo/graph.html`: expandable history items showing answer preview, confidence, timing
  - Click any history item to replay the question in the query input
  - `demo/index.html`: new "Chat History" sidebar section with rich card rendering
  - History auto-loads on document upload and after each query
- [x] T163 Clear uploaded files & history — API + UI:
  - `DELETE /contracts/clear` — wipes all contracts, facts, sessions, FAISS indices
  - `DELETE /query/history` — clears all chat sessions
  - `GET /contracts` — list all uploaded contracts with metadata
  - `TrustGraph.clear_all_data()` — cascading delete across 9 tables
  - `TrustGraph.list_contracts()` — list all indexed contracts
  - `WorkspaceStore.clear_sessions_by_workspace()` — delete sessions by workspace
  - `demo/graph.html`: "Clear All" button (red) resets graph, FAISS, history, UI state
  - `demo/graph.html`: "Clear" button on chat history section
  - `demo/index.html`: "Clear All Data" and "Clear Chat History" sidebar endpoints
  - Auto-clears client state (document_id, uploadedDocIds) on clear
- [x] T164 HuggingFace contract fixtures — 3 realistic procurement contracts:
  - `hf_master_services_agreement.docx` — GlobalTech ↔ Meridian ($2.4M, 3yr MSA)
    - 13 sections: definitions, scope, fees/payment, termination, IP, confidentiality,
      indemnification, liability cap, insurance, non-solicitation, audit, governing law
  - `hf_software_license_agreement.docx` — CloudVault ↔ Pacific Rim ($750K SaaS)
    - 8 sections: license grant, subscription fees, SLA (99.95%), data processing,
      termination, warranties, liability, governing law
  - `hf_supply_chain_agreement.docx` — Apex ↔ NovaTech (EUR 18.5M, 5yr supply)
    - 9 sections: supply obligations, pricing, quality (50 PPM), delivery (DDP),
      warranties, penalties, termination, liability, governing law
  - Based on CUAD (510 real contracts) and ContractNLI (607 NDAs) dataset patterns
- [x] T165 Multi-document analysis integration tests (`tests/integration/test_multi_doc_analysis.py`) — 7 tests:
  - Upload 3 HuggingFace contracts, verify all listed
  - Single-doc query on MSA (payment terms)
  - 2-doc cross-query (MSA + Software License termination comparison)
  - 3-doc cross-query (liability caps across all contracts)
  - Chat history records multi-doc queries with correct document_ids
  - Clear all contracts + history
  - Metadata richness: >20 facts, >5 clauses, >3 bindings per contract
- [x] T166 Unit tests for clear & history (`tests/unit/test_chat_history_and_clear.py`) — 8 tests:
  - `TestChatHistoryVisibility` (3): empty initially, shows Q&A, ordered most-recent-first
  - `TestClearOperations` (3): clear history, clear all contracts, clear empty is safe
  - `TestListContracts` (2): list empty, list after upload

**Checkpoint**: ✅ Full chat history visible. Clear all working. 3 HuggingFace contracts for multi-doc. **568 tests total.**

---

### Phase 7f: Real ContractNLI Document Testing ✅ COMPLETE

**Goal**: Download and test against all 50 real NDA documents referenced in LegalBench train.tsv files from the ContractNLI dataset (Stanford NLP, CC BY 4.0, 607 annotated NDAs). Complex single-document and multi-document questions covering diverse NDA types.
**Tests**: 54 new tests (622 total passing)

- [x] T167 Download & convert ContractNLI documents:
  - Extracted 50 unique document names from 16 legalbench train.tsv files
  - Downloaded ContractNLI dataset (607 NDAs) from Stanford NLP
  - Loaded full contract texts from JSON (train.json, dev.json, test.json)
  - Converted all 50 documents to DOCX format in `tests/fixtures/contractnli_docs/`
  - Document types: PDFs (37), SEC filings as HTML (6), SEC filings as TXT (7)
  - Script: `tests/fixtures/prepare_contractnli_docs.py`
- [x] T168 Single-document extraction quality tests (11 parametrized + 5 specific):
  - Parametrized upload test across 11 diverse NDAs (corporate, M&A, gov, SEC)
  - Rich extraction test on 4 complex NDAs (≥10 facts, ≥2 clauses)
  - Bosch NDA: facts + graph structure verification
  - NSK NDA: clause classification verification
  - CEII NDA: TrustGraph node/edge connectivity (≥10 nodes, ≥5 edges)
  - SEC filing NDA: clean extraction from HTML-converted text (>1000 words, >15 facts)
- [x] T169 Single-document complex Q&A tests (8 tests):
  - Bosch: confidentiality scope definition
  - NSK: termination provisions and survival obligations
  - The Munt: third-party disclosure restrictions
  - CEII: compelled disclosure procedures
  - SEC filing: residuals clause analysis
  - Casino: return/destruction of materials
  - SAMED: board member confidentiality obligations
  - Provenance chain verification on real documents
- [x] T170 Multi-document comparative analysis tests (5 tests):
  - 2-doc: Compare confidentiality scope (Bosch vs NSK)
  - 3-doc: Compare termination clauses (corporate vs M&A vs gov)
  - 5-doc: Disclosure rules across diverse NDA types
  - 2-doc: Corporate vs M&A permitted uses + residuals
  - 3-doc: Licensing restrictions comparison
- [x] T171 ContractNLI-style entailment tests (10 tests):
  - Explicit identification of confidential information
  - Limited use restrictions
  - No licensing grants
  - Notice on compelled disclosure
  - Sharing with employees
  - Return of confidential information
  - Survival of obligations
  - Confidentiality of agreement itself
  - Verbally conveyed information coverage
  - Multi-doc entailment comparison (copying restrictions across 3 NDAs)
- [x] T172 Chat history & session persistence with real docs (4 tests):
  - Single-doc session persistence
  - Multi-doc session persistence with correct document_ids
  - Multiple queries ordering (reverse chronological)
  - Clear history after real queries
- [x] T173 Bulk operations tests (3 tests):
  - Upload 10 diverse NDAs, verify all listed with facts
  - Query across 5 uploaded documents
  - Clear all after bulk upload
- [x] T174 Complex cross-document legal analysis tests (5 tests):
  - Identify most restrictive NDA (broadest definition, longest survival)
  - Remedies comparison (injunctive relief, specific performance)
  - Exceptions and carve-outs comparison across 4 NDAs
  - Governing law and jurisdiction comparison (international NDAs)
  - Definition scope analysis across 5 NDAs (marking, oral info, comparative)

**Document Groups Tested**:
- Corporate Mutual NDAs: Bosch, NSK, AMC, BT, non-disclosure-agreement-en
- M&A Confidentiality: The Munt, Business Sale, Casino, ICTSC, SEC-814457
- Government/Contractor: 064-19, CCTV, SAMED, CEII, Attachment-I
- SEC Filings: 802724, 915191, 916457, 1062478, 1010552
- Diverse Mix: Bosch + The Munt + CEII + SEC-802724 + Basic NDA

**Checkpoint**: ✅ All 50 real ContractNLI NDAs converted and tested. 54 new integration tests covering extraction, Q&A, multi-doc analysis, NLI entailment, history, bulk ops, and complex legal analysis. **622 tests total.**

---

### Phase 8a: Browser-Based Document Copilot ✅ COMPLETE

**Goal**: Build a browser-based DOCX/PDF document renderer with an embedded AI Copilot sidebar — replacing the need for a Word Add-in. Users can view contracts in-browser and interact with ContractOS as a Copilot alongside the rendered document. Prepare deployment configs for quick sharing.

**Architecture**: Instead of building a Word/Office Add-in (Phase 8 original), we build a web-native Copilot that works in any browser:
- **PDF rendering**: Mozilla PDF.js (v4.9.155) — native canvas-based PDF viewer
- **DOCX rendering**: docx-preview.js (v0.3.3) — high-fidelity Word document rendering
- **Copilot sidebar**: Chat-style AI assistant with extraction summary, quick actions, provenance display
- **Claude Agent SDK** (`@anthropic-ai/claude-agent-sdk`): Referenced for future server-side agent orchestration via TypeScript; current Copilot uses the existing `/query/ask` API

**Tests**: 9 new tests (631 total passing)

- [x] T175 Browser-based Document Copilot (`demo/copilot.html`):
  - **Document Viewer**: Full-page DOCX/PDF renderer with zoom controls (in/out/fit)
  - **PDF.js integration**: Canvas-based PDF rendering with page-by-page display
  - **docx-preview integration**: High-fidelity DOCX rendering preserving formatting
  - **Copilot sidebar** (420px, collapsible):
    - Extraction summary panel (facts, clauses, bindings, word count)
    - 8 quick-action buttons (Parties, Payment, Termination, Confidentiality, Governing Law, Liability, Key Dates, Gaps)
    - Chat-style Q&A with typing indicator and message history
    - Confidence labels with color coding (very_high/high/moderate/speculative)
    - Provenance display with icons and source references
    - Retrieval method indicator (faiss_semantic / full_scan)
    - Generation time display
  - **Drag & drop** file upload
  - **Server status** indicator (online/offline with polling)
  - **Navigation links** to API Console and TrustGraph pages
  - **Dark theme** consistent with existing demo pages
- [x] T176 Copilot integration tests (`tests/integration/test_copilot_page.py`) — 9 tests:
  - `TestCopilotPageServing` (3): Page served, PDF.js included, docx-preview included
  - `TestCopilotWorkflow` (4): Upload+query DOCX, upload+query PDF, quick actions workflow, extraction summary data
  - `TestCopilotWithRealNDAs` (2): Bosch NDA workflow, CEII NDA workflow
- [x] T177 Deployment configuration:
  - `Dockerfile` — Python 3.12-slim, health check, port 8742
  - `.dockerignore` — Excludes tests, specs, .git, .venv
  - `railway.toml` — Railway one-click deploy config
  - `render.yaml` — Render free-tier deploy config
  - `Procfile` — Heroku/Railway/Render compatible process file

**Deployment Options** (all free tier):
| Platform | Deploy Method | URL Pattern |
|----------|--------------|-------------|
| **Railway** | `railway up` or GitHub connect | `https://contractos-xxx.up.railway.app` |
| **Render** | Connect GitHub repo | `https://contractos.onrender.com` |
| **Fly.io** | `fly launch` | `https://contractos.fly.dev` |
| **Docker** | `docker build -t contractos . && docker run -p 8742:8742 contractos` | `http://localhost:8742` |

**Claude Agent SDK Integration Path** (future):
The [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-typescript) (`@anthropic-ai/claude-agent-sdk`) enables building autonomous AI agents with Claude's capabilities. Future integration:
1. Server-side Node.js agent using the SDK for complex multi-step contract analysis
2. Tool system integration: bash, text editor, web fetch, web search, memory tools
3. MCP Server integration for extending ContractOS with external tools
4. Subagent architecture for hierarchical contract reasoning (DocumentAgent → ClauseAgent → ComplianceAgent)

**Checkpoint**: ✅ Browser-based Document Copilot with PDF.js + docx-preview rendering. Copilot sidebar with chat, quick actions, provenance. Deployment configs for Railway/Render/Docker. **631 tests total.**

---

## Phase 8: Word Copilot Add-in (P2) — SUPERSEDED by Phase 8a

**Goal**: A working Word sidebar that communicates with the ContractOS server.

### Unit Tests (write FIRST — TypeScript/Jest)

- [ ] T112 [P] Write unit tests for API client in `copilot/src/services/__tests__/api-client.test.ts` — verify all endpoint calls match api-server.md contract; verify SSE stream parsing; verify error handling (server down, timeout, 4xx, 5xx)
- [ ] T113 [P] Write unit tests for provenance chain component in `copilot/src/components/__tests__/ProvenanceChain.test.tsx` — verify rendering of fact nodes, binding nodes, inference nodes; verify "Go to clause" click handler fires with correct char range; verify expand/collapse behavior
- [ ] T114 [P] Write unit tests for answer card component in `copilot/src/components/__tests__/AnswerCard.test.tsx` — verify answer text display; verify confidence indicator renders correct label/color; verify provenance expansion toggle

### Integration Tests (write FIRST)

- [ ] T115 [P] Write integration test for Copilot ↔ Server communication in `copilot/src/__tests__/integration.test.ts` — mock server responses; verify document detection flow (check indexed → prompt analyze → show status); verify Q&A flow (submit question → show streaming → show answer + provenance)

### Implementation

- [ ] T116 [P] Initialize Office Add-in project in `copilot/` — package.json, TypeScript config, React, Office JS API, Jest
- [ ] T117 [P] Create Office Add-in manifest (`copilot/manifest.xml`) — sidebar taskpane, localhost development
- [ ] T118 Implement API client service in `copilot/src/services/api-client.ts` — all endpoints from api-server.md, SSE streaming support
- [ ] T119 Implement sidebar layout component in `copilot/src/taskpane/App.tsx` — per copilot-api.md UI wireframe
- [ ] T120 Implement Q&A input component in `copilot/src/components/QueryInput.tsx` — text input with submit, loading state
- [ ] T121 Implement answer display component in `copilot/src/components/AnswerCard.tsx` — answer text, confidence indicator, expandable provenance
- [ ] T122 Implement provenance chain component in `copilot/src/components/ProvenanceChain.tsx` — fact nodes with "Go to clause" links, binding nodes, inference nodes, reasoning summary
- [ ] T123 Implement document navigation — use Office JS API to navigate to char ranges when "Go to clause" is clicked
- [ ] T124 Implement document status bar — show indexed/parsing/not-indexed status, fact/binding counts
- [ ] T125 Implement session history component in `copilot/src/components/SessionHistory.tsx` — list recent Q&A sessions
- [ ] T126 Implement error handling — server not running, LLM unavailable, unsupported format, per copilot-api.md error table
- [ ] T127 Implement auto-detection of document — on sidebar open, check if current document is indexed, prompt if not

**Checkpoint**: All Copilot tests pass. End-to-end system works. Open contract in Word, ask questions via sidebar, get answers with provenance.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Quality, performance, and developer experience improvements.

### Tests

- [ ] T128 [P] Write unit tests for CLI in `tests/unit/test_cli.py` — verify `serve`, `parse`, `query`, `facts`, `bindings` subcommands; verify argument parsing; verify output formatting
- [ ] T129 [P] Write unit test for truth model enforcement middleware in `tests/unit/test_truth_model_enforcement.py` — verify: tool output without Fact/Binding/Inference/Opinion type is rejected; verify typed outputs pass through
- [ ] T130 [P] Write integration test for full end-to-end flow in `tests/integration/test_end_to_end.py` — upload document via API → wait for indexing → query via API → verify answer with provenance → verify workspace persists → verify session history; this is the "golden path" test
- [ ] T131 [P] Write performance test in `tests/benchmark/test_performance.py` — verify <5s query on cached document; verify <30s first parse for 30-page document; verify <1s fact retrieval from TrustGraph

### Implementation

- [ ] T132 [P] Create CLI interface (`contractos` command) — `serve`, `parse`, `query`, `facts`, `bindings` subcommands in `src/contractos/cli.py`
- [ ] T133 [P] Set up COBench v0.1 benchmark framework in `tests/benchmark/cobench_v01.py` — 20 annotated contracts, 100 queries, Precision@N + Recall@N + MRR + NDCG metrics, confidence calibration curve
- [ ] T134 [P] Add structured logging (JSON format) with audit trail in `src/contractos/logging.py`
- [ ] T135 Add truth model enforcement middleware in `src/contractos/api/middleware/truth_model.py` — reject any tool output that is not typed as Fact/Binding/Inference/Opinion
- [ ] T136 Performance optimization — ensure <5s query on cached documents, profile and optimize hot paths
- [ ] T137 [P] Write comprehensive README with setup instructions referencing quickstart.md
- [ ] T138 Run full test suite, verify 90%+ code coverage, fix any failures, verify all acceptance scenarios from spec.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1: Fact Extraction)**: Depends on Phase 2 — first user story
- **Phase 4 (US2: Binding Resolution)**: Depends on Phase 3 (needs facts to resolve bindings)
- **Phase 5 (US3: Q&A)**: Depends on Phase 3 + Phase 4 (needs facts AND bindings)
- **Phase 6 (US4: Provenance Display)**: Depends on Phase 5 (needs query results to display)
- **Phase 7 (US5: Workspace Persistence)**: Depends on Phase 2 only (can parallel with US1-US3)
- **Phase 8 (Word Copilot)**: Depends on Phase 5 + Phase 6 + Phase 7 (needs working API)
- **Phase 9 (Polish)**: Depends on all user stories being complete

### TDD Execution Within Each Phase

```
1. Write ALL unit tests for the phase → verify they FAIL
2. Write ALL integration tests for the phase → verify they FAIL
3. Write ALL contract tests for the phase → verify they FAIL
4. Implement code until unit tests pass
5. Implement code until integration tests pass
6. Implement code until contract tests pass
7. Refactor while all tests stay green
```

### Parallel Opportunities

- **Phase 2**: All model tests (T009–T015) parallel. All model implementations (T016–T026) parallel. Storage tests (T027–T028) after models. LLM tests (T034) parallel with storage.
- **Phase 3**: All unit tests (T041–T049) parallel. All integration tests (T050–T051) parallel. Contract tests (T052) parallel with integration tests. Implementation sequential.
- **Phase 7 can start alongside Phase 3–5** — workspace persistence is independent of parsing/Q&A.
- **Phase 8 can start T116–T117 alongside Phase 3–5** — scaffold the add-in project early.
- **Phase 9**: T128–T131 (tests) all parallel. T132–T137 (implementation) all parallel.

### Critical Path

```
Phase 1 → Phase 2 → Phase 3 (Fact Extraction)
                        ↓
                     Phase 4 (Binding Resolution)
                        ↓
                     Phase 5 (Q&A) ← This is the MVP
                        ↓
                     Phase 6 (Provenance) + Phase 7 (Workspace)
                        ↓
                     Phase 8 (Word Copilot) ← This is the full Phase 1 product
                        ↓
                     Phase 9 (Polish)
```

---

## Phase 8b: Provenance Highlighting Fix + LLM-Powered Fact Discovery [COMPLETE]

### Bug Fix: Multi-Fact Document Highlighting (T178)

- [X] T178: Fix provenance fact highlighting in copilot.html — only first fact was highlighting [Bug Fix]
  - **Root cause**: `onclick` handlers used inline escaped strings that broke on quotes/special chars in fact summaries. Also `findAndHighlightText` returned on first match without trying subsequent facts.
  - **Fix 1**: Replaced inline `onclick` string interpolation with `data-panel`/`data-idx` attributes + `window._provPanels` registry. Click handler reads from stored data, not inline strings.
  - **Fix 2**: Rewrote `findAndHighlightText` to use `buildSearchPhrases()` — generates multiple search phrases of varying lengths (full text, first sentence, middle fragment, short fallback) and tries each progressively.
  - **Fix 3**: Added `doc-highlight-active` CSS class for currently-selected provenance item with purple accent glow.
  - **Fix 4**: Improved summary cleaning — strips location prefixes like "heading: X:" and "characters N-M:" before searching.
  - Files: `demo/copilot.html`

### LLM-Powered Hidden Fact Discovery (T179–T182)

- [X] T179: Write unit tests for `fact_discovery.py` — 9 tests [TDD Red] → [Green]
  - Tests: DiscoveredFact model, DiscoveryResult model, LLM discovery with mock responses, empty response handling, LLM error handling, long text truncation, empty claim filtering
  - File: `tests/unit/test_fact_discovery.py`

- [X] T180: Implement `src/contractos/tools/fact_discovery.py` — LLM discovery engine [Implementation]
  - `DISCOVERY_SYSTEM_PROMPT`: Expert legal analyst prompt for finding implicit obligations, hidden risks, unstated assumptions, cross-clause implications, missing protections, ambiguous terms
  - `DiscoveredFact` model: type, claim, evidence, risk_level, explanation
  - `DiscoveryResult` model: discovered_facts list, summary, categories_found, discovery_time_ms
  - `discover_hidden_facts()`: Async function that sends contract text + existing extraction context to LLM, parses structured response
  - Handles: text truncation (8000 char limit), empty claims filtering, LLM errors
  - File: `src/contractos/tools/fact_discovery.py`

- [X] T181: Write integration tests for discovery endpoint — 4 tests [TDD Red] → [Green]
  - Tests: 404 for missing doc, full discovery workflow with mock LLM, empty results handling, copilot page has discover button
  - File: `tests/integration/test_discovery_endpoint.py`

- [X] T182: Add `POST /contracts/{document_id}/discover` endpoint [Implementation]
  - Gathers existing facts, clauses, bindings as context
  - Reconstructs contract text from clause_text facts
  - Calls `discover_hidden_facts()` with LLM
  - Returns `DiscoveryResponse` with structured discovered facts, summary, categories, confidence
  - File: `src/contractos/api/routes/contracts.py`

### Copilot UI Enhancements (T183)

- [X] T183: Add "Discover Hidden Facts" button + discovered facts UI in copilot.html [Implementation]
  - Yellow-accented "Discover Hidden Facts" quick action button
  - Cursor-like reasoning steps for discovery: Loading facts → Reading context → AI Discovery Mode → Results
  - `discovered-section` panel: collapsible, yellow-themed, shows each discovered fact with type, claim, evidence, risk level
  - Clicking discovered facts highlights evidence in the rendered document
  - Extraction summary updates with discovered count badge
  - File: `demo/copilot.html`

---

## Phase 8c: Conversation Context Retention [COMPLETE]

**Goal**: Enable multi-turn conversations where the user can ask follow-up questions that reference prior answers. For example: user asks "What are the termination clauses?", model answers, then user asks "Any reference to section 5b?" — the model should understand the context.

**Architecture Note**: ContractOS uses a **three-phase extraction pipeline**:
1. **Phase 1: Deterministic extraction** — regex patterns for dates, amounts, definitions, section refs, aliases
2. **Phase 2: FAISS vector embedding** — `all-MiniLM-L6-v2` sentence-transformers for semantic retrieval at query time
3. **Phase 3: LLM discovery** — Anthropic Claude for implicit obligations, hidden risks, unstated assumptions (added in Phase 8b)

Conversation context retention adds a **fourth dimension**: multi-turn memory across Q&A interactions.

### ChatTurn Model + DocumentAgent Chat History (T184–T187)

- [X] T184: Add `ChatTurn` model to `models/query.py` [TDD Red → Green]
  - Simple Pydantic model: `question` + `answer` fields
  - Used to represent prior Q&A turns in conversation history
  - File: `src/contractos/models/query.py`

- [X] T185: Write unit tests for conversation context retention — 11 tests [TDD Red → Green]
  - Tests: ChatTurn creation/serialization, DocumentAgent accepts chat_history, history included in LLM messages, empty/None history backward compatible, multi-turn history ordering, history truncation (MAX_HISTORY_TURNS=10), system prompt includes conversation instruction, QueryRequest accepts session_id
  - File: `tests/unit/test_conversation_context.py`

- [X] T186: Update `DocumentAgent.answer()` to accept `chat_history` parameter [Implementation]
  - New keyword-only parameter: `chat_history: list[ChatTurn] | None = None`
  - `_build_messages()` helper: prepends prior Q&A turns as user/assistant message pairs
  - Truncates to `MAX_HISTORY_TURNS` (10) most recent turns to avoid token overflow
  - When history present, uses `SYSTEM_PROMPT_CONVERSATION` (includes follow-up/pronoun resolution instructions)
  - When no history, uses original `SYSTEM_PROMPT` (fully backward compatible)
  - File: `src/contractos/agents/document_agent.py`

- [X] T187: Update `QueryRequest` to accept optional `session_id` [Implementation]
  - New optional field: `session_id: str | None = None`
  - Backward compatible — existing callers without session_id work unchanged
  - File: `src/contractos/api/routes/query.py`

### API Endpoint + Session History (T188–T189)

- [X] T188: Add `_build_chat_history()` helper to query route [Implementation]
  - Looks up referenced session to find workspace scope
  - Fetches all completed sessions from same workspace targeting same document(s)
  - Returns chronologically ordered `ChatTurn` list
  - Only includes sessions with completed answers (filters out active/failed)
  - File: `src/contractos/api/routes/query.py`

- [X] T189: Write integration tests for conversation context endpoint — 4 tests [TDD Red → Green]
  - Tests: first query returns session_id, follow-up with session_id includes history in LLM messages, query without session_id has no history (stateless), multi-turn accumulation (3 turns)
  - File: `tests/integration/test_conversation_context_endpoint.py`

### Copilot UI Session Tracking (T190)

- [X] T190: Update copilot.html to track and send session_id [Implementation]
  - Added `currentSessionId` variable — tracks latest session_id from responses
  - `sendMessage()` includes `session_id` in request body when available
  - Updates `currentSessionId` from each response
  - Resets on new document upload or chat clear
  - File: `demo/copilot.html`

**Checkpoint**: ✅ Conversation context retention operational. Multi-turn Q&A works end-to-end. **659 tests total.**

---

## Test Coverage Summary

| Phase | Unit Tests | Integration Tests | Contract Tests | Total Tests |
|-------|-----------|------------------|---------------|-------------|
| Phase 2 (Foundation) | 14 | 0 | 1 | 15 |
| Phase 3 (US1: Extraction) | 9 | 2 | 1 | 12 |
| Phase 4 (US2: Bindings) | 2 | 1 | 1 | 4 |
| Phase 5 (US3: Q&A) | 6 | 3 | 1 | 10 |
| Phase 6 (US4: Provenance) | 2 | 1 | 1 | 4 |
| Phase 7 (US5: Workspace) | 2 | 2 | 1 | 5 |
| Phase 8 (Copilot) | 3 | 1 | 0 | 4 |
| Phase 8b (Discovery) | 9 | 4 | 0 | 13 |
| Phase 8c (Conversation Context) | 11 | 4 | 0 | 15 |
| Phase 9 (Polish) | 2 | 1 | 0 | 3 |
| **Total** | **60** | **19** | **6** | **85** |

## Task Summary

| Metric | Value |
|--------|-------|
| Total tasks | 190 |
| Test tasks | 104 (55%) |
| Implementation tasks | 86 (45%) |
| Phase 1 (Setup) | 5 tasks |
| Phase 2 (Foundation) | 35 tasks |
| Phase 3–7 (User Stories) | 71 tasks |
| Phase 7a–7f (Enhancements) | 36 tasks |
| Phase 8a (Browser Copilot) | 3 tasks |
| Phase 8b (Discovery + Highlighting Fix) | 6 tasks |
| Phase 8c (Conversation Context) | 7 tasks |
| Phase 8 (Word Add-in, superseded) | 16 tasks |
| Phase 9 (Polish) | 11 tasks |
| Total passing tests | 659 |
| Real NDA documents tested | 50 (from ContractNLI) |
| Deployment configs | 4 (Docker, Railway, Render, Procfile) |
| Parallelizable tasks | 55 (29%) |
| MVP scope (through Phase 5) | 86 tasks |
| Full scope (through Phase 8c) | 190 tasks |

---

## Notes

- [P] tasks = different files, no dependencies — can run in parallel
- [Story] label maps task to specific user story for traceability
- **Tests are ALWAYS written before implementation** — Red → Green → Refactor
- Every unit test mocks external dependencies (LLM, file system for non-fixture tests, network)
- Integration tests use real SQLite (in-memory) and real parsers, but mock LLM
- Contract tests use FastAPI TestClient against the running app
- Commit after each test-implementation pair passes
- Target: 90%+ code coverage enforced in CI
- Stop at any checkpoint to validate story independently
