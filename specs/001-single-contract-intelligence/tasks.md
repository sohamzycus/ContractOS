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
- **Phase 10 (Playbook Intelligence)**: Depends on Phase 8d (666 tests passing). Sub-phases:
  - **10a (Models)**: No internal dependencies — start immediately after Phase 8d
  - **10b (ComplianceAgent)**: Depends on 10a (needs playbook models)
  - **10c (DraftAgent)**: Depends on 10b (needs review findings to generate redlines)
  - **10d (NDA Triage)**: Depends on 10a only (independent of 10b/10c)
  - **10e (Copilot UI)**: Depends on 10b + 10d (needs API endpoints to call)
  - **10f (Polish)**: Depends on 10a–10e completion

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
- **Phase 10a**: T200–T202 (tests) all parallel. T203–T205 (models) all parallel. T206–T207 sequential.
- **Phase 10b**: T208–T209 (tests) parallel. T210–T216 sequential (agent → prompt → aggregation → strategy → endpoint → models → storage).
- **Phase 10c**: T217 (test) first. T218–T222 sequential.
- **Phase 10d**: T223–T225 (tests) all parallel. T226 parallel with T227. T228–T232 sequential.
- **Phase 10e**: T233–T237 all parallel (different UI sections, same file but independent functions).
- **Phase 10f**: T238–T240 all parallel. T241–T242 sequential.

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
                        ↓
                     Phase 10a (Playbook Models)
                        ↓
              ┌─────────┴──────────┐
              ↓                    ↓
         Phase 10b            Phase 10d
       (ComplianceAgent)     (NDA Triage)
              ↓                    │
         Phase 10c                 │
        (DraftAgent)               │
              └─────────┬──────────┘
                        ↓
                     Phase 10e (Copilot UI)
                        ↓
                     Phase 10f (Polish)
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

## Phase 8d: Sample Contracts & Playground [COMPLETE]

**Goal**: Allow users to explore ContractOS with pre-built sample contracts before uploading their own. Provides a frictionless onboarding experience with both simple and complex contracts in PDF and DOCX formats.

### Sample Contract Library (T191–T193)

- [X] T191: Create sample contract files in `demo/samples/` [Implementation]
  - Copied existing test fixtures: `simple_nda.pdf`, `complex_procurement_framework.pdf`
  - Generated DOCX fixtures: `simple_procurement.docx`, `complex_it_outsourcing.docx`
  - Created `manifest.json` with metadata (title, description, format, complexity, tags)
  - 4 sample contracts: 2 simple (NDA, MSA), 2 complex (procurement framework, IT outsourcing)
  - Files: `demo/samples/manifest.json`, `demo/samples/*.pdf`, `demo/samples/*.docx`

- [X] T192: Add `GET /contracts/samples` endpoint [TDD Red → Green]
  - Returns structured metadata from `manifest.json`
  - Includes filename, title, description, format, complexity, tags
  - Route placed BEFORE `/{document_id}` to avoid path parameter collision
  - File: `src/contractos/api/routes/contracts.py`

- [X] T193: Add `POST /contracts/samples/{filename}/load` endpoint [TDD Red → Green]
  - Reads sample file from `demo/samples/`
  - Processes through full extraction pipeline (parse → extract → classify → resolve → FAISS index)
  - Returns same `ContractResponse` as `/contracts/upload`
  - Validates file extension, returns 404 for missing samples
  - File: `src/contractos/api/routes/contracts.py`

- [X] T194: Write unit tests for sample contracts — 7 tests [TDD Red → Green]
  - Tests: list returns samples, required fields present, both formats included, load PDF, load DOCX, load nonexistent returns 404, loaded sample is queryable
  - File: `tests/unit/test_sample_contracts.py`

### Copilot UI Sample Picker (T195)

- [X] T195: Add sample contract picker to copilot.html [Implementation]
  - Added "or try a sample contract" divider below upload zone
  - 2x2 grid of sample cards with format badge, complexity badge, title, description, tags
  - One-click loading: fetches sample via API, renders document, shows extraction summary
  - Loading animation with progress bar on card
  - Added "Upload Contract" button in header for easy switching from sample to own contract
  - CSS: `.sample-grid`, `.sample-card`, `.sc-format`, `.sc-complexity`, `.sc-title`, `.sc-desc`, `.sc-tags`
  - File: `demo/copilot.html`

**Checkpoint**: ✅ Sample contracts playground operational. Users can try 4 pre-built contracts (2 PDF, 2 DOCX) with one click. **666 tests total.**

---

## Phase 10: Playbook Intelligence & Risk Framework [COMPLETE]

**Goal**: Adopt domain workflows from [Anthropic's Legal Productivity Plugin](https://github.com/anthropics/knowledge-work-plugins/tree/main/legal) as grounded agents built on ContractOS's extraction pipeline, TrustGraph, and FAISS semantic search. Every assessment is backed by extracted facts with provenance chains.

**Spec**: `plan.md` (Phase 9 plan), `research.md` (R1–R7), `data-model-phase9.md`, `contracts/review-contract.md`, `contracts/triage-nda.md`, `quickstart.md`

**Prerequisites**: All Phase 8d tasks complete (666 tests passing). Existing clause classifier, fact extractor, binding resolver, and LLM provider operational.

### Phase 10a: Foundation — Playbook Models & Loader (T200–T207)

**Purpose**: Core data models and configuration loading that all playbook features depend on.

#### Tests (TDD Red)

- [x] T200 [P] Write unit tests for playbook models in `tests/unit/test_playbook_models.py` — verify: `PlaybookConfig` validates from YAML dict; `PlaybookPosition` requires clause_type and standard_position; `AcceptableRange` has min/max; `NegotiationTier` enum has tier_1/tier_2/tier_3; `ReviewSeverity` enum has green/yellow/red; invalid YAML rejected with ValidationError
- [x] T201 [P] Write unit tests for risk models in `tests/unit/test_risk_models.py` — verify: `RiskScore` enforces severity/likelihood 1-5; score = severity × likelihood; `RiskLevel` derived correctly (1-4=low, 5-9=medium, 10-15=high, 16-25=critical); `RiskProfile` aggregates correctly
- [x] T202 [P] Write unit tests for playbook loader in `tests/unit/test_playbook_loader.py` — verify: loads YAML file into `PlaybookConfig`; validates schema; returns default playbook when no path given; raises FileNotFoundError for missing file; handles malformed YAML gracefully

#### Implementation (TDD Green)

- [x] T203 [P] Create playbook models in `src/contractos/models/playbook.py` — `PlaybookConfig`, `PlaybookPosition`, `AcceptableRange`, `NegotiationTier` Pydantic models
- [x] T204 [P] Create review models in `src/contractos/models/review.py` — `ReviewSeverity`, `ReviewFinding`, `RedlineSuggestion`, `ReviewResult`, `RiskProfile` Pydantic models
- [x] T205 [P] Create risk models in `src/contractos/models/risk.py` — `RiskScore`, `RiskLevel` with computed score and level derivation
- [x] T206 Implement playbook loader in `src/contractos/tools/playbook_loader.py` — `load_playbook(path)` → `PlaybookConfig`; `load_default_playbook()` → built-in default
- [x] T207 Create default playbook in `config/default_playbook.yaml` — standard commercial positions for: limitation_of_liability, indemnification, ip_ownership, data_protection, confidentiality, termination, governing_law, force_majeure, assignment, payment_terms (10 clause types with positions, ranges, triggers, priorities)

**Checkpoint**: ✅ Playbook models validated, loader tested, default playbook available. 42 tests pass.

---

### Phase 10b: ComplianceAgent — Playbook Review (T208–T216)

**Goal**: Compare extracted clauses against playbook positions, classify each as GREEN/YELLOW/RED with provenance.

**Independent Test**: Upload a contract, run playbook review, verify each clause gets a severity classification backed by extracted facts.

#### Tests (TDD Red)

- [x] T208 [P] Write unit tests for ComplianceAgent in `tests/unit/test_compliance_agent.py` — verify:
  - `review(document_id, playbook)` returns `ReviewResult` with findings
  - Each finding has severity, clause_id, provenance_facts
  - Missing required clauses → RED finding with "missing clause" type
  - Clause matching playbook standard → GREEN
  - Clause outside range → YELLOW
  - Escalation trigger match → RED (deterministic override)
  - Mock LLM for classification judgment
  - At least 8 test cases covering GREEN/YELLOW/RED paths
- [x] T209 [P] Write integration test for review endpoint in `tests/integration/test_review_endpoint.py` — verify:
  - `POST /contracts/{id}/review` returns 200 with ReviewResult
  - Response has findings, summary, risk_profile, negotiation_strategy
  - 404 for nonexistent document
  - Findings reference real extracted clause IDs
  - At least 4 test cases

#### Implementation (TDD Green)

- [x] T210 Implement ComplianceAgent in `src/contractos/agents/compliance_agent.py`:
  - `async review(document_id, playbook, state, user_side, focus_areas, generate_redlines)` → `ReviewResult`
  - Step 1: Load clauses from TrustGraph for document
  - Step 2: For each playbook position, find matching clause by type
  - Step 3: Missing required clause → RED finding (deterministic)
  - Step 4: Found clause → check escalation triggers (deterministic pattern match)
  - Step 5: If no trigger match → LLM classification (send clause text + playbook position)
  - Step 6: Build ReviewFinding with provenance (fact IDs from clause)
  - Step 7: Aggregate into ReviewResult with risk_profile
  - LLM system prompt: `COMPLIANCE_REVIEW_PROMPT` with structured JSON output
- [x] T211 Add LLM prompt for compliance review in `src/contractos/agents/compliance_agent.py` — `COMPLIANCE_REVIEW_PROMPT` that instructs LLM to compare clause text against playbook position and return severity, deviation_description, business_impact, risk_score (severity 1-5, likelihood 1-5) as JSON
- [x] T212 Implement risk profile aggregation in `src/contractos/agents/compliance_agent.py` — `_build_risk_profile(findings)` → `RiskProfile` with overall_level, distribution, tier counts
- [x] T213 Implement negotiation strategy generation in `src/contractos/agents/compliance_agent.py` — `_generate_strategy(findings, playbook)` → string summary using LLM with Tier 1/2/3 framework
- [x] T214 Add `POST /contracts/{document_id}/review` endpoint in `src/contractos/api/routes/contracts.py`:
  - Request body: `ReviewRequest(playbook, user_side, focus_areas, generate_redlines)`
  - Response: `ReviewResponse` (mirrors ReviewResult)
  - Route MUST be placed before `/{document_id}` catch-all
  - Loads playbook, calls ComplianceAgent.review(), returns result
- [x] T215 Add review response models to `src/contractos/api/routes/contracts.py` — `ReviewRequest`, `ReviewResponse`, `ReviewFindingResponse`, `RiskScoreResponse`, `RiskProfileResponse`, `RedlineResponse`
- [x] T216 Store review results as ReasoningSession in WorkspaceStore — review is persisted for later retrieval

**Checkpoint**: ✅ Playbook review operational. Upload contract → review against playbook → GREEN/YELLOW/RED per clause with provenance. Tests pass.

---

### Phase 10c: DraftAgent — Redline Generation (T217–T222)

**Goal**: Generate specific alternative contract language for YELLOW/RED findings.

**Independent Test**: Given a RED finding, generate a redline with proposed language, rationale, priority, and fallback.

#### Tests (TDD Red)

- [x] T217 [P] Write unit tests for DraftAgent in `tests/unit/test_draft_agent.py` — verify:
  - `generate_redline(finding, playbook_position, user_side)` returns `RedlineSuggestion`
  - Proposed language is non-empty and different from current language
  - Rationale is suitable for external sharing (no internal jargon)
  - Priority matches playbook position tier
  - Fallback language provided for tier_1 findings
  - Mock LLM for generation
  - At least 5 test cases

#### Implementation (TDD Green)

- [x] T218 Implement DraftAgent in `src/contractos/agents/draft_agent.py`:
  - `async generate_redline(finding, playbook_position, user_side, llm)` → `RedlineSuggestion`
  - LLM prompt: current language + playbook position + deviation + contract type + user side
  - Parse LLM response as structured JSON
  - Fallback: if LLM fails, return None (redline is optional)
- [x] T219 Add `REDLINE_GENERATION_PROMPT` in `src/contractos/agents/draft_agent.py` — instructs LLM to generate: proposed_language, rationale (suitable for counterparty), priority, fallback_language
- [x] T220 Integrate DraftAgent into ComplianceAgent — when `generate_redlines=True`, call DraftAgent for each YELLOW/RED finding and attach `RedlineSuggestion` to the finding
- [x] T221 [P] Write integration test for redline generation in `tests/integration/test_review_endpoint.py` — verify redlines appear in review response when `generate_redlines=true`
- [x] T222 Add lenient JSON parsing for redline LLM output — reuse `_parse_lenient_json` from `fact_discovery.py`

**Checkpoint**: ✅ Redline generation operational. YELLOW/RED findings include proposed alternative language. Tests pass.

---

### Phase 10d: NDA Triage Agent (T223–T232)

**Goal**: Automated 10-point NDA screening with GREEN/YELLOW/RED classification and routing.

**Independent Test**: Upload an NDA, run triage, verify 10-point checklist with pass/fail/review per item and overall classification.

#### Tests (TDD Red)

- [x] T223 [P] Write unit tests for triage models in `tests/unit/test_triage_models.py` — verify: `ChecklistItem` validates; `ChecklistResult` has status enum; `TriageClassification` has level/routing/timeline; `TriageResult` aggregates correctly; `TriageLevel` enum has green/yellow/red
- [x] T224 [P] Write unit tests for NDATriageAgent in `tests/unit/test_nda_triage_agent.py` — verify:
  - `triage(document_id, state)` returns `TriageResult`
  - 10 checklist items evaluated
  - All PASS → GREEN classification
  - One FAIL (non-critical) → YELLOW
  - Critical FAIL (missing carveout, non-compete) → RED
  - Automated checks run for `auto` and `hybrid` items
  - LLM called for `hybrid` and `llm_only` items
  - Mock LLM, at least 6 test cases
- [x] T225 [P] Write integration test for triage endpoint in `tests/integration/test_triage_endpoint.py` — verify:
  - `POST /contracts/{id}/triage` returns 200 with TriageResult
  - Response has classification, checklist_results, key_issues
  - 404 for nonexistent document
  - At least 3 test cases

#### Implementation (TDD Green)

- [x] T226 [P] Create triage models in `src/contractos/models/triage.py` — `AutomationLevel`, `ChecklistStatus`, `TriageLevel`, `ChecklistItem`, `ChecklistResult`, `TriageClassification`, `TriageResult`
- [x] T227 Create NDA checklist config in `config/nda_checklist.yaml` — 10 items: agreement_structure, definition_scope, receiving_party_obligations, standard_carveouts, permitted_disclosures, term_duration, return_destruction, remedies, problematic_provisions, governing_law; each with automation level and criteria
- [x] T228 Implement NDATriageAgent in `src/contractos/agents/nda_triage_agent.py`:
  - `async triage(document_id, state, checklist_path)` → `TriageResult`
  - Load checklist config
  - For each item: run automated checks (pattern matching on extracted facts/clauses) + LLM verification
  - Aggregate: all PASS → GREEN; any non-critical FAIL → YELLOW; critical FAIL → RED
  - Generate routing recommendation and timeline
- [x] T229 Implement automated checklist checks in `src/contractos/agents/nda_triage_agent.py`:
  - `_check_agreement_structure(facts, clauses)` — detect mutual/unilateral
  - `_check_standard_carveouts(facts)` — pattern match 5 required carveouts
  - `_check_term_duration(facts)` — extract term from duration facts
  - `_check_governing_law(facts)` — extract jurisdiction
  - `_check_problematic_provisions(facts, clauses)` — detect non-solicitation, non-compete patterns
- [x] T230 Add `NDA_TRIAGE_PROMPT` in `src/contractos/agents/nda_triage_agent.py` — LLM prompt for hybrid/llm_only checklist items
- [x] T231 Add `POST /contracts/{document_id}/triage` endpoint in `src/contractos/api/routes/contracts.py`:
  - Request body: `TriageRequest(checklist, context)`
  - Response: `TriageResponse` (mirrors TriageResult)
  - Route placed before `/{document_id}` catch-all
- [x] T232 Add triage response models to `src/contractos/api/routes/contracts.py` — `TriageRequest`, `TriageResponse`, `ChecklistResultResponse`, `TriageClassificationResponse`

**Checkpoint**: ✅ NDA triage operational. Upload NDA → 10-point checklist → GREEN/YELLOW/RED with routing. Tests pass.

---

### Phase 10e: Copilot UI — Review & Triage (T233–T237)

**Goal**: Display playbook review results and NDA triage in the Copilot UI.

#### Implementation

- [x] T233 Add "Review Against Playbook" quick-action button in `demo/copilot.html`:
  - New button alongside "Discover Hidden Facts"
  - Triggers `POST /contracts/{id}/review` with reasoning steps animation
  - Displays results as color-coded finding cards (GREEN/YELLOW/RED badges)
  - Each card: clause heading, severity badge, deviation description
  - Click card → highlight clause in rendered document
  - Expandable redline suggestion for YELLOW/RED
- [x] T234 Add "Triage NDA" quick-action button in `demo/copilot.html`:
  - Triggers `POST /contracts/{id}/triage`
  - Displays large classification badge (GREEN/YELLOW/RED)
  - 10-item checklist with pass/fail/review icons
  - Routing recommendation with timeline
  - Key issues list for YELLOW/RED
- [x] T235 Add risk matrix visualization in `demo/copilot.html`:
  - Small 5×5 grid showing finding distribution by severity × likelihood
  - Color-coded cells (green/yellow/orange/red)
  - Click cell → filter findings to that risk level
- [x] T236 Add CSS styles for review/triage UI in `demo/copilot.html`:
  - `.review-finding` card with severity badge
  - `.triage-badge` large classification indicator
  - `.checklist-item` with status icon
  - `.risk-matrix` grid visualization
  - `.redline-suggestion` expandable section
- [x] T237 Add negotiation strategy display in `demo/copilot.html`:
  - Tier 1/2/3 priority list
  - Collapsible section below findings
  - Links to relevant findings per tier

**Checkpoint**: ✅ Full Copilot UI for playbook review and NDA triage. Color-coded findings, risk matrix, redlines, triage checklist all functional.

---

### Phase 10f: Polish & Documentation (T238–T242)

- [x] T238 [P] Update `docs/EXECUTIVE_SUMMARY.md` with Phase 10 features
- [x] T239 [P] Update `docs/ANTHROPIC_COWORK_ANALYSIS.md` with implementation status
- [x] T240 [P] Update `README.md` with playbook review and NDA triage documentation
- [x] T241 Run full test suite — verify all tests pass (target: ~730+ tests)
- [x] T242 Update `tasks.md` with Phase 10 completion status and final test count

**Checkpoint**: ✅ Phase 10 complete. Playbook review, risk scoring, redline generation, NDA triage all operational with full TDD coverage. **77 new tests (70 unit + 7 integration), 743 total.**

---

## Phase 12: SSE Streaming, Expanded Legal Analysis, Reports & Bug Fixes [COMPLETE]

**Goal**: Real-time progressive reasoning via Server-Sent Events, expanded legal analysis (obligation extraction, risk memo generation), HTML report downloads, performance improvements via parallel LLM batching, and bug fixes for JSON parsing of truncated LLM responses.

**Tests**: 36 new tests (691 total passing)

### Streaming Endpoints (T243–T248)

- [x] T243 Create SSE streaming infrastructure in `src/contractos/api/routes/stream.py`:
  - `_sse_event()` helper for formatting Server-Sent Events
  - Event types: `step` (intermediate progress), `result` (final payload), `error`, `done`
  - All endpoints use `StreamingResponse` with `text/event-stream` media type
- [x] T244 `GET /stream/{document_id}/review` — progressive playbook review:
  - Streams clause-by-clause analysis with parallel LLM batching (batch_size=3)
  - Step events: `load_playbook`, `classify` (per batch), `redline` (parallel), `aggregate`
  - Result event: full `ReviewResult` with findings, risk profile, strategy
- [x] T245 `GET /stream/{document_id}/triage` — progressive NDA triage:
  - Streams per-checklist-item evaluation with parallel batching
  - Step events: `load_checklist`, `evaluate` (per batch), `classify`
  - Result event: full `TriageResult` with classification, routing
- [x] T246 `GET /stream/{document_id}/discover` — progressive hidden fact discovery:
  - Step events: `gather_context`, `build_prompt`, `llm_analysis`, per-fact `discovered_fact`
  - Result event: full `DiscoveryResult` with confidence
- [x] T247 `GET /stream/{document_id}/obligations` — obligation extraction:
  - LLM-powered extraction of affirmative, negative, and conditional obligations
  - System prompt limits to top 15 obligations with concise fields
  - `max_tokens=16384` to handle complex contracts
  - Step events: `gather`, `extract`, per-obligation `obligation`
- [x] T248 `GET /stream/{document_id}/risk-memo` — risk memo generation:
  - LLM-powered structured risk assessment
  - System prompt: executive summary, key risks (max 8), missing protections, recommendations
  - Step events: `gather`, `analyze`, per-risk `risk_item`, `missing`, `recommendation`

### Report Download (T249)

- [x] T249 `GET /stream/{document_id}/report?type=review|triage|discovery` — HTML report generation:
  - Professional dark-theme HTML reports with print-friendly CSS
  - Three report types: review (findings + redlines), triage (classification + checklist), discovery (hidden facts)
  - `_report_template()` base HTML + `_generate_review_report()`, `_generate_triage_report()`, `_generate_discovery_report()`

### Bug Fixes (T250–T252)

- [x] T250 Fix `ConfidenceDisplay.score` → `ConfidenceDisplay.value` attribute error in discovery stream
- [x] T251 Fix truncated LLM JSON parsing for obligations — generic `_salvage_array_objects()` helper:
  - Walks character-by-character through truncated JSON arrays
  - Handles escaped quotes, nested objects, strings containing braces
  - Salvageable keys: `discovered_facts`, `obligations`, `key_risks`, `recommendations`, `missing_protections`, `escalation_items`
  - Extracts scalar fields (summary, totals) from text before the truncated array
- [x] T252 Update obligation system prompt to limit to top 15 obligations and place summary before array to survive truncation

### Copilot UI Updates (T253–T256)

- [x] T253 `streamSSE()` helper function in copilot.html — generic EventSource consumer
- [x] T254 Progressive reasoning steps with `isRunning` animation:
  - `addReasoningStep(iconClass, iconText, html, isRunning)` — supports running/done states
  - `updateLastReasoningStep(html, markDone)` — update active step details
  - `completeReasoning(timeMs)` — clears both `activeReasoning` and `reasoningSteps` IDs (fixes DOM collision bug)
- [x] T255 New quick-action buttons: "Extract Obligations" and "Generate Risk Memo"
- [x] T256 `downloadReport(reportType)` — client-side report download trigger

### Tests (T257–T260)

- [x] T257 Unit tests for lenient JSON parser (`tests/unit/test_lenient_json_parser.py`) — 19 tests:
  - `TestParseLenientJsonBaseline` (6): valid JSON, arrays, markdown fenced, surrounding text, trailing commas
  - `TestSalvageArrayObjects` (8): complete arrays, truncated arrays, empty, nested, string braces, escaped quotes, mid-string truncation
  - `TestParseLenientJsonObligations` (2): truncated obligations salvaged, complete obligations parsed
  - `TestParseLenientJsonRiskMemo` (2): truncated key_risks salvaged, complete risk memo parsed
  - `TestParseLenientJsonDiscoveredFacts` (1): backward-compat truncated discovered_facts
- [x] T258 Integration tests for SSE streaming endpoints (`tests/integration/test_stream_endpoints.py`) — 17 tests:
  - `TestStreamEndpoints404` (6): all 6 streaming endpoints return 404 for missing documents
  - `TestObligationStream` (2): full obligation stream with events, truncated response handling
  - `TestRiskMemoStream` (1): risk memo stream with events
  - `TestReviewStream` (1): review stream returns 200 with SSE events
  - `TestTriageStream` (1): triage stream returns 200 with SSE events
  - `TestDiscoverStream` (1): discover stream with result events
  - `TestReportDownload` (3): report requires type, review/triage/discovery HTML reports
  - `TestSSEEventFormat` (1): verify event/data structure

**Checkpoint**: ✅ SSE streaming operational. Obligation extraction and risk memo working. Truncated JSON salvage generic. Progressive UI. Report downloads. **691 tests total.**

---

---

## Phase 13: MCP Server — Contract Intelligence via Model Context Protocol

**Goal**: Expose all ContractOS capabilities as an MCP server so AI assistants (Cursor, Claude Desktop, Claude Code) can perform contract intelligence natively — upload, analyze, review, triage, discover, and query contracts without the Copilot UI.

**Design Artifacts**: `research-mcp.md`, `data-model-mcp.md`, `contracts/mcp-server.md`, `quickstart-mcp.md`

**SDK**: `mcp[cli]>=1.26.0` (FastMCP)  
**Transports**: stdio (local, default), Streamable HTTP (remote/Docker)

---

### Phase 13a: Setup & Infrastructure (T261–T268)

**Purpose**: Install MCP dependency, create package structure, initialize shared context

- [ ] T261 Add `mcp[cli]>=1.26.0` to `pyproject.toml` dependencies and install
- [ ] T262 [P] Create `src/contractos/mcp/__init__.py` with package docstring
- [ ] T263 [P] Create `src/contractos/mcp/context.py` — shared `MCPContext` class:
  - **Wraps `AppState` via composition** (imports and reuses `init_state()` from `api/deps.py`)
  - Does NOT duplicate TrustGraph/EmbeddingIndex/LLM — accesses them via `self.state`
  - Singleton lifecycle (created once at server startup, calls `shutdown_state()` on close)
  - `get_contract_or_error(document_id)` helper that raises agent-friendly error strings
  - `get_document_text(document_id)` helper to retrieve full text for LLM calls
  - All LLM calls MUST go through `self.state.llm` (provider abstraction, not direct Anthropic SDK)
- [ ] T264 Create `src/contractos/mcp/server.py` — FastMCP server definition:
  - `FastMCP("ContractOS", version="0.1.0", json_response=True)`
  - `__main__` entry point: `python -m contractos.mcp.server`
  - CLI args: `--transport` (stdio|http), `--port` (default 8743)
  - Startup: initialize `MCPContext`, register tools/resources/prompts
  - Graceful shutdown: close TrustGraph, EmbeddingIndex
- [ ] T265 [P] Create `.cursor/mcp.json.example` — Cursor MCP client config template (checked in, placeholder keys). Add `.cursor/mcp.json` to `.gitignore` (contains real API keys)
- [ ] T266 [P] Create `tests/unit/test_mcp_context.py` — unit tests for MCPContext:
  - Test context initialization with mock config
  - Test `get_contract_or_error` raises for missing document
  - Test `get_document_text` returns full text
  - Test singleton lifecycle (init + shutdown)
- [ ] T267 [P] Create `tests/unit/test_mcp_server_startup.py` — server startup tests:
  - Test server creates FastMCP instance with correct name/version
  - Test tool/resource/prompt registration counts (13/10/5)
  - Test `--transport` CLI arg parsing
- [ ] T268 Verify MCP server starts without errors: `PYTHONPATH=src python -m contractos.mcp.server`

**Checkpoint**: MCP server starts, empty tool/resource/prompt registrations verified.

---

### Phase 13b: MCP Tools — Contract Ingestion (T269–T276)

**Purpose**: Implement tools for uploading and loading contracts

#### Tests (T269–T271)

- [ ] T269 [P] Unit test for `upload_contract` tool in `tests/unit/test_mcp_tools.py`:
  - Test successful upload returns `UploadResult` with doc_id, fact_count, clause_count
  - Test file-not-found returns agent-friendly error string
  - Test unsupported format (.txt) returns error
  - Mock: `fact_extractor.extract_from_file`, `TrustGraph`, `EmbeddingIndex`
- [ ] T270 [P] Unit test for `load_sample_contract` tool:
  - Test loading `simple_nda.pdf` returns `UploadResult`
  - Test invalid filename returns error with available samples list
  - Mock: file I/O, extraction pipeline
- [ ] T271 [P] Unit test for `clear_workspace` tool:
  - Test returns confirmation with counts
  - Mock: `TrustGraph.clear_all_data()`

#### Implementation (T272–T276)

- [ ] T272 Create `src/contractos/mcp/tools.py` — tool module with `register_tools(mcp, ctx)` function
- [ ] T273 Implement `@mcp.tool() upload_contract(file_path: str)` in tools.py:
  - Read file from `file_path`, detect format (.docx/.pdf)
  - Call `extract_from_file()` → store in TrustGraph → index in FAISS
  - Return `UploadResult` dict with doc_id, counts, timing
  - Error handling: FileNotFoundError, unsupported format, extraction failure
- [ ] T274 Implement `@mcp.tool() load_sample_contract(filename: str)`:
  - Resolve from `demo/samples/` directory
  - Validate against `manifest.json`
  - Reuse same extraction pipeline as `upload_contract`
- [ ] T275 Implement `@mcp.tool() clear_workspace()`:
  - Call `TrustGraph.clear_all_data()`, clear FAISS index, clear chat history
  - Return counts of removed items
- [ ] T276 Wire `register_tools()` into `server.py` startup

**Checkpoint**: Upload, load sample, and clear workspace tools functional.

---

### Phase 13c: MCP Tools — Q&A and Search (T277–T283)

**Purpose**: Implement question answering and semantic search tools

#### Tests (T277–T279)

- [ ] T277 [P] Unit test for `ask_question` tool:
  - Test returns answer with confidence, provenance, sources
  - Test with specific `document_ids` filter
  - Test with no indexed contracts returns error
  - Mock: `DocumentAgent.answer()`
- [ ] T278 [P] Unit test for `search_contracts` tool:
  - Test returns ranked results with scores
  - Test `top_k` parameter
  - Test empty index returns error
  - Mock: `EmbeddingIndex.search()`
- [ ] T279 [P] Unit test for `compare_clauses` tool:
  - Test returns differences with significance ratings
  - Test missing document returns error
  - Test missing clause type returns error
  - Mock: `DocumentAgent`, `TrustGraph`

#### Implementation (T280–T283)

- [ ] T280 Implement `@mcp.tool() ask_question(question: str, document_ids: list[str] | None = None)`:
  - Build `Query` from input, call `DocumentAgent.answer()`
  - Format `QueryResult` → `QuestionResult` dict with provenance
  - Use `ctx.report_progress()` for long-running queries
- [ ] T281 Implement `@mcp.tool() search_contracts(query: str, top_k: int = 5)`:
  - Call `EmbeddingIndex.search()` across all indexed documents
  - Return `SearchResult` dict with hits, scores, clause types
- [ ] T282 Implement `@mcp.tool() compare_clauses(document_id_1, document_id_2, clause_type)`:
  - Define `CLAUSE_COMPARISON_PROMPT` system prompt (structured diff template with aspect/significance output)
  - Fetch clauses of given type from both documents via TrustGraph
  - Call LLM via `ctx.state.llm` (NOT direct Anthropic SDK) with comparison prompt
  - Parse structured response with `_parse_lenient_json()`
  - Return `ComparisonResult` dict with differences and recommendation
- [ ] T283 Integration test in `tests/integration/test_mcp_qa_tools.py`:
  - Upload sample contract → ask question → verify answer has provenance
  - Upload two samples → compare clauses → verify differences returned

**Checkpoint**: Q&A, search, and comparison tools functional with provenance.

---

### Phase 13d: MCP Tools — Analysis (T284–T296)

**Purpose**: Implement playbook review, NDA triage, discovery, obligations, risk memo, gaps, and reports

#### Tests (T284–T289)

- [ ] T284 [P] Unit test for `review_against_playbook` tool:
  - Test returns findings with severity, risk_profile, strategy
  - Test progress reporting (ctx.report_progress called)
  - Mock: `ComplianceAgent.review()`
- [ ] T285 [P] Unit test for `triage_nda` tool:
  - Test returns checklist with PASS/FAIL/PARTIAL, classification, summary
  - Mock: `NDATriageAgent.triage()`
- [ ] T286 [P] Unit test for `discover_hidden_facts` tool:
  - Test returns discovered_facts with categories
  - Mock: `discover_hidden_facts()` from tools
- [ ] T287 [P] Unit test for `extract_obligations` tool:
  - Test returns obligations categorized by type
  - Mock: LLM call with obligation prompt
- [ ] T288 [P] Unit test for `generate_risk_memo` tool:
  - Test returns risk memo with key_risks, recommendations
  - Mock: LLM call with risk memo prompt
- [ ] T289 [P] Unit test for `get_clause_gaps` and `generate_report` tools:
  - Test clause gaps returns missing facts per clause
  - Test report generation returns HTML content
  - Mock: TrustGraph queries, report template

#### Implementation (T290–T296)

- [ ] T290 Implement `@mcp.tool() review_against_playbook(document_id, playbook_path=None)`:
  - Load playbook (custom or default), fetch contract + clauses from TrustGraph
  - Call `ComplianceAgent.review()` with progress reporting
  - Return `ReviewResult` serialized as dict
- [ ] T291 Implement `@mcp.tool() triage_nda(document_id)`:
  - Fetch contract text, call `NDATriageAgent.triage()`
  - Return `TriageResult` serialized as dict
- [ ] T292 Implement `@mcp.tool() discover_hidden_facts(document_id)`:
  - Fetch contract text, call `discover_hidden_facts()` from tools
  - Return `DiscoveryResult` serialized as dict
- [ ] T293 Implement `@mcp.tool() extract_obligations(document_id)`:
  - Fetch contract text via `ctx.get_document_text()`
  - Call LLM via `ctx.state.llm` (provider abstraction) with `OBLIGATION_SYSTEM_PROMPT`
  - Parse response with `_parse_lenient_json()`
  - Return `ObligationResult` dict
- [ ] T294 Implement `@mcp.tool() generate_risk_memo(document_id)`:
  - Fetch contract text via `ctx.get_document_text()`
  - Call LLM via `ctx.state.llm` (provider abstraction) with `RISK_MEMO_PROMPT`
  - Parse response with `_parse_lenient_json()`
  - Return `RiskMemoResult` dict
- [ ] T295 Implement `@mcp.tool() get_clause_gaps(document_id)`:
  - Query TrustGraph for missing mandatory fact slots
  - Return `ClauseGapResult` dict
- [ ] T296 Implement `@mcp.tool() generate_report(document_id, report_type)`:
  - Reuse `_report_template` and report generators from `stream.py`
  - Return `ReportResult` dict with HTML content

**Checkpoint**: All 13 MCP tools implemented and unit-tested.

---

### Phase 13e: MCP Resources (T297–T305)

**Purpose**: Implement 10 read-only resources for contract data access

#### Tests (T297–T298)

- [ ] T297 [P] Unit test for all resources in `tests/unit/test_mcp_resources.py`:
  - Test `contractos://contracts` returns list of contracts
  - Test `contractos://contracts/{id}` returns single contract
  - Test `contractos://contracts/{id}/facts` returns facts list
  - Test `contractos://contracts/{id}/clauses` returns clauses list
  - Test `contractos://contracts/{id}/bindings` returns bindings list
  - Test `contractos://contracts/{id}/graph` returns nodes + edges
  - Test `contractos://samples` returns manifest entries
  - Test `contractos://chat/history` returns sessions
  - Test `contractos://health` returns status dict
  - Test `contractos://playbook` returns playbook config
  - Mock: TrustGraph, EmbeddingIndex, manifest.json
- [ ] T298 [P] Unit test for resource error handling:
  - Test invalid document ID returns empty/error
  - Test empty TrustGraph returns empty lists

#### Implementation (T299–T305)

- [ ] T299 Create `src/contractos/mcp/resources.py` — resource module with `register_resources(mcp, ctx)`
- [ ] T300 [P] Implement `@mcp.resource("contractos://contracts")` and `@mcp.resource("contractos://contracts/{id}")`:
  - Query TrustGraph for contract list / single contract
  - Serialize as JSON
- [ ] T301 [P] Implement `@mcp.resource("contractos://contracts/{id}/facts")`:
  - Query TrustGraph `get_facts_by_document()`
  - Serialize facts with evidence and offsets
- [ ] T302 [P] Implement `@mcp.resource("contractos://contracts/{id}/clauses")` and `@mcp.resource("contractos://contracts/{id}/bindings")`:
  - Query TrustGraph for clauses and bindings
- [ ] T303 [P] Implement `@mcp.resource("contractos://contracts/{id}/graph")`:
  - Build TrustGraph view (nodes + edges) from facts, bindings, clauses, cross-refs
- [ ] T304 [P] Implement `@mcp.resource("contractos://samples")`, `@mcp.resource("contractos://chat/history")`, `@mcp.resource("contractos://health")`:
  - Samples: read `demo/samples/manifest.json`
  - Chat history: query session store
  - Health: return status, version, indexed count, embedding model
- [ ] T305 Implement `@mcp.resource("contractos://playbook")`:
  - Load default playbook via `load_default_playbook()`
  - Serialize PlaybookConfig as JSON

**Checkpoint**: All 10 MCP resources implemented and unit-tested.

---

### Phase 13f: MCP Prompts (T306–T313)

**Purpose**: Implement 5 reusable prompt workflows

#### Tests (T306–T307)

- [ ] T306 [P] Unit test for all prompts in `tests/unit/test_mcp_prompts.py`:
  - Test `full_contract_analysis` returns Message[] with correct tool sequence
  - Test `due_diligence_checklist` returns structured checklist template
  - Test `negotiation_prep` returns strategy-focused messages
  - Test `risk_summary` returns executive briefing messages
  - Test `clause_comparison` returns comparison workflow messages
  - Verify all prompts include parameter descriptions
- [ ] T307 [P] Unit test for prompt parameter validation:
  - Test missing required parameters raise appropriate errors

#### Implementation (T308–T313)

- [ ] T308 Create `src/contractos/mcp/prompts.py` — prompt module with `register_prompts(mcp, ctx)`
- [ ] T309 Implement `@mcp.prompt() full_contract_analysis(document_id)`:
  - Return Message[] guiding AI through: triage → review → obligations → risk memo → discover
  - Include instructions for synthesizing results
- [ ] T310 Implement `@mcp.prompt() due_diligence_checklist(document_id)`:
  - Return Message[] with structured due diligence template
  - Cover: parties, term, termination, liability, IP, confidentiality, compliance
- [ ] T311 Implement `@mcp.prompt() negotiation_prep(document_id)`:
  - Return Message[] for building negotiation strategy from review findings
  - Include playbook positions and redline suggestions
- [ ] T312 Implement `@mcp.prompt() risk_summary(document_id)`:
  - Return Message[] for executive risk briefing
  - Combine risk memo + obligations + discovery findings
- [ ] T313 Implement `@mcp.prompt() clause_comparison(doc_id_1, doc_id_2, clause_type)`:
  - Return Message[] for structured cross-contract comparison

**Checkpoint**: All 5 MCP prompts implemented and unit-tested.

---

### Phase 13g: Integration Tests & End-to-End (T314–T319)

**Purpose**: Verify MCP server works end-to-end with real protocol

#### Tests (T314–T318)

- [ ] T314 Create `tests/integration/test_mcp_server.py` — end-to-end MCP protocol tests:
  - Test server startup and tool listing (13 tools)
  - Test server startup and resource listing (10 resources)
  - Test server startup and prompt listing (5 prompts)
- [ ] T315 [P] Integration test: upload → query pipeline:
  - Load sample contract via `load_sample_contract`
  - Ask question via `ask_question`
  - Verify answer includes provenance
- [ ] T316 [P] Integration test: full analysis pipeline:
  - Load sample → triage → review → obligations → risk memo → report
  - Verify each tool returns expected structure
- [ ] T317 [P] Integration test: resource access:
  - Load sample → read `contractos://contracts` → verify contract listed
  - Read `contractos://contracts/{id}/facts` → verify facts returned
  - Read `contractos://health` → verify status ok
- [ ] T318 [P] Integration test: error handling:
  - Call tools with invalid document IDs → verify agent-friendly errors
  - Call `ask_question` with no indexed contracts → verify helpful error

#### Validation (T319)

- [ ] T319 Run MCP Inspector validation:
  - Start server in HTTP mode on port 8743
  - Connect MCP Inspector
  - Verify all 13 tools, 10 resources, 5 prompts visible
  - Execute `load_sample_contract` + `triage_nda` interactively

**Checkpoint**: All MCP protocol tests pass. Inspector validation complete.

---

### Phase 13h: Docker & Deployment (T320–T324)

**Purpose**: Add MCP server to Docker deployment, update documentation

- [ ] T320 Single-container deployment — both FastAPI + MCP HTTP in one container:
  - Create `entrypoint.sh` — starts MCP HTTP as background process (if `MCP_TRANSPORT=http`), then `exec` uvicorn as main process
  - Update `docker-compose.yml` — expose both ports (8742 FastAPI, 8743 MCP), add `MCP_TRANSPORT` and `MCP_PORT` env vars
  - Update `Dockerfile` — `COPY entrypoint.sh`, `RUN chmod +x`, set as `ENTRYPOINT`
  - Add header comment: "Container engine agnostic — works with Docker Desktop, Rancher Desktop, Podman, or any OCI runtime"
- [ ] T321 Update `Dockerfile` — ensure `mcp[cli]` is installed (already in pyproject.toml deps), expose MCP port
- [ ] T322 [P] Update `README.md` — add MCP server section:
  - Quick start for Cursor integration
  - Quick start for Claude Desktop
  - Docker deployment with MCP
  - Available tools, resources, prompts summary
- [ ] T323 [P] Update `docs/EXECUTIVE_SUMMARY.md` — add Phase 13 MCP section
- [ ] T324 [P] Update `tests/reports/QA_TEST_REPORT.md` — add MCP test results

**Checkpoint**: Docker deployment includes MCP server. Documentation updated.

---

### Phase 13i: Polish & Cross-Cutting (T325–T329)

**Purpose**: Final quality, performance, and usability improvements

- [ ] T325 Add structured logging to all MCP tools (tool name, document_id, timing)
- [ ] T326 Add `ctx.report_progress()` calls to long-running tools (review, triage, discover, obligations, risk_memo)
- [ ] T327 Performance test: measure tool response times against targets (<5s queries, <30s analysis)
- [ ] T328 Error message review: ensure all errors are agent-friendly (guide AI to fix the issue)
- [ ] T329 Run full test suite (`pytest tests/`) — verify no regressions, update total test count

**Checkpoint**: ✅ Phase 13 complete. ContractOS MCP server operational with 13 tools, 10 resources, 5 prompts. Cursor + Claude Desktop integration verified.

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
| Phase 8d (Sample Contracts) | 7 | 0 | 0 | 7 |
| Phase 9 (Polish) | 2 | 1 | 0 | 3 |
| Phase 10a (Playbook Models) | 3 | 0 | 0 | 3 |
| Phase 10b (ComplianceAgent) | 1 | 1 | 0 | 2 |
| Phase 10c (DraftAgent) | 1 | 1 | 0 | 2 |
| Phase 10d (NDA Triage) | 2 | 1 | 0 | 3 |
| Phase 12 (SSE Streaming + Bug Fixes) | 19 | 17 | 0 | 36 |
| **Phase 13 (MCP Server)** | **~35** | **~10** | **0** | **~45** |
| **Phase 14 (Deep Extraction)** | **47** | **17** | **0** | **64** |
| **Total** | **~175** | **~66** | **6** | **~247** |

## Task Summary

| Metric | Value |
|--------|-------|
| Total tasks | 337 |
| Test tasks | ~145 (44%) |
| Implementation tasks | ~184 (56%) |
| Phase 1 (Setup) | 5 tasks |
| Phase 2 (Foundation) | 35 tasks |
| Phase 3–7 (User Stories) | 71 tasks |
| Phase 7a–7f (Enhancements) | 36 tasks |
| Phase 8a (Browser Copilot) | 3 tasks |
| Phase 8b (Discovery + Highlighting Fix) | 6 tasks |
| Phase 8c (Conversation Context) | 7 tasks |
| Phase 8d (Sample Contracts) | 5 tasks |
| Phase 8 (Word Add-in, superseded) | 16 tasks |
| Phase 9 (Polish) | 11 tasks |
| **Phase 10a (Playbook Models)** | **8 tasks** |
| **Phase 10b (ComplianceAgent)** | **9 tasks** |
| **Phase 10c (DraftAgent)** | **6 tasks** |
| **Phase 10d (NDA Triage)** | **10 tasks** |
| **Phase 10e (Copilot UI)** | **5 tasks** |
| **Phase 10f (Polish)** | **5 tasks** |
| **Phase 12 (SSE Streaming)** | **18 tasks** |
| **Phase 13 (MCP Server)** | **69 tasks (T261–T329)** |
| Total passing tests | 691 + ~45 MCP + ~64 deep extraction |
| Real NDA documents tested | 50 (from ContractNLI) |
| Deployment configs | 5 (Docker, Docker+MCP, Railway, Render, Procfile) |
| Parallelizable tasks | ~95 (29%) |
| MVP scope (through Phase 5) | 86 tasks |
| Full scope (through Phase 8d) | 195 tasks |
| Phase 10 scope | 43 tasks (T200–T242) |
| Phase 12 scope | 18 tasks (T243–T260) |
| Phase 13 scope | 69 tasks (T261–T329) |
| Phase 14 scope | 8 tasks (T330–T337) |

---

## Dependencies & Execution Order (Phase 13)

### Phase Dependencies

```
Phase 13a (Setup)           ─── BLOCKS ALL ──→ Phase 13b–13f
Phase 13b (Ingestion Tools) ─── BLOCKS ──────→ Phase 13c, 13d (tools need upload first)
Phase 13c (Q&A Tools)       ─── independent ─→ can parallel with 13d
Phase 13d (Analysis Tools)  ─── independent ─→ can parallel with 13c
Phase 13e (Resources)       ─── independent ─→ can parallel with 13b–13d
Phase 13f (Prompts)         ─── independent ─→ can parallel with 13b–13e
Phase 13g (Integration)     ─── REQUIRES ────→ 13b + 13c + 13d + 13e + 13f
Phase 13h (Docker/Docs)     ─── REQUIRES ────→ 13g
Phase 13i (Polish)          ─── REQUIRES ────→ 13h
```

### Parallel Opportunities

- **13b + 13e + 13f** can run in parallel after 13a completes
- **13c + 13d** can run in parallel after 13b completes
- Within each sub-phase, tasks marked [P] can run in parallel
- Test tasks within a sub-phase can all run in parallel

---

## Phase 14: Deep Extraction — Real-World Contract Quality (T330–T337)

**Problem:** Real-world contracts (CDK50014.pdf, SERVICE AGREEMENT 2.docx) produce only dates/amounts as facts, with **zero clauses**, **zero bindings**, and **zero cross-references**. Root causes:

1. PDF parser never sets `heading_level` → clause classifier skips all paragraphs
2. DOCX parser only recognizes Word `Heading*` styles → bold/custom-styled headings ignored
3. Definition pattern only matches straight `"` quotes → smart quotes `\u201c\u201d` missed
4. Alias pattern requires "hereinafter" phrasing → common `Entity ("Alias")` missed
5. Cascade failure: no clauses → no cross-refs → no clause-body facts → no mandatory slots

**Files modified:** `contract_patterns.py`, `pdf_parser.py`, `docx_parser.py`, `clause_classifier.py`, `alias_detector.py`, `binding_resolver.py`, `fact_extractor.py`

### Phase 14a — Smart Quote Normalization (Foundation)

- [X] **T330** — Normalize smart/curly quotes before pattern matching `[contract_patterns.py]`
  - Add `normalize_quotes(text)` function: `\u201c\u201d` → `"`, `\u2018\u2019` → `'`, `\u2013\u2014` → `-`
  - Call at top of `extract_patterns()` and export for use by other modules
  - Ensures all downstream patterns work with normalized text
  - **Test:** Verify definition/alias patterns match smart-quoted text

### Phase 14b — Parser Heading Detection [P]

- [X] **T331** — PDF heading detection via font-size/bold heuristics `[pdf_parser.py]`
  - Use PyMuPDF `page.get_text("dict")` to get font size and flags per span
  - Detect headings by: (a) font size > median + threshold, (b) bold flag, (c) ALL-CAPS short text
  - Assign `heading_level` based on font size tiers (largest=1, next=2, etc.)
  - Preserve existing block-based extraction as fallback
  - **Test:** CDK50014.pdf should produce heading paragraphs for DEFINITIONS, TERM, INDEMNIFICATION, etc.

- [X] **T332** — DOCX bold-as-heading fallback `[docx_parser.py]`
  - If document has zero `Heading*` styles, re-scan paragraphs for bold formatting
  - Detect bold: check `w:b` in paragraph `rPr` or all runs' `rPr`
  - Short bold paragraph (< 80 chars, no period at end or ends with `.` as heading style) → `heading_level=1`
  - Only activate when zero headings found via style detection (avoid false positives in well-styled docs)
  - **Test:** SERVICE AGREEMENT 2.docx should produce headings for Term and Termination, Confidentiality, Indemnification, etc.

### Phase 14c — Broader Pattern Matching [P]

- [X] **T333** — Broader definition patterns `[contract_patterns.py, binding_resolver.py]`
  - Extend `DEFINITION_PATTERN` to match smart quotes and single quotes
  - Add new `PARENTHETICAL_DEFINITION_PATTERN`: `(the "Term")` or `("Term")` after descriptive text
  - Add new `INLINE_DEFINITION_PATTERN`: `"Term" shall mean` with broader verb list (designates, constitutes, includes)
  - Update `binding_resolver._extract_definition_bindings` to use all patterns
  - **Test:** "Affiliate" shall mean..., (the "Agreement"), ("Service Provider") all match

- [X] **T334** — Broader alias/entity patterns `[contract_patterns.py, alias_detector.py]`
  - Add `PARTY_ALIAS_PATTERN`: `Entity Name, a <jurisdiction> <entity_type> ("Alias")`
  - Support: `Corp ("X")`, `LLC ("X")`, `Inc. ("X")`, `Ltd ("X")`, `Pvt Ltd ("X")`
  - Support both straight and smart quotes in alias capture
  - **Test:** `Zycus Pvt Ltd a Michigan corporation ("Service Provider')` matches

### Phase 14d — Clause Classifier Fallback

- [X] **T335** — Structural heading detection when `heading_level` is None `[clause_classifier.py]`
  - Add `classify_paragraphs_with_fallback()` that wraps existing `classify_paragraphs()`
  - If zero clauses from heading-based classification, run structural fallback:
    - Numbered paragraphs: `^\d+\.?\s+[A-Z]` (e.g., "1. DEFINITIONS", "12. INSURANCE")
    - ALL-CAPS short lines: `^[A-Z\s]{4,60}$` (e.g., "CONFIDENTIALITY", "WARRANTIES")
    - Bold-marked paragraphs (from parser heading_level detection)
  - Create synthetic `heading_level=1` for matched paragraphs and re-run classification
  - Update `fact_extractor.py` to call the fallback version
  - **Test:** Contracts with no Word heading styles still produce clauses

### Phase 14e — Integration & Validation

- [X] **T336** — Unit tests for all new extraction capabilities `[tests/unit/]`
  - Test `normalize_quotes()` with all Unicode quote variants
  - Test PDF heading detection with mock font data
  - Test DOCX bold fallback with mock XML
  - Test broadened definition/alias patterns against real contract text
  - Test clause classifier fallback with numbered/ALL-CAPS paragraphs
  - Target: 15+ new unit tests

- [X] **T337** — End-to-end validation against real contracts `[tests/integration/]`
  - Run CDK50014.pdf through pipeline → verify clauses > 0, bindings > 0
  - Run SERVICE AGREEMENT 2.docx through pipeline → verify clauses > 0, bindings > 0
  - Compare before/after extraction counts
  - Verify no regression on existing sample contracts (simple_nda.pdf, etc.)
  - **Acceptance criteria:** Both real contracts produce ≥5 clauses and ≥3 bindings

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
