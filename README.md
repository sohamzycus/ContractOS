# ContractOS

> The operating system for contract intelligence.

ContractOS transforms contracts from static legal documents into executable,
explainable legal knowledge that can be queried, reasoned over, and evolved.

## What It Does

- **Ask questions** about contracts and get grounded, explainable answers
- **Extract facts** — parties, dates, amounts, durations, definitions, with precise character offsets
- **Classify clauses** — payment, termination, confidentiality, scope, and more
- **Resolve bindings** — "Buyer" = "Alpha Corp", "Effective Date" = "January 1, 2025"
- **Detect compliance gaps** — missing mandatory facts per clause type
- **Full provenance** — every answer traces back to source evidence with confidence labels

---

## Quick Start

### Prerequisites

- **Python 3.12+** (tested on 3.12, 3.13, 3.14)
- **pip** or **uv** for package management

### 1. Clone and Install

```bash
git clone <repo-url> ContractOS
cd ContractOS

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install with dev dependencies
pip install -e ".[dev]"
```

### 2. Run the Server

**With mock LLM (no API key needed — for testing):**

```bash
python -m uvicorn contractos.api.app:create_app --host 127.0.0.1 --port 8742 --factory
```

**With Anthropic Claude:**

```bash
export ANTHROPIC_API_KEY="your-api-key"
python -m uvicorn contractos.api.app:create_app --host 127.0.0.1 --port 8742 --factory
```

**With a LiteLLM proxy or custom endpoint:**

```bash
export ANTHROPIC_API_KEY="your-api-key"
export ANTHROPIC_BASE_URL="https://your-proxy.example.com/"
export ANTHROPIC_MODEL="claude-sonnet-4-5-global"
python -m uvicorn contractos.api.app:create_app --host 127.0.0.1 --port 8742 --factory
```

The server starts at **http://127.0.0.1:8742**. Open **http://127.0.0.1:8742/docs** for the interactive Swagger UI.

### 3. Upload a Contract

```bash
curl -X POST http://127.0.0.1:8742/contracts/upload \
  -F "file=@path/to/contract.docx"
```

### 4. Ask a Question

```bash
curl -X POST http://127.0.0.1:8742/query/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the payment terms?", "document_id": "doc-xxx"}'
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check |
| `GET` | `/config` | Current configuration (non-sensitive) |
| `POST` | `/contracts/upload` | Upload and index a contract (docx/pdf) |
| `GET` | `/contracts/{id}` | Get contract metadata |
| `GET` | `/contracts/{id}/facts` | List extracted facts (paginated, filterable) |
| `GET` | `/contracts/{id}/clauses` | List classified clauses |
| `GET` | `/contracts/{id}/bindings` | List resolved bindings (definitions + aliases) |
| `GET` | `/contracts/{id}/clauses/gaps` | List missing mandatory facts |
| `GET` | `/contracts/{id}/graph` | **TrustGraph context** — full node/edge graph |
| `POST` | `/query/ask` | Ask a question about a contract |
| `POST` | `/workspaces` | Create a workspace |
| `GET` | `/workspaces` | List all workspaces |
| `GET` | `/workspaces/{id}` | Get workspace with recent sessions |
| `POST` | `/workspaces/{id}/documents` | Add document to workspace |
| `DELETE` | `/workspaces/{id}/documents/{doc_id}` | Remove document from workspace |
| `GET` | `/workspaces/{id}/sessions` | Session history for workspace |
| `GET` | `/workspaces/{id}/documents/{doc_id}/check` | Document change detection |

### Example: Full Pipeline

```bash
# 1. Upload
RESP=$(curl -s -X POST http://127.0.0.1:8742/contracts/upload \
  -F "file=@tests/fixtures/simple_procurement.docx")
DOC_ID=$(echo $RESP | python -c "import json,sys; print(json.load(sys.stdin)['document_id'])")
echo "Uploaded: $DOC_ID"

# 2. Inspect extracted facts
curl -s "http://127.0.0.1:8742/contracts/$DOC_ID/facts?limit=5" | python -m json.tool

# 3. View clauses
curl -s "http://127.0.0.1:8742/contracts/$DOC_ID/clauses" | python -m json.tool

# 4. View bindings
curl -s "http://127.0.0.1:8742/contracts/$DOC_ID/bindings" | python -m json.tool

# 5. Check for gaps
curl -s "http://127.0.0.1:8742/contracts/$DOC_ID/clauses/gaps" | python -m json.tool

# 6. Ask a question
curl -s -X POST http://127.0.0.1:8742/query/ask \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"What are the payment terms?\", \"document_id\": \"$DOC_ID\"}" \
  | python -m json.tool
```

---

## CLI

ContractOS includes a command-line interface:

```bash
# Start the server
contractos serve --host 127.0.0.1 --port 8742

# Parse a document locally (no server needed)
contractos parse path/to/contract.docx

# Query via the API
contractos query "What are the payment terms?" --document-id doc-xxx

# List facts
contractos facts doc-xxx

# List bindings
contractos bindings doc-xxx
```

---

## Postman / Newman Integration Tests

ContractOS ships with a comprehensive Postman collection for API integration testing,
including LegalBench and CUAD benchmark document workflows.

### Setup

```bash
# Install Newman (Postman CLI runner)
npm install -g newman newman-reporter-htmlextra
```

### Run via Newman (CLI)

```bash
# Run all integration tests (requires server running)
./postman/run_integration_tests.sh

# Auto-start server + run tests
./postman/run_integration_tests.sh --server

# Run a specific folder
./postman/run_integration_tests.sh --folder "0 — Health & Config"
./postman/run_integration_tests.sh --folder "5 — LegalBench Benchmark Queries"
```

### Run via Postman GUI

1. Import `postman/ContractOS.postman_collection.json`
2. Import `postman/ContractOS.postman_environment.json`
3. Start the server: `python -m uvicorn contractos.api.app:create_app --host 127.0.0.1 --port 8742 --factory`
4. Run the collection folders in order (0 → 6)

### Collection Structure

| Folder | Requests | Description |
|--------|----------|-------------|
| 0 — Health & Config | 2 | Service health, configuration |
| 1 — Contract Upload & Indexing | 7 | Upload DOCX/PDF (simple + complex + LegalBench + CUAD), error handling |
| 2 — Contract Retrieval & Exploration | 10 | Metadata, facts (filtered/paginated), clauses, bindings, gaps, TrustGraph |
| 3 — Q&A with Provenance | 5 | Questions with confidence + provenance, error handling |
| 4 — Workspace Management | 9 | CRUD, document association, session history, error handling |
| 5 — LegalBench Benchmark Queries | 8 | CUAD + contract_nli + definition benchmark-style queries |
| 6 — Complex Document Deep Dive | 6 | SLA, data protection, price escalation, volume discounts, liquidated damages |

### LegalBench / CUAD Benchmark Fixtures

| Fixture | Source | Categories Covered |
|---------|--------|--------------------|
| `legalbench_nda.docx` | LegalBench-style | contract_nli_confidentiality, survival_of_obligations, definition_extraction |
| `cuad_license_agreement.docx` | CUAD-style | license_grant, non-compete, termination, cap_on_liability, governing_law, insurance, audit_rights |
| `complex_it_outsourcing.docx` | Real-world sim | SLA, data protection, price escalation, multi-party, insurance matrix |
| `complex_procurement_framework.pdf` | Real-world sim | Volume discounts, liquidated damages, performance bonds, ESG, KPIs |

---

## Running Tests

### Run the Full Suite

```bash
# All 467 tests
python -m pytest tests/

# Verbose output
python -m pytest tests/ -v

# With coverage report
python -m pytest tests/ --cov=src/contractos --cov-report=term-missing
```

### Run Specific Test Categories

```bash
# Unit tests only (389 tests)
python -m pytest tests/unit/

# Integration tests only (51 tests)
python -m pytest tests/integration/

# Contract tests (27 tests)
python -m pytest tests/contract/

# LegalBench / CUAD benchmark tests
python -m pytest tests/integration/test_legalbench_extraction.py -v
python -m pytest tests/contract/test_legalbench_api.py -v

# Specific module
python -m pytest tests/unit/test_fact_extractor.py -v
python -m pytest tests/unit/test_document_agent.py -v
python -m pytest tests/unit/test_api.py -v
```

### Run by Component

```bash
# Data models (75 tests)
python -m pytest tests/unit/test_models_*.py -v

# Storage layer (56 + 17 + 8 = 81 tests)
python -m pytest tests/unit/test_trust_graph.py tests/unit/test_workspace_store.py \
  tests/unit/test_workspace_documents.py -v

# Extraction tools (143 tests — includes complex fixture tests)
python -m pytest tests/unit/test_docx_parser.py tests/unit/test_pdf_parser.py \
  tests/unit/test_contract_patterns.py tests/unit/test_fact_extractor.py \
  tests/unit/test_clause_classifier.py tests/unit/test_cross_reference_extractor.py \
  tests/unit/test_mandatory_fact_extractor.py tests/unit/test_alias_detector.py -v

# Q&A pipeline (26 tests)
python -m pytest tests/unit/test_binding_resolver.py tests/unit/test_document_agent.py -v

# Workspace persistence (32 tests)
python -m pytest tests/unit/test_change_detection.py tests/unit/test_workspace_documents.py \
  tests/integration/test_workspace_persistence.py tests/integration/test_session_history.py \
  tests/contract/test_workspace_api.py -v

# API endpoints (36 tests)
python -m pytest tests/unit/test_api.py tests/integration/test_api.py \
  tests/contract/test_workspace_api.py -v
```

---

## Test Report

**467 tests, all passing** (Python 3.14.2, pytest 9.0.2)

### Test Breakdown by Module

| Module | Tests | Category |
|--------|------:|----------|
| `test_fact_extractor.py` | 40 | Tools — extraction orchestrator + complex fixtures |
| `test_trust_graph.py` | 39 | Storage — TrustGraph CRUD |
| `test_legalbench_extraction.py` | 32 | Integration — LegalBench/CUAD benchmark extraction |
| `test_clause_classifier.py` | 29 | Tools — clause type classification |
| `test_contract_patterns.py` | 25 | Tools — regex pattern extraction |
| `test_workspace_store.py` | 17 | Storage — workspace persistence |
| `test_models_fact.py` | 16 | Models — Fact, FactEvidence, FactType |
| `test_docx_parser.py` | 16 | Tools — Word document parser |
| `test_api.py` (unit) | 16 | API — all endpoints |
| `test_confidence.py` | 15 | Tools — confidence labels |
| `test_legalbench_api.py` (contract) | 14 | Contract — LegalBench/CUAD API endpoints |
| `test_models_clause.py` | 14 | Models — Clause, CrossReference |
| `test_workspace_api.py` (contract) | 13 | Contract — workspace API endpoints |
| `test_binding_resolver.py` | 13 | Tools — binding resolution |
| `test_cross_reference_extractor.py` | 13 | Tools — cross-reference detection |
| `test_document_agent.py` | 13 | Agents — Q&A pipeline |
| `test_pdf_parser.py` | 13 | Tools — PDF document parser |
| `test_llm_provider.py` | 12 | LLM — provider abstraction |
| `test_change_detection.py` | 11 | Tools — file hash + change detection |
| `test_models_query.py` | 11 | Models — Query, QueryResult |
| `test_alias_detector.py` | 10 | Tools — entity alias detection |
| `test_mandatory_fact_extractor.py` | 10 | Tools — mandatory fact slots |
| `test_models_workspace.py` | 10 | Models — Workspace, Session |
| `test_models_provenance.py` | 9 | Models — ProvenanceChain |
| `test_models_inference.py` | 8 | Models — Inference |
| `test_provenance_formatting.py` | 8 | Tools — provenance display |
| `test_workspace_documents.py` | 8 | Storage — workspace-document association |
| `test_session_history.py` (integration) | 8 | Integration — session history ordering |
| `test_models_binding.py` | 7 | Models — Binding |
| `test_config.py` | 7 | Config — YAML loading |
| `test_api.py` (integration) | 7 | API — full pipeline |
| `test_workspace_persistence.py` (integration) | 3 | Integration — persistence across restart |
| **Total** | **421** | |

---

## Q&A Test Reports (Live LLM)

Full Q&A test reports with real LLM responses are checked in at [`tests/reports/`](tests/reports/):

### Simple Fixtures

| Report | Document | Queries | Fact-grounded | Not-found | Avg Confidence |
|--------|----------|:-------:|:-------------:|:---------:|:--------------:|
| [MSA Report](tests/reports/QA_TEST_REPORT.md#report-1-master-services-agreement-simple_procurementdocx) | `simple_procurement.docx` | 10 | 7 | 3 | 0.86 |
| [NDA Report](tests/reports/QA_TEST_REPORT.md#report-2-non-disclosure-agreement-simple_ndapdf) | `simple_nda.pdf` | 7 | 5 | 2 | 0.90 |

### Complex Fixtures (Real-World Simulation)

| Report | Document | Queries | Fact-grounded | Not-found | Avg Confidence |
|--------|----------|:-------:|:-------------:|:---------:|:--------------:|
| [IT Outsourcing](tests/reports/QA_TEST_REPORT.md#report-3-it-outsourcing-agreement-complex_it_outsourcingdocx) | `complex_it_outsourcing.docx` | 10 | 7 | 3 | 0.86 |
| [Procurement Framework](tests/reports/QA_TEST_REPORT.md#report-4-procurement-framework-agreement-complex_procurement_frameworkpdf) | `complex_procurement_framework.pdf` | 7 | 6 | 1 | 0.91 |
| **Total** | **4 documents** | **34** | **25 (74%)** | **9 (26%)** | **0.88** |

Raw JSON: [`qa_report_procurement_msa.json`](tests/reports/qa_report_procurement_msa.json), [`qa_report_nda.json`](tests/reports/qa_report_nda.json), [`qa_report_complex_it_outsourcing.json`](tests/reports/qa_report_complex_it_outsourcing.json), [`qa_report_complex_procurement_framework.json`](tests/reports/qa_report_complex_procurement_framework.json)

See the [full Q&A Test Report](tests/reports/QA_TEST_REPORT.md) for every question, answer, confidence label, provenance chain, and analysis.

---

## Extraction Reports (Test Fixtures)

### Simple: `simple_procurement.docx` — Master Services Agreement

| Metric | Value |
|--------|------:|
| Word count | 224 |
| **Facts extracted** | **50** |
| Clauses classified | 8 |
| Bindings resolved | 5 |
| Cross-references | 6 |

**Facts by type:** `table_cell` 15, `text_span` 14, `clause_text` 9, `entity` 6, `cross_reference` 6

### Simple: `simple_nda.pdf` — Non-Disclosure Agreement

| Metric | Value |
|--------|------:|
| Word count | 123 |
| **Facts extracted** | **17** |
| Clauses classified | 0 |
| Bindings resolved | 3 |

**Facts by type:** `entity` 6, `text_span` 6, `table_cell` 4, `cross_reference` 1

### Complex: `complex_it_outsourcing.docx` — $47.5M IT Outsourcing Agreement

A production-grade 18-section IT outsourcing contract between Meridian Global Holdings (Client) and TechServe Solutions (Service Provider/Vendor).

| Metric | Value |
|--------|------:|
| Word count | 4,119 |
| **Facts extracted** | **607** |
| Clauses classified | 65 |
| Bindings resolved | 31 |
| Cross-references | 44 |
| Mandatory fact slots | 44 |

**Facts by type:**

| Type | Count | Description |
|------|------:|-------------|
| `table_cell` | 256 | SLA tables, pricing, locations, insurance, compliance, assets, applications |
| `text_span` | 172 | Dates, amounts, durations, percentages, definitions |
| `clause_text` | 98 | Full clause body paragraphs (termination conditions, liability caps, etc.) |
| `cross_reference` | 45 | Section refs, schedule refs, appendix refs |
| `entity` | 36 | Party aliases, defined terms |

**Clause types identified:**

| Type | Count | Examples |
|------|------:|---------|
| general | 39 | Title, definitions, key definitions, schedules |
| termination | 4 | For convenience, for cause, assistance, consequences |
| payment | 3 | Contract value, price escalation, quarterly reconciliation |
| compliance | 3 | Regulatory, SOC 2, ISO 27001 |
| dispute_resolution | 3 | Escalation, mediation, arbitration |
| confidentiality | 2 | Obligations, data breach notification |
| indemnification | 2 | Service provider indemnification, consequential damages |
| notice | 2 | Notices, amendments |
| scope | 1 | Infrastructure + application services |
| ip_rights | 1 | Client IP, Service Provider IP, Joint IP |
| insurance | 1 | 5 coverage types with limits |
| liability | 1 | 200% annual Base Fee cap |
| force_majeure | 1 | 90-day threshold |
| governing_law | 1 | State of New York |
| assignment | 1 | Affiliate/M&A exception |

**Key bindings resolved:**

| Term | Resolves To | Type |
|------|-------------|------|
| Agreement | IT Outsourcing Services Agreement | definition |
| CCPA | California Consumer Privacy Act | definition |
| Liability Cap | current contract year | definition |
| Escalation Cap | CPI increase, whichever is lower | definition |
| Monthly Credit Cap | 15% of monthly Base Fee | definition |
| Client IP | IP owned by Client prior to Effective Date | definition |
| Joint IP | IP developed jointly by the Parties | definition |
| DPA | Data Processing Agreement | definition |

**TrustGraph visualization:** `GET /contracts/{id}/graph` returns 748 nodes, 894 edges

### Complex: `complex_procurement_framework.pdf` — GBP 85M Procurement Framework

A multi-category procurement framework between Pinnacle Manufacturing Group (Buyer) and GlobalSource Industrial Supply (Supplier), covering 14 delivery points across 10 countries.

| Metric | Value |
|--------|------:|
| Word count | 3,128 |
| **Facts extracted** | **376** |
| Clauses classified | 0 (PDF heading detection limitation) |
| Bindings resolved | 16 |

**Facts by type:**

| Type | Count | Description |
|------|------:|-------------|
| `text_span` | 174 | Dates, amounts, durations, percentages |
| `table_cell` | 166 | Volume discounts, delivery points, categories, KPIs, liquidated damages |
| `cross_reference` | 22 | Section/annex references |
| `entity` | 14 | Party aliases, defined terms |

**Key bindings resolved:**

| Term | Resolves To | Type |
|------|-------------|------|
| Framework Agreement | This Procurement Framework Agreement | definition |
| Performance Bond | irrevocable, unconditional bank guarantee | definition |
| Liquidated Damages | pre-estimated damages for failure to meet obligations | definition |
| Warranty Period | 24 months from date of delivery | definition |
| Confidential Information | all information marked as confidential... | definition |
| ESG | environmental, social, and governance | definition |
| KPI | performance metrics set out in Annex 5 | definition |

---

## Architecture

```
Interaction    →  Word/PDF Copilot · CLI · API
Workspace      →  Persistent context · Session history · Change detection
Agents         →  DocumentAgent (Q&A with provenance)
Tools          →  FactExtractor · BindingResolver · ClauseClassifier
                  CrossReferenceExtractor · MandatoryFactExtractor
                  AliasDetector · ContractPatterns · Confidence
                  ChangeDetection · ProvenanceFormatter
Fabric         →  TrustGraph (SQLite) · WorkspaceStore
LLM            →  Anthropic Claude · Mock (testing)
```

### TrustGraph

The TrustGraph is the core knowledge store. For any indexed document, `GET /contracts/{id}/graph` returns the full context graph:

```
Contract (root)
├── Clauses (65 for complex DOCX)
│   ├── Clause body text facts (CLAUSE_TEXT)
│   └── Cross-references → other clauses
├── Facts (607 for complex DOCX)
│   ├── text_span — dates, amounts, durations
│   ├── table_cell — schedule data, SLA tables
│   ├── clause_text — full paragraph text
│   ├── entity — party names, defined terms
│   └── cross_reference — section/appendix refs
└── Bindings (31 for complex DOCX)
    ├── definitions — "Liability Cap" → "current contract year"
    └── aliases — "Client" → "Meridian Global Holdings"
```

### Project Structure

```
src/contractos/
├── agents/              # Q&A agents (DocumentAgent)
├── api/                 # FastAPI application
│   ├── app.py           # App factory
│   ├── deps.py          # Dependency injection
│   └── routes/          # Endpoint handlers
│       ├── contracts.py # Upload, facts, clauses, bindings, graph
│       ├── health.py    # Health + config
│       ├── query.py     # Q&A with provenance
│       └── workspace.py # Workspace CRUD, sessions, change detection
├── cli.py               # CLI interface
├── config.py            # Configuration loading
├── fabric/              # Storage layer
│   ├── trust_graph.py   # SQLite-backed fact/binding/clause store
│   ├── workspace_store.py
│   └── schema.sql       # Database schema
├── llm/                 # LLM provider abstraction
│   └── provider.py      # Anthropic + Mock providers
├── models/              # Pydantic data models
│   ├── fact.py          # Fact, FactEvidence, FactType (incl. CLAUSE_TEXT)
│   ├── binding.py       # Binding, BindingType
│   ├── clause.py        # Clause, ClauseTypeEnum, CrossReference
│   ├── inference.py     # Inference, InferenceType
│   ├── provenance.py    # ProvenanceChain, ProvenanceNode
│   ├── query.py         # Query, QueryResult
│   ├── workspace.py     # Workspace, ReasoningSession
│   └── document.py      # Contract metadata
└── tools/               # Extraction and analysis tools
    ├── fact_extractor.py       # Orchestrator (incl. clause body text)
    ├── docx_parser.py          # Word document parser
    ├── pdf_parser.py           # PDF document parser
    ├── contract_patterns.py    # Regex patterns
    ├── clause_classifier.py    # Heading-based classification
    ├── cross_reference_extractor.py
    ├── mandatory_fact_extractor.py
    ├── alias_detector.py       # Entity alias detection
    ├── binding_resolver.py     # Definition resolution
    ├── change_detection.py     # File hash + change detection
    ├── confidence.py           # Confidence labels
    └── provenance_formatter.py # Provenance display
```

## Truth Model

ContractOS strictly separates four layers of truth:

| Layer | What | Persistence |
|-------|------|------------|
| **Fact** | Directly grounded in contract text | Immutable |
| **Binding** | Explicit semantic mapping (definitions) | Persisted, scoped |
| **Inference** | Derived claim with confidence | Persisted, revisable |
| **Opinion** | Contextual judgment (role/policy-dependent) | Computed on demand |

Breaking this model breaks ContractOS.

## Configuration

Configuration is loaded from `config/default.yaml` with environment variable overrides:

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | _(falls back to mock)_ |
| `ANTHROPIC_BASE_URL` | Custom API endpoint (e.g. LiteLLM proxy) | _(Anthropic default)_ |
| `ANTHROPIC_MODEL` | Model name | `claude-sonnet-4-20250514` |

## Specification

See [`spec/`](spec/) for the complete ecosystem blueprint:

1. [Vision](spec/vision.md) — What and why
2. [Truth Model](spec/truth-model.md) — The most important file
3. [Architecture](spec/architecture.md) — System layers

## Status

**Phase 7 complete** — Full extraction pipeline, Q&A with provenance, workspace persistence, TrustGraph visualization, 17 API endpoints, 421 tests passing.

| Phase | Status | Tests |
|-------|--------|------:|
| Phase 1: Setup | Done | — |
| Phase 2: Foundation (Models, Storage, LLM, API) | Done | 168 |
| Phase 3: Fact Extraction (Parsers, Patterns, Classifiers) | Done | 137 |
| Phase 4: Binding Resolution | Done | 13 |
| Phase 5: Q&A Pipeline (DocumentAgent) | Done | 13 |
| Phase 6: Pipeline Wiring, Provenance Display, CLI | Done | 28 |
| Phase 7: Workspace Persistence, Change Detection, Complex Fixtures | Done | 62 |
| Phase 8: Word Copilot Add-in | Planned | — |
| Phase 9: Polish & Benchmarks | Planned | — |
