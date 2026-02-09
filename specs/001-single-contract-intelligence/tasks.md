# Tasks: Single-Contract Intelligence

**Input**: Design documents from `specs/001-single-contract-intelligence/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md
**Tech Stack**: Python 3.12, FastAPI, python-docx, PyMuPDF, pdfplumber, spaCy, Anthropic SDK, SQLite, Pydantic
**Branch**: `001-single-contract-intelligence`

---

## Phase 1: Setup (Project Infrastructure)

**Purpose**: Initialize the Python project, dependency management, and base structure.

- [ ] T001 Create project directory structure per plan.md (`src/contractos/`, `tests/`, `config/`, `copilot/`)
- [ ] T002 Initialize Python project with `pyproject.toml` — dependencies: python-docx, pymupdf, pdfplumber, spacy, anthropic, fastapi, uvicorn, pydantic, pydantic-settings, pytest, httpx
- [ ] T003 [P] Create `config/default.yaml` with all configuration keys from research.md §8
- [ ] T004 [P] Create `.gitignore` update for Python (.venv, __pycache__, *.db, .contractos/)
- [ ] T005 [P] Configure ruff (linter/formatter) and mypy (type checking) in `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models, storage, LLM abstraction, and configuration that ALL user stories depend on.

**CRITICAL**: No user story work can begin until this phase is complete.

### Data Models (Truth Model)

- [ ] T006 [P] Implement Fact + FactEvidence + FactType + EntityType Pydantic models in `src/contractos/models/fact.py`
- [ ] T007 [P] Implement Binding + BindingType + BindingScope Pydantic models in `src/contractos/models/binding.py`
- [ ] T008 [P] Implement Inference + InferenceType Pydantic models in `src/contractos/models/inference.py`
- [ ] T009 [P] Implement Opinion + OpinionType + Severity Pydantic models in `src/contractos/models/opinion.py` (schema only, not used in Phase 1)
- [ ] T010 [P] Implement Contract document metadata model in `src/contractos/models/document.py`
- [ ] T011 [P] Implement ProvenanceChain + ProvenanceNode models in `src/contractos/models/provenance.py`
- [ ] T012 [P] Implement Query + QueryResult + QueryScope models in `src/contractos/models/query.py`
- [ ] T013 [P] Implement Workspace + ReasoningSession + SessionStatus models in `src/contractos/models/workspace.py`

### Storage (TrustGraph)

- [ ] T014 Create SQLite schema in `src/contractos/fabric/schema.sql` per data-model.md
- [ ] T015 Implement TrustGraph class in `src/contractos/fabric/trust_graph.py` — CRUD for facts, bindings, inferences; query by document_id, by type, by term; ensure typed outputs
- [ ] T016 Implement WorkspaceStore in `src/contractos/workspace/manager.py` — CRUD for workspaces and reasoning sessions
- [ ] T017 Write unit tests for TrustGraph in `tests/unit/test_trust_graph.py` — verify type enforcement, CRUD, indexes

### Configuration

- [ ] T018 Implement config loading with Pydantic Settings in `src/contractos/config.py` — load from YAML, override with env vars, validate all fields

### LLM Abstraction

- [ ] T019 Implement LLMProvider abstract base class in `src/contractos/llm/provider.py` — `generate()`, `classify()`, `structured_output()` methods
- [ ] T020 Implement ClaudeProvider in `src/contractos/llm/claude.py` — uses Anthropic SDK, respects config (model, temperature, max_tokens)
- [ ] T021 Write unit test for LLM provider selection in `tests/unit/test_llm_provider.py`

### API Server Shell

- [ ] T022 Implement FastAPI application skeleton in `src/contractos/api/server.py` — CORS, health endpoint, router mounting
- [ ] T023 [P] Implement health endpoint (`GET /health`) in `src/contractos/api/routes/health.py`
- [ ] T024 [P] Implement config endpoint (`GET /config`) in `src/contractos/api/routes/health.py`

**Checkpoint**: Foundation ready — all data models defined, storage operational, LLM abstracted, API shell running. User story implementation can begin.

---

## Phase 3: User Story 1 — Document Ingestion & Fact Extraction (P1) MVP

**Goal**: Parse a Word or PDF contract and extract structured facts with precise evidence.

**Independent Test**: Upload a procurement contract; verify parties, dates, amounts, products, locations extracted with correct offsets.

### Tests

- [ ] T025 [P] [US1] Create test fixture contracts in `tests/fixtures/` — simple-procurement.docx (manually crafted with known entities), simple-nda.pdf
- [ ] T026 [P] [US1] Write unit test for Word parser in `tests/unit/test_docx_parser.py` — entity counts, offset accuracy, determinism
- [ ] T027 [P] [US1] Write unit test for PDF parser in `tests/unit/test_pdf_parser.py` — entity counts, table extraction, page numbers
- [ ] T028 [P] [US1] Write integration test for document pipeline in `tests/integration/test_fact_extraction.py` — parse → extract → store → retrieve

### Implementation

- [ ] T029 [US1] Implement Word document parser in `src/contractos/tools/docx_parser.py` — paragraphs, tables, headings, structural paths, character offsets
- [ ] T030 [US1] Implement PDF document parser in `src/contractos/tools/pdf_parser.py` — text with offsets via PyMuPDF, tables via pdfplumber, page numbers
- [ ] T031 [US1] Implement FactExtractor in `src/contractos/tools/fact_extractor.py` — orchestrates parser + spaCy NER + custom patterns; returns `[FactResult]`
- [ ] T032 [US1] Implement custom spaCy patterns for contract entities — definition patterns, section references, duration patterns in `src/contractos/tools/contract_patterns.py`
- [ ] T033 [US1] Implement clause classifier in `src/contractos/tools/clause_classifier.py` — heading-based detection + LLM-assisted classification for ambiguous sections
- [ ] T034 [US1] Implement document upload endpoint (`POST /documents`) in `src/contractos/api/routes/documents.py` — accept file, trigger parse, return 202
- [ ] T035 [US1] Implement document status endpoint (`GET /documents/{id}`) in `src/contractos/api/routes/documents.py`
- [ ] T036 [US1] Implement facts endpoint (`GET /documents/{id}/facts`) in `src/contractos/api/routes/documents.py` — with type/entity_type filters, pagination
- [ ] T037 [US1] Implement background parsing task — async processing of uploaded documents, progress tracking, error handling
- [ ] T038 [US1] Verify determinism: re-parse same document, assert identical fact set in `tests/unit/test_determinism.py`

**Checkpoint**: Document parsing works end-to-end. Upload a contract, get facts back. The core data pipeline is operational.

---

## Phase 4: User Story 2 — Binding Resolution (P1)

**Goal**: Identify definition clauses and resolve defined terms as Bindings throughout the document.

**Independent Test**: Parse a contract with 10+ defined terms; verify all captured with correct mappings.

### Tests

- [ ] T039 [P] [US2] Write unit test for BindingResolver in `tests/unit/test_binding_resolver.py` — definition patterns, assignment patterns, scope
- [ ] T040 [P] [US2] Write integration test for bindings pipeline in `tests/integration/test_binding_resolution.py` — parse → extract facts → resolve bindings → store → query

### Implementation

- [ ] T041 [US2] Implement BindingResolver in `src/contractos/tools/binding_resolver.py` — detect "X shall mean Y" patterns, assignment clauses, scope determination; returns `[BindingResult]`
- [ ] T042 [US2] Implement binding persistence in TrustGraph — store, retrieve, query by term, check overrides
- [ ] T043 [US2] Implement bindings endpoint (`GET /documents/{id}/bindings`) in `src/contractos/api/routes/documents.py`
- [ ] T044 [US2] Integrate BindingResolver into document parsing pipeline — after FactExtractor, before document is marked "indexed"
- [ ] T045 [US2] Implement binding lookup utility — given a term in a document, resolve through binding chain, return `BindingResult` or "unresolved"

**Checkpoint**: Document parsing now produces both facts AND bindings. Defined terms are resolved and queryable.

---

## Phase 5: User Story 3 — Single-Document Q&A (P1) MVP

**Goal**: Answer natural language questions about a contract using facts, bindings, and LLM-generated inferences.

**Independent Test**: Ask 10 benchmark questions; verify answers reference clauses, include confidence, and have provenance chains.

### Tests

- [ ] T046 [P] [US3] Write unit test for InferenceEngine in `tests/unit/test_inference_engine.py` — verify fact references, confidence range, reasoning chain
- [ ] T047 [P] [US3] Write integration test for Q&A pipeline in `tests/integration/test_document_qa.py` — parse → query → verify answer + provenance
- [ ] T048 [P] [US3] Write test for "not found" behavior in `tests/unit/test_not_found.py` — verify system returns "not found" with searched sections, not hallucination

### Implementation

- [ ] T049 [US3] Implement InferenceEngine in `src/contractos/tools/inference_engine.py` — takes facts + bindings + query, calls LLM, returns `[InferenceResult]` with confidence and reasoning chain
- [ ] T050 [US3] Implement confidence calculation in `src/contractos/tools/confidence.py` — heuristic: evidence count, direct vs. inferred, binding coverage
- [ ] T051 [US3] Implement DocumentAgent in `src/contractos/agents/document_agent.py` — orchestrates: check index → search TrustGraph → resolve bindings → generate inference → build provenance → return result
- [ ] T052 [US3] Implement ProvenanceChain builder in `src/contractos/models/provenance.py` — collects facts, bindings, inferences used during reasoning into a chain
- [ ] T053 [US3] Implement query endpoint (`POST /query`) in `src/contractos/api/routes/query.py` — accept question + document_ids, return answer with provenance
- [ ] T054 [US3] Implement SSE streaming for query responses in `src/contractos/api/routes/query.py` — stream partial results (searching → reasoning → answer)
- [ ] T055 [US3] Implement "not found" handling — when no relevant facts/inferences exist, return "not found" with list of sections searched
- [ ] T056 [US3] Implement query session retrieval (`GET /query/sessions/{id}`) in `src/contractos/api/routes/query.py`
- [ ] T057 [US3] Implement prompt templates for InferenceEngine — structured prompts for Q&A, clause classification, confidence estimation in `src/contractos/tools/prompts.py`

**Checkpoint**: Core value proposition works. User asks a question, gets a grounded answer with provenance. This is the MVP.

---

## Phase 6: User Story 4 — Provenance Display (P2)

**Goal**: Every answer includes an expandable provenance chain; clicking a fact navigates to the document location.

**Independent Test**: Ask a question producing an inference; verify the provenance chain shows facts with locations, confidence indicator, and readable reasoning.

### Implementation

- [ ] T058 [US4] Ensure all API responses include full ProvenanceChain in JSON per api-server.md contract
- [ ] T059 [US4] Implement provenance formatting — human-readable summaries for each node, navigable document locations
- [ ] T060 [US4] Add confidence display metadata — map 0.0–1.0 to high/medium/low label with color coding in API response

**Checkpoint**: Provenance is fully structured in the API. The Copilot (Phase 8) will consume this to render the UI.

---

## Phase 7: User Story 5 — Workspace Persistence (P2)

**Goal**: Documents and sessions persist across restarts. Previously parsed documents load instantly.

**Independent Test**: Parse a document, restart server, verify facts load from TrustGraph without re-parsing.

### Tests

- [ ] T061 [P] [US5] Write integration test for workspace persistence in `tests/integration/test_workspace_persistence.py` — index document, "restart" (recreate objects), verify data persists
- [ ] T062 [P] [US5] Write test for document change detection in `tests/unit/test_change_detection.py` — modify file, verify hash mismatch detected

### Implementation

- [ ] T063 [US5] Implement workspace endpoints — `POST /workspaces`, `GET /workspaces/{id}` in `src/contractos/api/routes/workspace.py`
- [ ] T064 [US5] Implement document-workspace association — add/remove documents to workspace, list workspace contents
- [ ] T065 [US5] Implement reasoning session history — store completed sessions, list recent sessions per workspace
- [ ] T066 [US5] Implement document change detection — compare file_hash on open; if changed, offer re-parse
- [ ] T067 [US5] Implement session retrieval by workspace — `GET /workspaces/{id}` includes recent_sessions per copilot-api.md

**Checkpoint**: Workspace persistence works. Restarting the server retains all indexed data and session history.

---

## Phase 8: Word Copilot Add-in (P2)

**Goal**: A working Word sidebar that communicates with the ContractOS server.

### Implementation

- [ ] T068 [P] Initialize Office Add-in project in `copilot/` — package.json, TypeScript config, React, Office JS API
- [ ] T069 [P] Create Office Add-in manifest (`copilot/manifest.xml`) — sidebar taskpane, localhost development
- [ ] T070 Implement API client service in `copilot/src/services/api-client.ts` — all endpoints from api-server.md, SSE streaming support
- [ ] T071 Implement sidebar layout component in `copilot/src/taskpane/App.tsx` — per copilot-api.md UI wireframe
- [ ] T072 Implement Q&A input component in `copilot/src/components/QueryInput.tsx` — text input with submit, loading state
- [ ] T073 Implement answer display component in `copilot/src/components/AnswerCard.tsx` — answer text, confidence indicator, expandable provenance
- [ ] T074 Implement provenance chain component in `copilot/src/components/ProvenanceChain.tsx` — fact nodes with "Go to clause" links, binding nodes, inference nodes, reasoning summary
- [ ] T075 Implement document navigation — use Office JS API to navigate to char ranges when "Go to clause" is clicked
- [ ] T076 Implement document status bar — show indexed/parsing/not-indexed status, fact/binding counts
- [ ] T077 Implement session history component in `copilot/src/components/SessionHistory.tsx` — list recent Q&A sessions
- [ ] T078 Implement error handling — server not running, LLM unavailable, unsupported format, per copilot-api.md error table
- [ ] T079 Implement auto-detection of document — on sidebar open, check if current document is indexed, prompt if not

**Checkpoint**: End-to-end system works. Open contract in Word, ask questions via sidebar, get answers with provenance.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Quality, performance, and developer experience improvements.

- [ ] T080 [P] Create CLI interface (`contractos` command) — `serve`, `parse`, `query`, `facts`, `bindings` subcommands in `src/contractos/cli.py`
- [ ] T081 [P] Set up COBench v0.1 benchmark framework in `tests/benchmark/cobench_v01.py` — 20 annotated contracts, 100 queries, accuracy + confidence calibration metrics
- [ ] T082 [P] Add structured logging (JSON format) with audit trail in `src/contractos/logging.py`
- [ ] T083 Create provenance middleware — ensure NO API response from `/query` lacks a ProvenanceChain in `src/contractos/api/middleware/provenance.py`
- [ ] T084 Add truth model enforcement middleware — reject any tool output that is not typed as Fact/Binding/Inference/Opinion
- [ ] T085 Performance optimization — ensure <5s query on cached documents, profile and optimize hot paths
- [ ] T086 [P] Write comprehensive README with setup instructions referencing quickstart.md
- [ ] T087 Run full test suite, fix any failures, verify all acceptance scenarios from spec.md

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

### Parallel Opportunities

- **Phase 2**: All model tasks (T006–T013) can run in parallel. Storage (T014–T017) after models.
- **Phase 3**: Test fixtures (T025) parallel with test writing (T026–T028). Implementation sequential.
- **Phase 7 can start alongside Phase 3–5** — workspace persistence is independent of parsing/Q&A.
- **Phase 8 can start T068–T069 alongside Phase 3–5** — scaffold the add-in project early.
- **Phase 9**: T080–T082 are all parallel with each other.

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

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 87 |
| Phase 1 (Setup) | 5 tasks |
| Phase 2 (Foundation) | 19 tasks |
| Phase 3–7 (User Stories) | 43 tasks |
| Phase 8 (Copilot) | 12 tasks |
| Phase 9 (Polish) | 8 tasks |
| Parallelizable tasks | 32 (37%) |
| MVP scope (through Phase 5) | 53 tasks |
| Full scope (through Phase 8) | 79 tasks |
