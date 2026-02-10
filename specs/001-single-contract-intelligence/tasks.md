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

## Phase 7: User Story 5 — Workspace Persistence (P2)

**Goal**: Documents and sessions persist across restarts. Previously parsed documents load instantly.

**Independent Test**: Parse a document, restart server, verify facts load from TrustGraph without re-parsing.

### Unit Tests (write FIRST)

- [ ] T102 [P] [US5] Write unit test for document change detection in `tests/unit/test_change_detection.py` — compute file hash; modify file; verify hash mismatch detected; verify same file produces same hash
- [ ] T103 [P] [US5] Write unit test for workspace document association in `tests/unit/test_workspace_documents.py` — add document to workspace; remove document; list documents; verify document appears in only associated workspaces

### Integration Tests (write FIRST)

- [ ] T104 [P] [US5] Write integration test for workspace persistence in `tests/integration/test_workspace_persistence.py` — index document → create workspace → add document → create reasoning session → "restart" (close and recreate TrustGraph/WorkspaceStore from same SQLite file) → verify all data persists: facts, bindings, clauses, workspace, sessions
- [ ] T105 [P] [US5] Write integration test for session history in `tests/integration/test_session_history.py` — create 5 reasoning sessions → retrieve workspace → verify sessions listed in reverse chronological order with query text and answer summary

### Contract Tests (write FIRST)

- [ ] T106 [P] [US5] Write contract tests for workspace API in `tests/contract/test_workspace_api.py` — `POST /workspaces` creates workspace; `GET /workspaces/{id}` returns workspace with indexed_documents and recent_sessions; verify document-workspace association endpoints; error cases: workspace not found (404)

### Implementation

- [ ] T107 [US5] Implement workspace endpoints — `POST /workspaces`, `GET /workspaces/{id}` in `src/contractos/api/routes/workspace.py`
- [ ] T108 [US5] Implement document-workspace association — add/remove documents to workspace, list workspace contents
- [ ] T109 [US5] Implement reasoning session history — store completed sessions, list recent sessions per workspace
- [ ] T110 [US5] Implement document change detection — compare file_hash on open; if changed, offer re-parse
- [ ] T111 [US5] Implement session retrieval by workspace — `GET /workspaces/{id}` includes recent_sessions per copilot-api.md

**Checkpoint**: All US5 tests pass. Workspace persistence works. Restarting the server retains all indexed data and session history.

---

## Phase 8: Word Copilot Add-in (P2)

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
| Phase 9 (Polish) | 2 | 1 | 0 | 3 |
| **Total** | **40** | **11** | **6** | **57** |

## Task Summary

| Metric | Value |
|--------|-------|
| Total tasks | 138 |
| Test tasks | 57 (41%) |
| Implementation tasks | 81 (59%) |
| Phase 1 (Setup) | 5 tasks |
| Phase 2 (Foundation) | 35 tasks |
| Phase 3–7 (User Stories) | 71 tasks |
| Phase 8 (Copilot) | 16 tasks |
| Phase 9 (Polish) | 11 tasks |
| Parallelizable tasks | 55 (40%) |
| MVP scope (through Phase 5) | 86 tasks |
| Full scope (through Phase 8) | 127 tasks |

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
