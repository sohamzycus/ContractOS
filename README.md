<p align="center">
  <h1 align="center">ContractOS</h1>
  <p align="center"><strong>The Operating System for Contract Intelligence</strong></p>
  <p align="center">
    <a href="#quick-start">Quick Start</a> &bull;
    <a href="#features">Features</a> &bull;
    <a href="#architecture">Architecture</a> &bull;
    <a href="#demo">Live Demo</a> &bull;
    <a href="docs/EXECUTIVE_SUMMARY.md">Executive Summary</a> &bull;
    <a href="presentation/">Presentation</a>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/tests-794%20passing-brightgreen?logo=pytest&logoColor=white" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/LLM-Anthropic%20Claude-blueviolet?logo=anthropic" alt="Anthropic Claude">
  <img src="https://img.shields.io/badge/MCP-13%20tools-orange" alt="MCP Tools">
  <img src="https://img.shields.io/badge/API-34%20endpoints-informational" alt="API Endpoints">
  <img src="https://img.shields.io/badge/LOC-~9.8K%20prod%20%7C%20~14.8K%20test-lightgrey" alt="Lines of Code">
</p>

---

## Why ContractOS?

Contracts encode obligations, risks, and rights **implicitly** — buried in tables, scattered across clauses that reference each other, wrapped in defined terms that transform meaning. Most contract AI systems fail because they treat contracts as flat text blobs, rely on keyword matching, and answer questions without grounding or provenance.

**ContractOS is different.** It transforms static legal documents into structured, queryable, explainable legal knowledge — with every answer traceable back to source text.

> *"Does this contract indemnify the buyer for data breach?"*
>
> ContractOS doesn't guess. It extracts facts, resolves definitions, searches its knowledge graph, reasons with Claude grounded in evidence, and returns an answer with **confidence score**, **provenance chain**, and **clickable source references**.

---

## The Truth Model

ContractOS introduces a strict four-layer epistemological model that separates what a contract **says** from what it **means**, what can be **derived**, and what someone **thinks** about it:

| Layer | What It Is | Example | Persistence |
|-------|-----------|---------|-------------|
| **Fact** | Directly grounded in contract text | "Term: 24 months" | Immutable |
| **Binding** | Explicitly stated semantic mapping | "'Company' means Acme Corp" | Persisted, scoped |
| **Inference** | Derived claim from facts + knowledge | "Contract expires Dec 2025" | Persisted with confidence |
| **Opinion** | Contextual judgment | "Missing force majeure is a risk" | Computed on demand |

This separation is **foundational** — it ensures every answer is auditable and every claim is traceable.

---

## Features

### Upload & Instant Analysis
Upload any PDF or DOCX. Within seconds: full document rendering, extraction summary (facts, clauses, bindings), and 8 quick-action buttons for immediate exploration.

### Semantic Q&A with Provenance
Ask natural language questions. The system searches FAISS vectors, builds context from the TrustGraph, reasons with Claude, and returns answers with confidence labels, provenance chains, and clickable source references.

### Playbook Compliance Review
Review contracts against configurable organizational playbooks. Clause-by-clause comparison with **GREEN/YELLOW/RED** classification, automated redline suggestions, risk profiles, and negotiation strategy — all streamed progressively via SSE.

### NDA Triage Screening
Automated 10-point checklist with hybrid pattern + LLM evaluation. GREEN (auto-approve), YELLOW (expedited review), RED (full legal review) routing with timeline recommendations.

### Hidden Fact Discovery
LLM-powered analysis that surfaces implicit obligations, liability exposure, unstated assumptions, cross-clause implications, missing protections, and ambiguous terms.

### Risk Memo & Obligation Extraction
Structured risk assessment with severity/likelihood scoring, missing protections, prioritized recommendations. Extract all obligations (affirmative, negative, conditional) with deadlines and breach consequences.

### MCP Server Integration
Full contract intelligence exposed as an MCP server (Anthropic's open standard) — 13 tools, 10 resources, 5 prompts. Works in Cursor, Claude Desktop, Claude Code, or any MCP client.

### TrustGraph Visualization
Interactive D3.js force-directed graph showing the full knowledge graph — contracts, clauses, facts, bindings, and cross-references as connected nodes.

---

## By the Numbers

| Metric | Value |
|--------|-------|
| Production code | ~9,800 lines across 63 modules |
| Test code | ~14,800 lines (1.5x production) |
| **Passing tests** | **794** |
| API endpoints | 34 + 6 SSE streaming |
| MCP tools / resources / prompts | 13 / 10 / 5 |
| Real NDA documents tested | 50 (ContractNLI, Stanford NLP) |
| LegalBench benchmark tasks | 16 tasks, 128 samples |
| Sample contracts | 4 (simple NDA, complex procurement, simple MSA, complex IT outsourcing) |
| Development phases | 13 phases, 280+ tasks, all complete |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     INTERACTION LAYER                         │
│    Browser Copilot · API Console · TrustGraph Viz · MCP      │
├──────────────────────────────────────────────────────────────┤
│                MCP INTEGRATION LAYER                          │
│   13 Tools · 10 Resources · 5 Prompts (stdio + HTTP)        │
├──────────────────────────────────────────────────────────────┤
│              AGENT ORCHESTRATION LAYER                        │
│   DocumentAgent · ComplianceAgent · NDATriageAgent           │
│   DraftAgent · ObligationExtractor · RiskMemoGenerator       │
├──────────────────────────────────────────────────────────────┤
│                    TOOLING LAYER                              │
│   FactExtractor · BindingResolver · ClauseClassifier         │
│   AliasDetector · CrossRefExtractor · FactDiscovery          │
│   PlaybookLoader · ConfidenceCalibrator · ProvenanceFormatter│
├──────────────────────────────────────────────────────────────┤
│            CONTRACT INTELLIGENCE FABRIC                       │
│       TrustGraph (SQLite) · EmbeddingIndex (FAISS)           │
├──────────────────────────────────────────────────────────────┤
│                      DATA LAYER                               │
│            Raw Documents · Config · Audit Log                 │
└──────────────────────────────────────────────────────────────┘
```

**Architectural Rules:**
1. Downward-only data flow — Agents call tools, tools write to Fabric
2. Every tool output is typed — Fact, Binding, Inference, or Opinion
3. Agents are stateless — all state lives in TrustGraph and WorkspaceStore
4. Interaction layer never reasons — all reasoning in the Agent layer

### Three-Phase Extraction Pipeline

| Phase | Technology | What It Finds |
|-------|-----------|---------------|
| **1. Pattern Extraction** | Regex + structural parsing | Definitions, dates, amounts, durations, percentages, section refs, aliases, table data |
| **2. Semantic Indexing** | FAISS + `all-MiniLM-L6-v2` (384-dim) | Vector embeddings of every fact, clause, and binding for cosine-similarity search |
| **3. LLM Discovery** | Anthropic Claude | Implicit obligations, hidden risks, unstated assumptions, cross-clause implications |

Phases 1 and 2 are **deterministic and reproducible**. Phase 3 is **AI-augmented** — it finds what patterns miss.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12+, FastAPI, Uvicorn (async) |
| **LLM** | Anthropic Claude (via SDK), LiteLLM proxy compatible |
| **Embeddings** | sentence-transformers `all-MiniLM-L6-v2` (384-dim) |
| **Vector Search** | FAISS IndexFlatIP (cosine similarity) |
| **Storage** | SQLite with WAL mode, foreign keys |
| **Document Parsing** | python-docx (DOCX), PyMuPDF + pdfplumber (PDF) |
| **Streaming** | Server-Sent Events (SSE) via FastAPI |
| **MCP** | FastMCP (`mcp[cli]`), stdio + Streamable HTTP |
| **Frontend** | Vanilla JS, D3.js, docx-preview.js, PDF.js |
| **Testing** | pytest (794 tests), pytest-asyncio, httpx, factory-boy |
| **Deployment** | Docker Compose, Railway, Render |

---

## Quick Start

### Prerequisites

- **Python 3.12+** (tested on 3.12, 3.13, 3.14)
- **pip** or **uv** for package management

### 1. Clone and Install

```bash
git clone <repo-url> ContractOS
cd ContractOS
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Run the Server

```bash
# With Anthropic Claude
export ANTHROPIC_API_KEY="your-api-key"
python -m uvicorn contractos.api.app:create_app --host 127.0.0.1 --port 8742 --factory
```

### 3. Open the Copilot

Navigate to **http://127.0.0.1:8742/demo/copilot.html** — upload a contract and start asking questions.

### 4. Or Use via MCP (Cursor / Claude Desktop)

```json
{
  "mcpServers": {
    "contractos": {
      "command": "/path/to/.venv/bin/python",
      "args": ["-m", "contractos.mcp.server"],
      "env": {
        "PYTHONPATH": "src",
        "ANTHROPIC_API_KEY": "your-key"
      }
    }
  }
}
```

---

## Demo

### Document Copilot
Full document rendering with AI-powered sidebar — extraction summary, quick-action buttons, Q&A with provenance, playbook review, NDA triage, risk matrix, and redline suggestions.

```bash
open http://127.0.0.1:8742/demo/copilot.html
```

### API Console
22 pre-built requests covering the full API surface with drag-and-drop upload.

```bash
open http://127.0.0.1:8742/demo/
```

### TrustGraph Visualization
Interactive D3.js knowledge graph with node inspector, traversal explorer, and layout modes.

```bash
open http://127.0.0.1:8742/demo/graph.html
```

---

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/contracts/upload` | Upload and index a contract (DOCX/PDF) |
| `GET` | `/contracts/{id}/facts` | Extracted facts (paginated, filterable) |
| `GET` | `/contracts/{id}/clauses` | Classified clauses |
| `GET` | `/contracts/{id}/bindings` | Resolved definitions and aliases |
| `GET` | `/contracts/{id}/graph` | Full TrustGraph (nodes + edges) |
| `POST` | `/contracts/{id}/review` | Playbook compliance review |
| `POST` | `/contracts/{id}/triage` | NDA triage screening |
| `POST` | `/query/ask` | Q&A with provenance |

### Streaming (SSE)

| Endpoint | Description |
|----------|-------------|
| `/stream/{id}/review` | Progressive playbook review |
| `/stream/{id}/triage` | Progressive NDA triage |
| `/stream/{id}/discover` | Hidden fact discovery |
| `/stream/{id}/obligations` | Obligation extraction |
| `/stream/{id}/risk-memo` | Risk memo generation |
| `/stream/{id}/report` | HTML report download |

### MCP Tools

| Tool | Description |
|------|-------------|
| `upload_contract` | Upload and analyse a contract |
| `load_sample_contract` | Load built-in sample |
| `ask_question` | Q&A with provenance |
| `review_against_playbook` | Playbook compliance review |
| `triage_nda` | 10-point NDA screening |
| `discover_hidden_facts` | Implicit risk discovery |
| `extract_obligations` | Obligation extraction |
| `generate_risk_memo` | Risk assessment memo |
| `get_clause_gaps` | Mandatory fact gap analysis |
| `search_contracts` | Semantic search |
| `compare_clauses` | Cross-contract clause comparison |
| `generate_report` | HTML report generation |
| `clear_workspace` | Clear all data |

---

## Testing

Built entirely with TDD — tests written before code.

```bash
python -m pytest tests/ -v          # All 794 tests
python -m pytest tests/unit/        # 539 unit tests
python -m pytest tests/integration/ # 156 integration tests
python -m pytest tests/benchmark/   # 61 LegalBench benchmarks
```

### Test Coverage

| Category | Tests | Description |
|----------|------:|-------------|
| Unit | ~539 | Models, tools, storage, agents, FAISS, JSON parser |
| Integration | ~156 | Full API pipeline, SSE streams, real NDA documents |
| Contract | ~27 | API contract tests |
| Benchmark | ~61 | LegalBench contract_nli, definition extraction |
| **Total** | **794** | **All passing** |

### Real Document Validation

| Source | Documents | Description |
|--------|----------:|-------------|
| ContractNLI (Stanford NLP) | 50 | Real-world NDAs (corporate, M&A, government, SEC filings) |
| LegalBench fixtures | 4 | NDA, CUAD license, IT outsourcing, procurement framework |
| HuggingFace (CUAD) | 3 | Synthetic procurement contracts |

---

## Deployment

### Docker

```bash
cp .env.example .env    # Set ANTHROPIC_API_KEY, BASE_URL, MODEL
docker compose up --build -d
# Copilot UI: http://localhost:8742/demo/copilot.html
# MCP HTTP:   http://localhost:8743/mcp/
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key (falls back to mock LLM without it) |
| `ANTHROPIC_BASE_URL` | No | Custom endpoint (e.g. LiteLLM proxy) |
| `ANTHROPIC_MODEL` | No | Model name (default: `claude-sonnet-4-20250514`) |

---

## Project Structure

```
src/contractos/
├── agents/              # DocumentAgent, ComplianceAgent, DraftAgent, NDATriageAgent
├── api/                 # FastAPI app factory, routes, dependency injection
├── fabric/              # TrustGraph (SQLite), EmbeddingIndex (FAISS), WorkspaceStore
├── llm/                 # LLM provider abstraction (Anthropic + Mock)
├── mcp/                 # MCP server (13 tools, 10 resources, 5 prompts)
├── models/              # Pydantic domain models (Fact, Binding, Clause, Query, Review, Risk, Triage)
├── tools/               # FactExtractor, BindingResolver, ClauseClassifier, and more
├── cli.py               # CLI entry point
└── config.py            # YAML + env var configuration
```

---

## Specification

See [`spec/`](spec/) for the complete ecosystem blueprint:

1. [Vision](spec/vision.md) — What and why
2. [Truth Model](spec/truth-model.md) — The foundational epistemological model
3. [Architecture](spec/architecture.md) — System layers and design rules

See [`docs/EXECUTIVE_SUMMARY.md`](docs/EXECUTIVE_SUMMARY.md) for a comprehensive deep-dive into every feature, metric, and design decision.

---

## License

MIT

---

<p align="center">
  <strong>ContractOS</strong> — Don't read contracts. Understand them.
</p>
