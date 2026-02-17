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
│    Browser Copilot · API Console · TrustGraph Viz · MCP      │
├──────────────────────────────────────────────────────────────┤
│                MCP INTEGRATION LAYER                          │
│   13 Tools · 10 Resources · 5 Prompts (stdio + HTTP)        │
│   Cursor · Claude Desktop · Claude Code · Any MCP Client    │
├──────────────────────────────────────────────────────────────┤
│                     WORKSPACE LAYER                           │
│          WorkspaceStore · SessionStore · ContextMemory        │
├──────────────────────────────────────────────────────────────┤
│              AGENT ORCHESTRATION LAYER                        │
│   DocumentAgent · ComplianceAgent · NDATriageAgent           │
│   DraftAgent · ObligationExtractor · RiskMemoGenerator       │
│         (FAISS retrieval → context building → LLM → answer)  │
├──────────────────────────────────────────────────────────────┤
│                   STREAMING LAYER (SSE)                       │
│   Progressive reasoning · Parallel LLM batching              │
│   Real-time step events · Report generation                  │
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
1. **Downward-only data flow** — Agents call tools, tools write to Fabric
2. **Every tool output is typed** — Fact, Binding, Inference, or Opinion
3. **Agents are stateless** — all state lives in TrustGraph and WorkspaceStore
4. **Interaction layer never reasons** — all reasoning in the Agent layer
5. **MCP wraps, never duplicates** — MCPContext composes AppState via delegation

---

## What's Been Built

### By the Numbers

| Metric | Value |
|--------|-------|
| Python source modules | 63 |
| Lines of production code | ~9,800 |
| Test files | 69 |
| Lines of test code | ~14,800 (1.5x production code) |
| **Passing tests** | **794** |
| API endpoints | 34 |
| SSE streaming endpoints | 6 |
| MCP tools | 13 |
| MCP resources | 10 |
| MCP prompts | 5 |
| Demo UI pages | 3 |
| Sample contracts | 4 (2 PDF, 2 DOCX) |
| Real NDA documents tested | 50 (ContractNLI dataset, Stanford NLP) |
| Deployment configs | Docker Compose (single-container), Railway, Render, Procfile |

### API Surface (34 Endpoints + MCP)

| Category | Endpoints | Key Operations |
|----------|----------|----------------|
| **Contracts** | 16 | Upload, list, clear, samples, facts, clauses, bindings, graph, gaps, discover, review, triage |
| **Query** | 3 | Ask (with conversation context), history, clear history |
| **Workspaces** | 7 | Create, list, get, add/remove documents, check changes, sessions |
| **Streaming** | 6 | SSE review, triage, discover, obligations, risk-memo, report download |
| **Health** | 2 | Health check, configuration |
| **MCP** | 13 tools + 10 resources + 5 prompts | Full contract intelligence via Model Context Protocol (stdio + HTTP) |

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
| `ReviewFinding` + `ReviewResult` | Playbook review findings with severity, risk score, redlines |
| `RedlineSuggestion` | Proposed alternative language with rationale and fallback |
| `RiskProfile` + `RiskScore` | Severity × likelihood risk matrix with tier distribution |
| `TriageResult` + `ChecklistResult` | NDA triage classification and per-item results |
| `PlaybookConfig` + `PlaybookPosition` | Configurable playbook with positions and acceptable ranges |

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

### 5. Playbook Review with Redline Generation
Review any contract against a configurable playbook:
- Clause-by-clause comparison with GREEN/YELLOW/RED classification
- Automated redline suggestions (alternative language + rationale + fallback)
- Risk profile with severity × likelihood matrix
- Tier-based negotiation strategy (Must-have / Should-have / Nice-to-have)
- Streaming progressive updates via SSE as each clause is analyzed

### 6. NDA Triage Screening
Automated 10-point NDA checklist with hybrid evaluation:
- Pattern-based checks (carveouts, term duration, governing law, problematic provisions)
- LLM verification for nuanced items (receiving party obligations, remedies)
- GREEN/YELLOW/RED routing with timeline recommendations
- Real-time streaming of each checklist item result

### 7. Obligation Extraction
Extract all contractual obligations for each party:
- Affirmative (must do), Negative (must not do), Conditional (if X then Y)
- Deadlines, clause references, and breach consequences
- Streaming progressive results as obligations are discovered

### 8. Risk Memo Generation
Structured risk assessment with:
- Executive summary and overall risk rating
- Key risks with severity/likelihood scoring and mitigation strategies
- Missing protections identification
- Prioritized recommendations with owners
- Escalation items requiring senior counsel

### 9. Cursor-Like Progressive Reasoning (SSE Streaming)
Real-time streaming UI showing the AI's actual thought process:
- Server-Sent Events (SSE) deliver each reasoning step as it happens
- Intermediate results shown progressively (e.g., GREEN/YELLOW/RED counts update live)
- Each step loads after the previous completes — no fake delays
- Pulsing animation on active steps, checkmark on completion
- Parallel LLM calls in batches for 3-4x speed improvement

### 10. Report Download
Download comprehensive HTML reports for any analysis:
- Playbook Review Report (findings, redlines, risk profile, negotiation strategy)
- NDA Triage Report (classification, checklist results, key issues)
- Discovery Report (hidden facts with evidence and risk levels)
- Professional dark-theme styling with print-friendly CSS

### 11. TrustGraph Visualization
Interactive D3.js force-directed graph showing the full knowledge graph — contracts, clauses, facts, bindings, and cross-references as connected nodes with typed edges.

### 12. MCP Server — Model Context Protocol Integration

ContractOS exposes its full contract intelligence as an **MCP server** (Anthropic's open standard), enabling any MCP-compatible AI assistant to use ContractOS as a tool:

**13 Tools:**

| Tool | Description |
|------|-------------|
| `upload_contract` | Upload and analyse a contract (PDF/DOCX) |
| `load_sample_contract` | Load a built-in sample for testing |
| `ask_question` | Natural-language Q&A with provenance |
| `review_against_playbook` | Playbook compliance review with redlines |
| `triage_nda` | 10-point NDA screening checklist |
| `discover_hidden_facts` | LLM-powered implicit risk discovery |
| `extract_obligations` | Obligation extraction (affirmative/negative/conditional) |
| `generate_risk_memo` | Structured risk assessment memo |
| `get_clause_gaps` | Mandatory fact gap analysis |
| `search_contracts` | Semantic search across all indexed contracts |
| `compare_clauses` | Cross-contract clause comparison |
| `generate_report` | HTML report generation (review/triage/discovery) |
| `clear_workspace` | Clear all contracts and analysis data |

**10 Resources** (read-only data): contracts list, contract metadata, facts, clauses, bindings, TrustGraph, samples, chat history, health, playbook config.

**5 Prompts** (reusable workflows): full contract analysis pipeline, due diligence checklist, negotiation prep, risk summary, clause comparison.

**Transport:** stdio (Cursor, Claude Desktop, Claude Code) and Streamable HTTP (Docker, remote deployment).

**Architecture:** `MCPContext` wraps the existing `AppState` via composition — no duplication of TrustGraph, EmbeddingIndex, or LLM provider. All LLM calls route through the provider abstraction.

### 13. Sample Contract Playground
4 pre-built contracts (simple NDA, complex procurement framework, simple procurement, complex IT outsourcing) available for one-click loading — users can explore the system immediately.

### 14. Multi-Document Workspaces
Create workspaces containing multiple contracts. Ask cross-document questions with document-labeled provenance.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.14, FastAPI, Uvicorn (async) |
| **LLM** | Anthropic Claude (via SDK), LiteLLM proxy compatible |
| **Embeddings** | sentence-transformers `all-MiniLM-L6-v2` (384-dim, ~90MB) |
| **Vector Search** | FAISS IndexFlatIP (inner product on L2-normalized = cosine similarity) |
| **Storage** | SQLite with WAL mode, foreign keys |
| **Document Parsing** | python-docx (DOCX), PyMuPDF + pdfplumber (PDF) |
| **Streaming** | Server-Sent Events (SSE) via FastAPI StreamingResponse |
| **MCP** | FastMCP (`mcp[cli]`), stdio + Streamable HTTP transports |
| **Frontend** | Vanilla JS, EventSource API, docx-preview.js, PDF.js, D3.js |
| **Testing** | pytest, pytest-asyncio, httpx (async), respx, factory-boy |
| **Deployment** | Docker Compose (single-container, OCI-compliant), Railway, Render |
| **Configuration** | YAML + env var overrides, Pydantic settings |

---

## Test-Driven Development

The entire system was built TDD — tests written before code:

| Category | Tests | Description |
|----------|------:|-------------|
| Unit Tests | ~539 | Models, tools, storage, agents, FAISS, query persistence, JSON parser, MCP server |
| Integration Tests | ~156 | Full API pipeline, SSE streams, obligation/risk-memo extraction |
| Contract Tests | ~27 | API contract tests via AsyncClient |
| Benchmark Tests | ~61 | LegalBench contract_nli, definition extraction |
| MCP Tests | ~15 | Server creation, tool/resource/prompt registration, context lifecycle |
| **Total** | **794** | **All passing** |

- **50 real NDA documents** from ContractNLI (Stanford NLP) tested end-to-end
- **~14.8K lines of test code** — 1.5x the production code
- Tests run in ~62 seconds

---

## Deployment

### Docker Compose (Production)

```bash
cp .env.example .env    # Fill in ANTHROPIC_API_KEY, BASE_URL, MODEL
docker compose up --build -d
# FastAPI + Copilot UI: http://<host>:8742/demo/copilot.html
# MCP HTTP endpoint:    http://<host>:8743/mcp/
```

- **Single-container deployment** — FastAPI + MCP HTTP server managed by `entrypoint.sh`
- **Container engine agnostic** — Docker Desktop, Rancher Desktop (`nerdctl`), Podman, or any OCI runtime
- Pre-baked embedding model (no cold-start downloads)
- Persistent SQLite volume
- 4GB memory allocation, 2GB reserved
- Health checks, auto-restart, structured logging
- Single command deployment on any VDI

### MCP Client Setup (Cursor / Claude Desktop)

```bash
cp .cursor/mcp.json.example .cursor/mcp.json
# Edit: set absolute path to .venv/bin/python and your API key
```

- stdio transport for local IDE integration (Cursor, Claude Desktop, Claude Code)
- Streamable HTTP transport for remote/Docker deployment
- `.cursor/mcp.json` is git-ignored (contains API keys)

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
| Phase 10 | Playbook Intelligence & Risk Framework | 80+ |
| Phase 12 | SSE Streaming, Expanded Legal Analysis, Reports | 36 |
| Phase 13 | MCP Server — Model Context Protocol | 15 |
| **Total** | **280+ tasks** | **794** |

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

Then they click **"Review Against Playbook"** — and watch in real-time as ContractOS:
1. Loads the organization's standard positions
2. Compares each clause (progress streaming live: "5/17 positions evaluated — 3 GREEN, 1 YELLOW, 1 RED")
3. Generates redline suggestions for deviations
4. Builds a risk profile and negotiation strategy
5. Offers a downloadable HTML report

They click **"Risk Memo"** and get a structured assessment with severity/likelihood scoring, missing protections, prioritized recommendations, and escalation items — all streamed progressively as the AI reasons.

Or — they stay in their IDE. In Cursor, they type:

> "Load the simple NDA sample and run a full contract analysis"

The AI assistant calls ContractOS MCP tools — `load_sample_contract`, `triage_nda`, `review_against_playbook`, `extract_obligations`, `generate_risk_memo`, `discover_hidden_facts` — and synthesizes a comprehensive executive summary, all without leaving the editor.

That is ContractOS — the operating system for contract intelligence.
