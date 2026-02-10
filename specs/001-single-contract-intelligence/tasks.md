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

## Phase 1: Setup (Project Infrastructure)

**Purpose**: Initialize the Python project, dependency management, and base structure.

- [ ] T001 Create project directory structure per plan.md (`src/contractos/`, `tests/unit/`, `tests/integration/`, `tests/contract/`, `tests/benchmark/`, `tests/fixtures/`, `tests/mocks/`, `config/`, `copilot/`)
- [ ] T002 Initialize Python project with `pyproject.toml` — dependencies: python-docx, pymupdf, pdfplumber, spacy, anthropic, fastapi, uvicorn, pydantic, pydantic-settings, pytest, pytest-asyncio, pytest-cov, httpx, respx (HTTP mocking), factory-boy (fixtures)
- [ ] T003 [P] Create `config/default.yaml` with all configuration keys from research.md §9
- [ ] T004 [P] Create `.gitignore` update for Python (.venv, __pycache__, *.db, .contractos/)
- [ ] T005 [P] Configure ruff (linter/formatter), mypy (type checking), and pytest (coverage threshold 90%) in `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models, storage, LLM abstraction, and configuration that ALL user stories depend on.

**CRITICAL**: No user story work can begin until this phase is complete.

### Test Infrastructure

- [ ] T006 Create test fixtures: manually crafted `tests/fixtures/simple-procurement.docx` (30 known entities, 8 clauses, 5 defined terms, 4 cross-references, 2 tables) and `tests/fixtures/simple-nda.pdf` (10 entities, 3 clauses, 2 defined terms)
- [ ] T007 [P] Create `tests/conftest.py` with shared fixtures: in-memory SQLite TrustGraph, sample Fact/Binding/Inference/Clause factories, test config
- [ ] T008 [P] Create `tests/mocks/llm_mock.py` — mock LLM provider that returns deterministic responses for known prompts (clause classification, inference generation, confidence estimation)

### Data Models — Tests First

- [ ] T009 [P] Write unit tests for Fact model in `tests/unit/test_models_fact.py` — validate FactType enum, FactEvidence required fields, CROSS_REFERENCE type, serialization/deserialization, immutability constraints
- [ ] T010 [P] Write unit tests for Binding model in `tests/unit/test_models_binding.py` — validate BindingType enum, scope constraints, override chain, serialization
- [ ] T011 [P] Write unit tests for Inference model in `tests/unit/test_models_inference.py` — validate confidence range [0.0–1.0], required supporting_fact_ids, InferenceType enum
- [ ] T012 [P] Write unit tests for Clause model in `tests/unit/test_models_clause.py` — validate ClauseTypeEnum, CrossReference resolution, ReferenceEffect enum, ClauseFactSlot status transitions
- [ ] T013 [P] Write unit tests for ProvenanceChain model in `tests/unit/test_models_provenance.py` — validate chain construction, node types, empty chain rejection
- [ ] T014 [P] Write unit tests for Query/QueryResult model in `tests/unit/test_models_query.py` — validate QueryScope, answer_type enum, provenance required on all results
- [ ] T015 [P] Write unit tests for Workspace/ReasoningSession model in `tests/unit/test_models_workspace.py` — validate SessionStatus transitions, document_ids list

### Data Models — Implementation

- [ ] T016 [P] Implement Fact + FactEvidence + FactType (incl. CROSS_REFERENCE) + EntityType Pydantic models in `src/contractos/models/fact.py`
- [ ] T017 [P] Implement Binding + BindingType + BindingScope Pydantic models in `src/contractos/models/binding.py`
- [ ] T018 [P] Implement Inference + InferenceType Pydantic models in `src/contractos/models/inference.py`
- [ ] T019 [P] Implement Opinion + OpinionType + Severity Pydantic models in `src/contractos/models/opinion.py` (schema only, not used in Phase 1)
- [ ] T020 [P] Implement Contract document metadata model in `src/contractos/models/document.py`
- [ ] T021 [P] Implement Clause + ClauseTypeEnum + CrossReference + ReferenceType + ReferenceEffect Pydantic models in `src/contractos/models/clause.py`
- [ ] T022 [P] Implement ClauseTypeSpec + MandatoryFactSpec + ClauseFactSlot + SlotStatus Pydantic models in `src/contractos/models/clause_type.py`
- [ ] T023 [P] Implement ProvenanceChain + ProvenanceNode models in `src/contractos/models/provenance.py`
- [ ] T024 [P] Implement Query + QueryResult + QueryScope models in `src/contractos/models/query.py`
- [ ] T025 [P] Implement Workspace + ReasoningSession + SessionStatus models in `src/contractos/models/workspace.py`
- [ ] T026 Create default Clause Type Registry YAML in `config/clause_types.yaml` — 14 clause types with mandatory/optional fact schemas per truth-model.md §1b

### Storage (TrustGraph) — Tests First

- [ ] T027 Write unit tests for TrustGraph in `tests/unit/test_trust_graph.py` — CRUD for facts (insert, get by id, get by document, get by type, get by entity_type); CRUD for bindings (insert, get by term, get by document); CRUD for inferences; CRUD for clauses; CRUD for cross-references; CRUD for clause_fact_slots; type enforcement (reject untyped); idempotent re-insert; cascade delete by document_id
- [ ] T028 Write unit tests for WorkspaceStore in `tests/unit/test_workspace_store.py` — CRUD for workspaces, add/remove documents, session creation, session history retrieval, session status transitions

### Storage — Implementation

- [ ] T029 Create SQLite schema in `src/contractos/fabric/schema.sql` per data-model.md — includes contracts, facts, bindings, inferences, clauses, cross_references, clause_type_registry, clause_fact_slots, workspaces, reasoning_sessions tables
- [ ] T030 Implement TrustGraph class in `src/contractos/fabric/trust_graph.py` — all CRUD operations, query methods, type enforcement
- [ ] T031 Implement WorkspaceStore in `src/contractos/workspace/manager.py` — all CRUD operations, session lifecycle

### Configuration — Tests First

- [ ] T032 Write unit tests for config loading in `tests/unit/test_config.py` — load from YAML, env var override, missing required fields raise error, default values, clause_types registry path resolution

### Configuration — Implementation

- [ ] T033 Implement config loading with Pydantic Settings in `src/contractos/config.py` — load from YAML, override with env vars, validate all fields, load clause type registry

### LLM Abstraction — Tests First

- [ ] T034 Write unit tests for LLM provider in `tests/unit/test_llm_provider.py` — provider selection by config, ClaudeProvider initialization, mock generate/classify calls, error handling (API timeout, rate limit, invalid response)

### LLM Abstraction — Implementation

- [ ] T035 Implement LLMProvider abstract base class in `src/contractos/llm/provider.py` — `generate()`, `classify()`, `structured_output()` methods
- [ ] T036 Implement ClaudeProvider in `src/contractos/llm/claude.py` — uses Anthropic SDK, respects config (model, temperature, max_tokens)

### API Server Shell — Tests First

- [ ] T037 Write contract tests for health/config endpoints in `tests/contract/test_health_api.py` — `GET /health` returns status, version, llm_status; `GET /config` returns provider, model, pipeline

### API Server Shell — Implementation

- [ ] T038 Implement FastAPI application skeleton in `src/contractos/api/server.py` — CORS, health endpoint, router mounting, error handlers
- [ ] T039 [P] Implement health endpoint (`GET /health`) in `src/contractos/api/routes/health.py`
- [ ] T040 [P] Implement config endpoint (`GET /config`) in `src/contractos/api/routes/health.py`

**Checkpoint**: Foundation ready — all data models defined and tested, storage operational and tested, LLM abstracted and tested, API shell running and tested. User story implementation can begin.

---

## Phase 3: User Story 1 — Document Ingestion & Fact Extraction (P1) MVP

**Goal**: Parse a Word or PDF contract and extract structured facts with precise evidence.

**Independent Test**: Upload a procurement contract; verify parties, dates, amounts, products, locations extracted with correct offsets.

### Unit Tests (write FIRST — must FAIL before implementation)

- [ ] T041 [P] [US1] Write unit test for Word parser in `tests/unit/test_docx_parser.py` — parse simple-procurement.docx; verify paragraph count, heading extraction, table cell extraction with row/column metadata, character offset accuracy, structural path generation
- [ ] T042 [P] [US1] Write unit test for PDF parser in `tests/unit/test_pdf_parser.py` — parse simple-nda.pdf; verify text extraction with offsets, table extraction via pdfplumber, page number assignment, handling of scanned PDF (error)
- [ ] T043 [P] [US1] Write unit test for FactExtractor in `tests/unit/test_fact_extractor.py` — verify orchestration: parser → NER → custom patterns → FactResult list; verify entity counts per type; verify all results are typed as FactResult; verify determinism (same input → same output)
- [ ] T044 [P] [US1] Write unit test for contract patterns in `tests/unit/test_contract_patterns.py` — verify spaCy custom patterns: definition detection ("X shall mean Y"), section references (§12.1, Section 3.2.1), duration patterns ("thirty (30) days"), monetary patterns
- [ ] T045 [P] [US1] Write unit test for clause classifier in `tests/unit/test_clause_classifier.py` — verify heading-based classification (known headings → correct types); verify LLM fallback for ambiguous headings (mock LLM); verify ClauseTypeEnum assignment; verify classification_confidence is None for pattern matches and float for LLM
- [ ] T046 [P] [US1] Write unit test for cross-reference extractor in `tests/unit/test_cross_reference_extractor.py` — verify regex patterns for §N.N, Section N, Appendix X, Schedule X, clause N(a); verify resolution to target clause_id within same document; verify ReferenceEffect classification; verify unresolvable refs flagged as resolved=False
- [ ] T047 [P] [US1] Write unit test for mandatory fact extractor in `tests/unit/test_mandatory_fact_extractor.py` — verify slot filling per clause type (termination → notice_period, termination_reasons); verify missing mandatory facts produce SlotStatus.MISSING; verify optional facts produce SlotStatus.MISSING without error
- [ ] T048 [P] [US1] Write unit test for entity alias detector in `tests/unit/test_alias_detector.py` — verify detection of "X, hereinafter referred to as 'Y'"; "X (the 'Y')"; "X, hereafter 'Y'"; verify Binding records produced with correct term/resolves_to
- [ ] T049 [P] [US1] Write unit test for determinism in `tests/unit/test_determinism.py` — parse same document twice, assert identical fact sets (same ids, same offsets, same values)

### Integration Tests (write FIRST — must FAIL before implementation)

- [ ] T050 [P] [US1] Write integration test for full extraction pipeline in `tests/integration/test_fact_extraction_pipeline.py` — parse document → extract facts → extract clauses → extract cross-references → fill mandatory fact slots → store in TrustGraph → retrieve and verify counts, types, relationships
- [ ] T051 [P] [US1] Write integration test for extraction + alias detection in `tests/integration/test_extraction_with_aliases.py` — parse document with entity aliases → verify both Facts and Bindings produced → verify binding lookup resolves aliases

### Contract Tests (write FIRST — must FAIL before implementation)

- [ ] T052 [P] [US1] Write contract tests for document API in `tests/contract/test_documents_api.py` — `POST /documents` returns 202 with document_id; `GET /documents/{id}` returns metadata + status; `GET /documents/{id}/facts` returns paginated facts with filters; `GET /documents/{id}/clauses` returns typed clauses with cross-refs and slot status; `GET /documents/{id}/clauses/gaps` returns missing mandatory facts; error cases: unsupported format (400), corrupted file (422), not found (404)

### Implementation

- [ ] T053 [US1] Implement Word document parser in `src/contractos/tools/docx_parser.py` — paragraphs, tables, headings, structural paths, character offsets
- [ ] T054 [US1] Implement PDF document parser in `src/contractos/tools/pdf_parser.py` — text with offsets via PyMuPDF, tables via pdfplumber, page numbers
- [ ] T055 [US1] Implement custom spaCy patterns for contract entities in `src/contractos/tools/contract_patterns.py` — definition patterns, section references, duration patterns, monetary patterns
- [ ] T056 [US1] Implement FactExtractor in `src/contractos/tools/fact_extractor.py` — orchestrates parser + spaCy NER + custom patterns; returns `[FactResult]`
- [ ] T057 [US1] Implement clause classifier in `src/contractos/tools/clause_classifier.py` — heading-based detection + LLM-assisted classification for ambiguous sections; assign ClauseTypeEnum
- [ ] T058 [US1] Implement cross-reference extractor in `src/contractos/tools/cross_reference_extractor.py` — regex patterns, resolution within document, effect classification
- [ ] T059 [US1] Implement mandatory fact extractor in `src/contractos/tools/mandatory_fact_extractor.py` — clause type → expected facts → search within clause → fill ClauseFactSlot records
- [ ] T060 [US1] Implement entity alias detector in `src/contractos/tools/alias_detector.py` — detect alias patterns, produce Binding records
- [ ] T061 [US1] Implement document upload endpoint (`POST /documents`) in `src/contractos/api/routes/documents.py` — accept file, trigger parse, return 202
- [ ] T062 [US1] Implement document status endpoint (`GET /documents/{id}`) in `src/contractos/api/routes/documents.py`
- [ ] T063 [US1] Implement facts endpoint (`GET /documents/{id}/facts`) in `src/contractos/api/routes/documents.py` — with type/entity_type filters, pagination
- [ ] T064 [US1] Implement clauses endpoint (`GET /documents/{id}/clauses`) in `src/contractos/api/routes/documents.py` — list clauses with types, cross-references, mandatory fact slot status
- [ ] T065 [US1] Implement clause gaps endpoint (`GET /documents/{id}/clauses/gaps`) — list missing mandatory facts across all clauses
- [ ] T066 [US1] Implement background parsing task — async processing of uploaded documents, progress tracking, error handling

**Checkpoint**: All US1 tests pass. Document parsing works end-to-end. Upload a contract, get facts, clauses, cross-references, and gap analysis back.

---

## Phase 4: User Story 2 — Binding Resolution (P1)

**Goal**: Identify definition clauses and resolve defined terms as Bindings throughout the document.

**Independent Test**: Parse a contract with 10+ defined terms; verify all captured with correct mappings.

### Unit Tests (write FIRST)

- [ ] T067 [P] [US2] Write unit test for BindingResolver in `tests/unit/test_binding_resolver.py` — verify detection of "X shall mean Y" patterns, "X refers to Y" patterns, assignment clauses; verify scope assignment (contract-level); verify override chain (later binding supersedes earlier); verify unresolvable terms flagged as ambiguous
- [ ] T068 [P] [US2] Write unit test for binding lookup utility in `tests/unit/test_binding_lookup.py` — given a term, resolve through binding chain; verify resolution order (same doc → governing doc → latest amendment → ambiguous); verify case-insensitive matching; verify partial match handling

### Integration Tests (write FIRST)

- [ ] T069 [P] [US2] Write integration test for bindings pipeline in `tests/integration/test_binding_resolution.py` — parse document → extract facts → run BindingResolver → store bindings → query by term → verify resolution; also test with alias detector output

### Contract Tests (write FIRST)

- [ ] T070 [P] [US2] Write contract tests for bindings API in `tests/contract/test_bindings_api.py` — `GET /documents/{id}/bindings` returns all bindings with term, resolves_to, source_fact_id, scope; verify filtering by binding_type

### Implementation

- [ ] T071 [US2] Implement BindingResolver in `src/contractos/tools/binding_resolver.py` — detect definition patterns, assignment clauses, scope determination; returns `[BindingResult]`
- [ ] T072 [US2] Implement binding persistence in TrustGraph — store, retrieve, query by term, check overrides
- [ ] T073 [US2] Implement bindings endpoint (`GET /documents/{id}/bindings`) in `src/contractos/api/routes/documents.py`
- [ ] T074 [US2] Integrate BindingResolver into document parsing pipeline — after FactExtractor, before document is marked "indexed"
- [ ] T075 [US2] Implement binding lookup utility in `src/contractos/tools/binding_resolver.py` — given a term in a document, resolve through binding chain, return `BindingResult` or "unresolved"

**Checkpoint**: All US2 tests pass. Document parsing produces facts AND bindings. Defined terms are resolved and queryable.

---

## Phase 5: User Story 3 — Single-Document Q&A (P1) MVP

**Goal**: Answer natural language questions about a contract using facts, bindings, and LLM-generated inferences.

**Independent Test**: Ask 10 benchmark questions; verify answers reference clauses, include confidence, and have provenance chains.

### Unit Tests (write FIRST)

- [ ] T076 [P] [US3] Write unit test for InferenceEngine in `tests/unit/test_inference_engine.py` — verify: takes facts + bindings + query; calls LLM (mocked); returns InferenceResult with supporting_fact_ids, confidence in [0.0–1.0], reasoning_chain non-empty; verify confidence < 0.5 flagged; verify external knowledge declared in domain_sources
- [ ] T077 [P] [US3] Write unit test for confidence calculation in `tests/unit/test_confidence.py` — verify heuristic: more supporting facts → higher confidence; direct fact answer → higher than inferred; binding-resolved → higher than unresolved; verify range always [0.0–1.0]
- [ ] T078 [P] [US3] Write unit test for DocumentAgent in `tests/unit/test_document_agent.py` — verify orchestration: check index → search TrustGraph → resolve bindings → generate inference → build provenance → return QueryResult; verify all code paths: direct fact answer, inference answer, not-found answer; mock TrustGraph and InferenceEngine
- [ ] T079 [P] [US3] Write unit test for ProvenanceChain builder in `tests/unit/test_provenance_builder.py` — verify chain construction from facts + bindings + inferences; verify every node has node_type and reference_id; verify reasoning_summary is non-empty; verify chain is never empty (at minimum contains the "searched sections" node)
- [ ] T080 [P] [US3] Write unit test for "not found" handling in `tests/unit/test_not_found.py` — verify: when no relevant facts/inferences exist, return answer_type="not_found" with list of sections searched; verify confidence is None; verify provenance contains searched sections
- [ ] T081 [P] [US3] Write unit test for prompt templates in `tests/unit/test_prompts.py` — verify Q&A prompt includes facts and bindings in context; verify clause classification prompt constrains to ClauseTypeEnum; verify confidence prompt includes evidence summary

### Integration Tests (write FIRST)

- [ ] T082 [P] [US3] Write integration test for Q&A pipeline in `tests/integration/test_document_qa.py` — parse document → index → ask question → verify answer references correct clauses; verify provenance chain is complete; verify confidence is assigned; test with mock LLM
- [ ] T083 [P] [US3] Write integration test for Q&A with bindings in `tests/integration/test_qa_with_bindings.py` — parse document with defined terms → ask "Who is the supplier?" → verify answer resolves through binding → verify provenance shows binding resolution step
- [ ] T084 [P] [US3] Write integration test for "not found" end-to-end in `tests/integration/test_qa_not_found.py` — parse document → ask about non-existent clause → verify "not found" with searched sections

### Contract Tests (write FIRST)

- [ ] T085 [P] [US3] Write contract tests for query API in `tests/contract/test_query_api.py` — `POST /query` with stream=false returns answer + provenance + confidence; `POST /query` with stream=true returns SSE events (status, partial, provenance, complete); `GET /query/sessions/{id}` returns previous session; error cases: empty query (400), document not indexed (404), LLM unavailable (503 with facts still accessible)

### Implementation

- [ ] T086 [US3] Implement prompt templates in `src/contractos/tools/prompts.py` — structured prompts for Q&A, clause classification, confidence estimation
- [ ] T087 [US3] Implement InferenceEngine in `src/contractos/tools/inference_engine.py` — takes facts + bindings + query, calls LLM, returns `[InferenceResult]` with confidence and reasoning chain
- [ ] T088 [US3] Implement confidence calculation in `src/contractos/tools/confidence.py` — heuristic: evidence count, direct vs. inferred, binding coverage
- [ ] T089 [US3] Implement ProvenanceChain builder in `src/contractos/models/provenance.py` — collects facts, bindings, inferences used during reasoning into a chain
- [ ] T090 [US3] Implement DocumentAgent in `src/contractos/agents/document_agent.py` — orchestrates: check index → search TrustGraph → resolve bindings → generate inference → build provenance → return result
- [ ] T091 [US3] Implement "not found" handling — when no relevant facts/inferences exist, return "not found" with list of sections searched
- [ ] T092 [US3] Implement query endpoint (`POST /query`) in `src/contractos/api/routes/query.py` — accept question + document_ids, return answer with provenance
- [ ] T093 [US3] Implement SSE streaming for query responses in `src/contractos/api/routes/query.py` — stream partial results (searching → reasoning → answer)
- [ ] T094 [US3] Implement query session retrieval (`GET /query/sessions/{id}`) in `src/contractos/api/routes/query.py`

**Checkpoint**: All US3 tests pass. Core value proposition works. User asks a question, gets a grounded answer with provenance. This is the MVP.

---

## Phase 6: User Story 4 — Provenance Display (P2)

**Goal**: Every answer includes an expandable provenance chain; clicking a fact navigates to the document location.

**Independent Test**: Ask a question producing an inference; verify the provenance chain shows facts with locations, confidence indicator, and readable reasoning.

### Unit Tests (write FIRST)

- [ ] T095 [P] [US4] Write unit test for provenance formatting in `tests/unit/test_provenance_formatting.py` — verify human-readable summaries for each node type (fact, binding, inference, external); verify document_location is populated for facts; verify reasoning_summary is plain English
- [ ] T096 [P] [US4] Write unit test for confidence display metadata in `tests/unit/test_confidence_display.py` — verify mapping: 0.0–0.39 → "speculative", 0.40–0.59 → "low", 0.60–0.79 → "moderate", 0.80–0.94 → "high", 0.95–1.0 → "very_high"; verify color coding metadata

### Integration Tests (write FIRST)

- [ ] T097 [P] [US4] Write integration test for provenance in API response in `tests/integration/test_provenance_in_response.py` — ask a question → verify response JSON contains provenance with at least one fact node with document_location; verify confidence_label is present; verify reasoning_summary is non-empty

### Contract Tests (write FIRST)

- [ ] T098 [P] [US4] Write contract test for provenance structure in `tests/contract/test_provenance_contract.py` — verify every `POST /query` response includes provenance matching the schema in api-server.md; verify no response from `/query` lacks provenance (provenance middleware test)

### Implementation

- [ ] T099 [US4] Implement provenance formatting — human-readable summaries for each node, navigable document locations
- [ ] T100 [US4] Add confidence display metadata — map 0.0–1.0 to label + color in API response
- [ ] T101 [US4] Create provenance middleware in `src/contractos/api/middleware/provenance.py` — ensure NO API response from `/query` lacks a ProvenanceChain; reject responses without provenance

**Checkpoint**: All US4 tests pass. Provenance is fully structured, formatted, and enforced in the API.

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
