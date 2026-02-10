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
| `POST` | `/query/ask` | Ask a question about a contract |

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

## Running Tests

### Run the Full Suite

```bash
# All 359 tests
python -m pytest tests/

# Verbose output
python -m pytest tests/ -v

# With coverage report
python -m pytest tests/ --cov=src/contractos --cov-report=term-missing
```

### Run Specific Test Categories

```bash
# Unit tests only (352 tests)
python -m pytest tests/unit/

# Integration tests only (7 tests)
python -m pytest tests/integration/

# Specific module
python -m pytest tests/unit/test_fact_extractor.py -v
python -m pytest tests/unit/test_document_agent.py -v
python -m pytest tests/unit/test_api.py -v
```

### Run by Component

```bash
# Data models (75 tests)
python -m pytest tests/unit/test_models_*.py -v

# Storage layer (56 tests)
python -m pytest tests/unit/test_trust_graph.py tests/unit/test_workspace_store.py -v

# Extraction tools (124 tests)
python -m pytest tests/unit/test_docx_parser.py tests/unit/test_pdf_parser.py \
  tests/unit/test_contract_patterns.py tests/unit/test_fact_extractor.py \
  tests/unit/test_clause_classifier.py tests/unit/test_cross_reference_extractor.py \
  tests/unit/test_mandatory_fact_extractor.py tests/unit/test_alias_detector.py -v

# Q&A pipeline (26 tests)
python -m pytest tests/unit/test_binding_resolver.py tests/unit/test_document_agent.py -v

# API endpoints (23 tests)
python -m pytest tests/unit/test_api.py tests/integration/test_api.py -v
```

---

## Test Report

**359 tests, all passing** (Python 3.14.2, pytest 9.0.2)

### Test Breakdown by Module

| Module | Tests | Category |
|--------|------:|----------|
| `test_trust_graph.py` | 39 | Storage — TrustGraph CRUD |
| `test_clause_classifier.py` | 29 | Tools — clause type classification |
| `test_contract_patterns.py` | 25 | Tools — regex pattern extraction |
| `test_fact_extractor.py` | 21 | Tools — extraction orchestrator |
| `test_workspace_store.py` | 17 | Storage — workspace persistence |
| `test_models_fact.py` | 16 | Models — Fact, FactEvidence, FactType |
| `test_docx_parser.py` | 16 | Tools — Word document parser |
| `test_api.py` (unit) | 16 | API — all endpoints |
| `test_confidence.py` | 15 | Tools — confidence labels |
| `test_models_clause.py` | 14 | Models — Clause, CrossReference |
| `test_binding_resolver.py` | 13 | Tools — binding resolution |
| `test_cross_reference_extractor.py` | 13 | Tools — cross-reference detection |
| `test_document_agent.py` | 13 | Agents — Q&A pipeline |
| `test_pdf_parser.py` | 13 | Tools — PDF document parser |
| `test_llm_provider.py` | 12 | LLM — provider abstraction |
| `test_models_query.py` | 11 | Models — Query, QueryResult |
| `test_alias_detector.py` | 10 | Tools — entity alias detection |
| `test_mandatory_fact_extractor.py` | 10 | Tools — mandatory fact slots |
| `test_models_workspace.py` | 10 | Models — Workspace, Session |
| `test_models_provenance.py` | 9 | Models — ProvenanceChain |
| `test_models_inference.py` | 8 | Models — Inference |
| `test_provenance_formatting.py` | 8 | Tools — provenance display |
| `test_models_binding.py` | 7 | Models — Binding |
| `test_config.py` | 7 | Config — YAML loading |
| `test_api.py` (integration) | 7 | API — full pipeline |
| **Total** | **359** | |

---

## Extraction Reports (Test Fixtures)

### DOCX: `simple_procurement.docx` — Master Services Agreement

A procurement MSA between Alpha Corp (Buyer) and Beta Services Ltd (Vendor).

| Metric | Value |
|--------|------:|
| Word count | 224 |
| Paragraphs | 17 |
| Tables | 2 |
| **Facts extracted** | **41** |
| Clauses classified | 8 |
| Bindings resolved | 5 |
| Cross-references | 6 |
| Mandatory fact slots | 11 |

**Facts by type:**

| Type | Count |
|------|------:|
| `table_cell` | 15 |
| `text_span` | 14 |
| `entity` | 6 |
| `cross_reference` | 6 |

**Clauses identified:**

| Type | Heading | Cross-refs |
|------|---------|:----------:|
| general | Master Services Agreement | 0 |
| general | 1. Definitions | 0 |
| scope | 2. Scope of Services | 2 |
| payment | 3. Payment Terms | 0 |
| termination | 4. Termination | 1 |
| confidentiality | 5. Confidentiality | 1 |
| general | Schedule A: Products | 1 |
| general | Schedule B: Locations | 1 |

**Bindings resolved:**

| Term | Resolves To | Type |
|------|-------------|------|
| Agreement | Master Services Agreement | definition |
| Buyer | Alpha Corp | alias |
| Vendor | Beta Services Ltd | alias |
| Effective Date | January 1, 2025 | definition |
| Service Period | thirty (30) days from the Effective Date | definition |

**Mandatory fact slot analysis:**

| Clause | Fact Spec | Status | Required |
|--------|-----------|--------|----------|
| 3. Payment Terms | payment_amount | partial | yes |
| 3. Payment Terms | payment_schedule | partial | yes |
| 3. Payment Terms | currency | partial | no |
| 3. Payment Terms | late_payment_penalty | missing | no |
| 4. Termination | notice_period | partial | yes |
| 4. Termination | termination_reasons | partial | yes |
| 4. Termination | cure_period | partial | no |
| 4. Termination | survival_clauses | missing | no |
| 5. Confidentiality | confidentiality_duration | partial | yes |
| 5. Confidentiality | confidential_information_definition | partial | yes |
| 5. Confidentiality | exclusions | missing | no |

### PDF: `simple_nda.pdf` — Non-Disclosure Agreement

An NDA between Gamma Inc (Discloser) and Delta LLC (Recipient).

| Metric | Value |
|--------|------:|
| Word count | 123 |
| Paragraphs | 13 |
| Tables | 1 |
| **Facts extracted** | **17** |
| Clauses classified | 0 |
| Bindings resolved | 3 |
| Cross-references | 0 |
| Mandatory fact slots | 0 |

**Facts by type:**

| Type | Count |
|------|------:|
| `entity` | 6 |
| `text_span` | 6 |
| `table_cell` | 4 |
| `cross_reference` | 1 |

**Bindings resolved:**

| Term | Resolves To | Type |
|------|-------------|------|
| NDA | Disclosure Agreement | definition |
| Discloser | Gamma Inc | alias |
| Recipient | Delta LLC | alias |

**Sample extracted facts:**

| Fact ID | Type | Value | Location |
|---------|------|-------|----------|
| f-... | entity | `Disclosure Agreement ("NDA"` | chars 45–72 |
| f-... | entity | `Gamma Inc (the "Discloser"` | chars 74–124 |
| f-... | entity | `Delta LLC (the "Recipient"` | chars 126–156 |
| f-... | text_span | `four (24) months` | chars 446–462 |
| f-... | text_span | `thirty (30) days` | chars 555–571 |
| f-... | cross_reference | `Section 2` | chars 678–687 |
| f-... | text_span | `January 1, 2025` | chars 735–750 |
| f-... | text_span | `December 31, 2026` | chars 763–780 |

---

## Architecture

```
Interaction    →  Word/PDF Copilot · CLI · API
Workspace      →  Persistent context · Auto-discovery · Session memory
Agents         →  DocumentAgent (Q&A with provenance)
Tools          →  FactExtractor · BindingResolver · ClauseClassifier
                  CrossReferenceExtractor · MandatoryFactExtractor
                  AliasDetector · ContractPatterns · Confidence
Fabric         →  TrustGraph (SQLite) · WorkspaceStore
LLM            →  Anthropic Claude · Mock (testing)
```

### Project Structure

```
src/contractos/
├── agents/              # Q&A agents (DocumentAgent)
├── api/                 # FastAPI application
│   ├── app.py           # App factory
│   ├── deps.py          # Dependency injection
│   └── routes/          # Endpoint handlers
├── cli.py               # CLI interface
├── config.py            # Configuration loading
├── fabric/              # Storage layer
│   ├── trust_graph.py   # SQLite-backed fact/binding/clause store
│   ├── workspace_store.py
│   └── schema.sql       # Database schema
├── llm/                 # LLM provider abstraction
│   └── provider.py      # Anthropic + Mock providers
├── models/              # Pydantic data models
│   ├── fact.py          # Fact, FactEvidence, FactType
│   ├── binding.py       # Binding, BindingType
│   ├── clause.py        # Clause, ClauseTypeEnum, CrossReference
│   ├── inference.py     # Inference, InferenceType
│   ├── provenance.py    # ProvenanceChain, ProvenanceNode
│   ├── query.py         # Query, QueryResult
│   └── ...
└── tools/               # Extraction and analysis tools
    ├── fact_extractor.py       # Orchestrator
    ├── docx_parser.py          # Word document parser
    ├── pdf_parser.py           # PDF document parser
    ├── contract_patterns.py    # Regex patterns
    ├── clause_classifier.py    # Heading-based classification
    ├── cross_reference_extractor.py
    ├── mandatory_fact_extractor.py
    ├── alias_detector.py       # Entity alias detection
    ├── binding_resolver.py     # Definition resolution
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

**Phase 6 complete** — Full extraction pipeline, Q&A with provenance, 9 API endpoints, 359 tests passing.

| Phase | Status | Tests |
|-------|--------|------:|
| Phase 1: Setup | Done | — |
| Phase 2: Foundation (Models, Storage, LLM, API) | Done | 168 |
| Phase 3: Fact Extraction (Parsers, Patterns, Classifiers) | Done | 137 |
| Phase 4: Binding Resolution | Done | 13 |
| Phase 5: Q&A Pipeline (DocumentAgent) | Done | 13 |
| Phase 6: Pipeline Wiring, Provenance Display, CLI | Done | 28 |
| Phase 7: Workspace Persistence | Planned | — |
| Phase 8: Word Copilot Add-in | Planned | — |
| Phase 9: Polish & Benchmarks | Planned | — |
