# ContractOS — Executive Summary

> The operating system for contract intelligence.

---

## What Is ContractOS?

ContractOS is an **AI-powered contract intelligence ecosystem** that transforms static legal documents into structured, queryable, explainable legal knowledge. It ingests contracts (PDF/DOCX), extracts structured facts through a multi-phase pipeline, builds a typed knowledge graph, and provides an interactive AI copilot for contract analysis — all with full provenance tracking.

ContractOS is **not** a document chatbot, a keyword search engine, or an LLM wrapper. It is a **legal reasoning substrate** — a system that separates what a contract says (facts), what terms mean (bindings), what can be derived (inferences), and what someone thinks about it (opinions).

---

## The Problem

Contracts encode obligations, risks, and rights **implicitly** — across tables buried in schedules, scattered clauses that reference each other, defined terms that transform meaning, and amendment chains where later documents override earlier ones.

Most contract AI systems fail because they:
1. Treat contracts as flat text blobs
2. Rely on keyword matching or shallow embedding search
3. Answer questions without grounding, provenance, or confidence
4. Cannot distinguish between what a contract says vs. what it implies vs. what someone thinks about it

---

## How ContractOS Solves It

### The Truth Model

ContractOS introduces a strict four-layer truth model:

| Layer | What It Is | Example | Persistence |
|-------|-----------|---------|-------------|
| **Fact** | Directly grounded in contract text | "Term: 24 months" | Immutable, always persisted |
| **Binding** | Explicitly stated semantic mapping | "'Company' means Acme Corp" | Persisted, scoped to contract |
| **Inference** | Derived claim from facts + knowledge | "Contract expires Dec 2025" | Persisted with confidence + provenance |
| **Opinion** | Contextual judgment | "Missing force majeure is a risk" | Computed on demand, never persisted as truth |

This separation is **foundational** — it ensures every answer is auditable and every claim is traceable to source text.

### Three-Phase Extraction Pipeline

Every uploaded contract goes through a deterministic, auditable pipeline:

| Phase | Technology | What It Finds |
|-------|-----------|---------------|
| **Phase 1: Pattern Extraction** | Regex + structural parsing | Definitions, dates, monetary values, durations, percentages, section references, entity aliases, table data |
| **Phase 2: Semantic Indexing** | FAISS + `all-MiniLM-L6-v2` (384-dim) | Vector embeddings of every fact, clause, and binding for cosine-similarity semantic search |
| **Phase 3: LLM Discovery** | Anthropic Claude | Implicit obligations, hidden risks, unstated assumptions, cross-clause implications, missing protections, ambiguous terms |

Phase 1 and 2 are **deterministic and reproducible**. Phase 3 is **AI-augmented** — it finds what patterns miss.

### TrustGraph — The Knowledge Fabric

Every extracted entity is stored in a **typed, relational knowledge graph** (SQLite-backed with WAL mode):

- **Facts** — extracted data points with evidence spans, char offsets, and confidence
- **Clauses** — classified by type (termination, confidentiality, payment, indemnification, etc.)
- **Bindings** — resolved definitions and party aliases with scope
- **Cross-References** — links between clauses ("subject to Section 5.2")
- **Mandatory Fact Slots** — gap analysis (what's missing from each clause type)
- **Provenance Chains** — full audit trail from answer back to source text

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     INTERACTION LAYER                         │
│         Browser Copilot · API Console · TrustGraph Viz       │
├──────────────────────────────────────────────────────────────┤
│                     WORKSPACE LAYER                           │
│          WorkspaceStore · SessionStore · ContextMemory        │
├──────────────────────────────────────────────────────────────┤
│              AGENT ORCHESTRATION LAYER                        │
│                    DocumentAgent                              │
│         (FAISS retrieval → context building → LLM → answer)  │
├──────────────────────────────────────────────────────────────┤
│                    TOOLING LAYER                              │
│   FactExtractor · BindingResolver · ClauseClassifier         │
│   AliasDetector · CrossRefExtractor · FactDiscovery          │
│   ConfidenceCalibrator · ProvenanceFormatter                 │
├──────────────────────────────────────────────────────────────┤
│            CONTRACT INTELLIGENCE FABRIC                       │
│       TrustGraph (SQLite) · EmbeddingIndex (FAISS)           │
├──────────────────────────────────────────────────────────────┤
│                      DATA LAYER                               │
│            Raw Documents · Config · Audit Log                 │
└──────────────────────────────────────────────────────────────┘
```

**Architectural Rules:**
1. **Downward-only data flow** — Agents call tools, tools write to Fabric
2. **Every tool output is typed** — Fact, Binding, Inference, or Opinion
3. **Agents are stateless** — all state lives in TrustGraph and WorkspaceStore
4. **Interaction layer never reasons** — all reasoning in the Agent layer

---

## What's Been Built

### By the Numbers

| Metric | Value |
|--------|-------|
| Python source modules | 42 |
| Lines of production code | ~5,936 |
| Test files | 51 |
| Lines of test code | ~12,174 (2x production code) |
| **Passing tests** | **666** |
| API endpoints | 25 |
| Demo UI pages | 3 |
| Sample contracts | 4 (2 PDF, 2 DOCX) |
| Real NDA documents tested | 50 (ContractNLI dataset, Stanford NLP) |
| Deployment configs | Docker Compose, Railway, Render, Procfile |

### API Surface (25 Endpoints)

| Category | Endpoints | Key Operations |
|----------|----------|----------------|
| **Contracts** | 12 | Upload, list, clear, samples, facts, clauses, bindings, graph, gaps, discover |
| **Query** | 3 | Ask (with conversation context), history, clear history |
| **Workspaces** | 7 | Create, list, get, add/remove documents, check changes, sessions |
| **Health** | 2 | Health check, configuration |

### Pydantic Model Layer

| Model | Purpose |
|-------|---------|
| `Fact` + `FactEvidence` | Extracted data point with text span, char offsets, location hint |
| `Binding` | Resolved definition or alias with scope |
| `Clause` | Classified clause with type, heading, section number, contained facts |
| `CrossReference` | Link between clauses with reference type and effect |
| `Contract` | Document metadata (parties, word count, file hash) |
| `ProvenanceChain` | Audit trail from answer to source evidence |
| `QueryResult` | Answer with confidence, provenance, retrieval method |
| `ChatTurn` | Single Q&A pair for multi-turn conversation context |
| `Workspace` + `ReasoningSession` | Persistent workspace and session state |

---

## Key Features

### 1. Upload & Instant Analysis
Upload any PDF or DOCX contract. Within seconds:
- Full document rendering (high-fidelity DOCX via docx-preview.js, PDF via PDF.js)
- Extraction summary: fact count, clause count, binding count, word count
- 8 quick-action buttons (Parties, Payment, Termination, Confidentiality, Liability, Dates, Definitions, Summary)

### 2. Semantic Q&A with Provenance
Ask natural language questions. The system:
1. Searches FAISS vector index for relevant facts (cosine similarity, top-k)
2. Builds context from TrustGraph (facts + bindings + clauses)
3. Sends to Claude with a specialized system prompt
4. Returns answer with confidence label, provenance chain, and clickable source references
5. Retains conversation context across turns within a session

### 3. Hidden Fact Discovery (LLM Phase 3)
One-click LLM analysis that identifies:
- Implicit obligations not stated as "shall" or "must"
- Liability exposure and missing caps
- Unstated assumptions the contract relies on
- Cross-clause implications from combining provisions
- Missing standard protections (force majeure, IP, data protection)
- Ambiguous terms that could be interpreted multiple ways

### 4. Document Highlighting with Provenance
Click any cited fact in the Copilot sidebar to:
- Scroll to the exact location in the rendered document
- Highlight the source text with a visual flash animation
- Multi-strategy text matching for reliable highlighting across document structures

### 5. Cursor-Like Reasoning Steps
Animated multi-step UI showing the AI's thought process:
- Searching document index...
- Reading relevant sections...
- Reasoning with LLM...
- Building provenance chain...
- Answer ready (with timing and fact count)

### 6. TrustGraph Visualization
Interactive D3.js force-directed graph showing the full knowledge graph — contracts, clauses, facts, bindings, and cross-references as connected nodes with typed edges.

### 7. Sample Contract Playground
4 pre-built contracts (simple NDA, complex procurement framework, simple procurement, complex IT outsourcing) available for one-click loading — users can explore the system immediately.

### 8. Multi-Document Workspaces
Create workspaces containing multiple contracts. Ask cross-document questions with document-labeled provenance.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, Uvicorn (async) |
| **LLM** | Anthropic Claude (via SDK), LiteLLM proxy compatible |
| **Embeddings** | sentence-transformers `all-MiniLM-L6-v2` (384-dim, ~90MB) |
| **Vector Search** | FAISS IndexFlatIP (inner product on L2-normalized = cosine similarity) |
| **Storage** | SQLite with WAL mode, foreign keys |
| **Document Parsing** | python-docx (DOCX), PyMuPDF + pdfplumber (PDF) |
| **Frontend** | Vanilla JS, docx-preview.js, PDF.js, D3.js |
| **Testing** | pytest, pytest-asyncio, httpx (async), respx, factory-boy |
| **Deployment** | Docker Compose (production), Railway, Render |
| **Configuration** | YAML + env var overrides, Pydantic settings |

---

## Test-Driven Development

The entire system was built TDD — tests written before code:

| Category | Tests | Description |
|----------|------:|-------------|
| Unit Tests | ~480 | Models, tools, storage, agents, FAISS, query persistence |
| Integration Tests | ~120 | Full API pipeline (upload → extract → query → answer) |
| Contract Tests | ~27 | API contract tests via AsyncClient |
| Benchmark Tests | ~39 | LegalBench contract_nli, definition extraction |
| **Total** | **666** | **All passing** |

- **50 real NDA documents** from ContractNLI (Stanford NLP) tested end-to-end
- **~12K lines of test code** — 2x the production code
- Tests run in ~55 seconds

---

## Deployment

### Docker Compose (Production)

```bash
cp .env.example .env    # Fill in ANTHROPIC_API_KEY, BASE_URL, MODEL
docker compose up --build -d
# Access: http://<host>:8742/demo/copilot.html
```

- Pre-baked embedding model (no cold-start downloads)
- Persistent SQLite volume
- 4GB memory allocation, 2GB reserved
- Health checks, auto-restart, structured logging
- Single command deployment on any VDI

---

## Development Phases Completed

| Phase | Description | Tests |
|-------|-------------|------:|
| Phase 1 | Project Setup & Infrastructure | 5 |
| Phase 2 | Foundation (Models, TrustGraph, Config) | 15 |
| Phase 3 | Document Ingestion & Fact Extraction | 12 |
| Phase 4 | Binding Resolution | 4 |
| Phase 5 | Single-Document Q&A | 10 |
| Phase 6 | Provenance Display & Pipeline Wiring | 4 |
| Phase 7 | Workspace Persistence | 5 |
| Phase 7a | Algorithm Docs, TrustGraph Viz, LegalBench | — |
| Phase 7b | FAISS Vector Indexing, Provenance Viz | — |
| Phase 7c | TrustGraph Branding, Chat Persistence | — |
| Phase 7d | Chat History, Clear All, Multi-Doc | — |
| Phase 7e | Real ContractNLI Testing (50 NDAs) | 54 |
| Phase 8a | Browser-Based Document Copilot | 9 |
| Phase 8b | Provenance Highlighting + LLM Discovery | 13 |
| Phase 8c | Conversation Context Retention | 15 |
| Phase 8d | Sample Contracts & Playground | 7 |
| **Total** | **195 tasks, 666 tests** | **666** |

---

## What Success Looks Like

A user opens the ContractOS Copilot, uploads a vendor contract, and asks:

> "Does this contract indemnify the buyer for data breach?"

ContractOS:
1. **Extracts** facts from the document (parties, clauses, definitions, obligations)
2. **Resolves** bindings ("Service Provider" → "Dell Technologies")
3. **Searches** FAISS index for indemnity-related facts
4. **Reasons** with Claude, grounded in extracted evidence
5. **Returns** an answer with confidence (0.92 — high), provenance chain (3 facts cited), and clickable source references
6. The user clicks a cited fact → the document scrolls to and highlights the exact text

The user didn't search. They didn't read 40 pages. They asked a question and got a **grounded, explainable, auditable answer**.

That is ContractOS.
