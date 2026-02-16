# Phase 13 Research: ContractOS MCP Server

**Date**: 2026-02-09  
**Branch**: `001-single-contract-intelligence`  
**Objective**: Expose ContractOS capabilities as an MCP (Model Context Protocol) server so that AI coding assistants (Cursor, Claude Desktop, Claude Code) and other MCP clients can perform contract intelligence operations natively.

---

## 1. What We Have Today

ContractOS is a full-stack contract intelligence platform with:

| Layer | Capabilities | Files |
|-------|-------------|-------|
| **Parsing** | DOCX, PDF ingestion with paragraph/table/offset extraction | `tools/parsers.py`, `tools/docx_parser.py`, `tools/pdf_parser.py` |
| **Extraction** | Facts (parties, dates, amounts, products, locations), bindings, clauses, cross-references, mandatory fact slots | `tools/fact_extractor.py`, `tools/binding_resolver.py`, `tools/clause_classifier.py`, `tools/contract_patterns.py`, `tools/alias_detector.py`, `tools/mandatory_fact_extractor.py` |
| **Semantic Search** | FAISS-backed vector index with all-MiniLM-L6-v2 embeddings | `fabric/embedding_index.py` |
| **TrustGraph** | SQLite-backed knowledge graph (contracts, facts, bindings, clauses, cross-refs, inferences) | `fabric/trust_graph.py` |
| **Agents** | NDA Triage (10-point checklist), Playbook Compliance Review, Document Q&A, Draft/Redline Generation | `agents/nda_triage_agent.py`, `agents/compliance_agent.py`, `agents/document_agent.py`, `agents/draft_agent.py` |
| **Discovery** | LLM-powered hidden fact discovery (implicit obligations, risks) | `tools/fact_discovery.py` |
| **Analysis** | Obligation extraction, risk memo generation, clause gap analysis | `api/routes/stream.py` |
| **Provenance** | Full provenance chains linking every answer to source material | `tools/provenance_formatter.py`, `models/provenance.py` |
| **Workspaces** | Multi-document workspaces with session tracking | `fabric/workspace_store.py` |
| **API** | 25+ REST endpoints with SSE streaming | `api/routes/*.py` |
| **UI** | Copilot sidebar, TrustGraph visualizer, demo console | `demo/*.html` |

---

## 2. What MCP Gives Us

MCP (Model Context Protocol) is Anthropic's open standard for connecting AI assistants to external tools and data. It defines three primitives:

| Primitive | Purpose | Analogy |
|-----------|---------|---------|
| **Tools** | Actions the AI can invoke (side effects, computation) | Function calls |
| **Resources** | Read-only data the AI can access | GET endpoints |
| **Prompts** | Reusable prompt templates the user can invoke | Macros / workflows |

**SDK**: `mcp` Python package (v1.26.0, MIT license, Python ≥3.10)  
**Transports**: stdio (local), Streamable HTTP (remote), SSE (deprecated)  
**Clients**: Cursor, Claude Desktop, Claude Code CLI, MCP Inspector

---

## 3. MCP Tool Design — What ContractOS Should Expose

### 3.1 Tools (Actions — the AI can call these)

**Principle**: Design tools for *user intents*, not raw API calls. Group related operations.

| # | Tool Name | Description | Maps To |
|---|-----------|-------------|---------|
| 1 | `upload_contract` | Upload and analyze a contract file (DOCX/PDF). Returns document ID, extracted facts count, clause count. | `POST /contracts/upload` |
| 2 | `load_sample_contract` | Load a built-in sample contract for testing. | `POST /contracts/samples/{filename}/load` |
| 3 | `ask_question` | Ask a natural-language question about one or more contracts. Returns grounded answer with provenance. | `POST /query/ask` |
| 4 | `review_against_playbook` | Run playbook compliance review. Returns findings (GREEN/YELLOW/RED) with redline suggestions. | `POST /contracts/{id}/review` |
| 5 | `triage_nda` | Run NDA triage screening (10-point checklist). Returns pass/fail per item with classification. | `POST /contracts/{id}/triage` |
| 6 | `discover_hidden_facts` | LLM-powered discovery of implicit obligations, risks, and hidden facts. | `POST /contracts/{id}/discover` |
| 7 | `extract_obligations` | Extract and categorize all contractual obligations (affirmative, negative, conditional). | SSE `/stream/{id}/obligations` |
| 8 | `generate_risk_memo` | Generate a structured risk assessment memo with ratings and recommendations. | SSE `/stream/{id}/risk-memo` |
| 9 | `get_clause_gaps` | Identify mandatory fact gaps per clause type. | `GET /contracts/{id}/clauses/gaps` |
| 10 | `search_contracts` | Semantic search across indexed contracts. | `fabric/embedding_index.search()` |
| 11 | `compare_clauses` | Compare specific clause types across two contracts. | New — combines Q&A + multi-doc |
| 12 | `generate_report` | Generate a downloadable HTML report (review/triage/discovery). | `GET /stream/{id}/report` |
| 13 | `clear_workspace` | Clear all uploaded contracts and analysis data. | `DELETE /contracts/clear` |

**Total: 13 tools** (well within the 20-30 best-practice range)

### 3.2 Resources (Read-only data)

| # | URI Pattern | Description | Maps To |
|---|-------------|-------------|---------|
| 1 | `contractos://contracts` | List all indexed contracts | `GET /contracts` |
| 2 | `contractos://contracts/{id}` | Contract metadata | `GET /contracts/{id}` |
| 3 | `contractos://contracts/{id}/facts` | Extracted facts for a contract | `GET /contracts/{id}/facts` |
| 4 | `contractos://contracts/{id}/clauses` | Classified clauses | `GET /contracts/{id}/clauses` |
| 5 | `contractos://contracts/{id}/bindings` | Definitions and aliases | `GET /contracts/{id}/bindings` |
| 6 | `contractos://contracts/{id}/graph` | TrustGraph (nodes + edges) | `GET /contracts/{id}/graph` |
| 7 | `contractos://samples` | Available sample contracts | `GET /contracts/samples` |
| 8 | `contractos://chat/history` | Chat Q&A history | `GET /query/history` |
| 9 | `contractos://health` | Server health and config | `GET /health` |
| 10 | `contractos://playbook` | Current playbook configuration | `load_default_playbook()` |

### 3.3 Prompts (Reusable workflows)

| # | Prompt Name | Description | Parameters |
|---|-------------|-------------|------------|
| 1 | `full_contract_analysis` | Run complete analysis pipeline: extract → triage → review → obligations → risk memo | `document_id` |
| 2 | `due_diligence_checklist` | Structured due diligence review with all checks | `document_id` |
| 3 | `negotiation_prep` | Prepare negotiation strategy from playbook review findings | `document_id` |
| 4 | `risk_summary` | Executive risk summary combining all analysis outputs | `document_id` |
| 5 | `clause_comparison` | Compare clause language across two contracts | `doc_id_1`, `doc_id_2`, `clause_type` |

---

## 4. Architecture Decision

### 4.1 Reuse Existing Infrastructure

The MCP server should **reuse** the existing ContractOS fabric, agents, and tools — NOT duplicate them. The MCP server is a thin adapter layer:

```
┌─────────────────────────────────────────────┐
│  MCP Clients (Cursor, Claude Desktop, etc.) │
└─────────────────┬───────────────────────────┘
                  │ MCP Protocol (stdio / Streamable HTTP)
┌─────────────────▼───────────────────────────┐
│         MCP Server (src/contractos/mcp/)     │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │  Tools   │ │Resources │ │   Prompts    │ │
│  └────┬─────┘ └────┬─────┘ └──────┬───────┘ │
│       │             │              │          │
│  ┌────▼─────────────▼──────────────▼───────┐ │
│  │        Shared AppState / Context        │ │
│  │  (TrustGraph, EmbeddingIndex, Agents)   │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│        Existing ContractOS Core              │
│  fabric/ │ agents/ │ tools/ │ models/        │
└─────────────────────────────────────────────┘
```

### 4.2 Transport Strategy

| Mode | Transport | Use Case |
|------|-----------|----------|
| **Local** (default) | stdio | Cursor integration, Claude Desktop |
| **Remote** | Streamable HTTP | VDI deployment, team sharing, CI/CD |

Both transports share the same tool/resource/prompt definitions. The transport is selected at startup via CLI flag or environment variable.

### 4.3 Server Strategy — Single Container

ContractOS runs **two servers from the same codebase**, sharing a single `AppState`:

1. **FastAPI HTTP server** (existing) — serves the Copilot UI, REST API, SSE streams (port 8742)
2. **MCP server** (new) — serves MCP clients via stdio or Streamable HTTP (port 8743)

**Critical constraint:** SQLite doesn't support concurrent writers across processes. Both servers MUST share the same `AppState` singleton. In Docker, both run in the **same container** via an `entrypoint.sh` supervisor script (FastAPI as main process, MCP HTTP as background).

When running as MCP stdio (local Cursor/Claude Desktop), only the MCP server starts — no FastAPI.

### 4.4 Container Engine Compatibility

All deployment artifacts use OCI-standard commands and Compose v2 format. Compatible with:
- **Docker Desktop** (`docker compose`)
- **Rancher Desktop** (`nerdctl compose` or Docker-compatible CLI)
- **Podman** (`podman-compose` or `podman compose`)
- Any OCI-compliant container runtime

### 4.4 File Structure

```
src/contractos/mcp/
├── __init__.py
├── server.py          # FastMCP server definition + startup
├── tools.py           # @mcp.tool() definitions (13 tools)
├── resources.py       # @mcp.resource() definitions (10 resources)
├── prompts.py         # @mcp.prompt() definitions (5 prompts)
└── context.py         # Shared context (AppState initialization)
```

---

## 5. Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| Evidence Before Intelligence | PASS | All MCP tool outputs include provenance chains |
| Truth Model Integrity | PASS | MCP tools return typed outputs (Fact, Binding, Inference, Opinion) |
| Inference Over Extraction | PASS | Tools expose both extraction and reasoning (discover, review, triage) |
| Auditability By Design | PASS | Every tool response includes confidence scores and reasoning chains |
| Repository-Level Reasoning | PASS | `ask_question` supports multi-document queries, `compare_clauses` is cross-document |
| Configuration Over Code | PASS | Transport, port, LLM provider all configurable via env vars |
| Context Is Persistent | PASS | TrustGraph and workspaces persist across MCP sessions |
| Test-Driven Development | PASS | Unit tests for each tool, integration tests for MCP protocol |

---

## 6. Key Decisions

1. **Package**: `mcp[cli]` (v1.26.0) — official Anthropic SDK
2. **Entry point**: `python -m contractos.mcp.server` (stdio) or `--transport http` (Streamable HTTP)
3. **Cursor config**: `.cursor/mcp.json` in project root for zero-config local usage
4. **Docker**: Add MCP port (default 8743) to docker-compose for remote transport
5. **File uploads**: MCP tools accept file paths (stdio) or base64-encoded content (HTTP)
6. **Long-running operations**: Tools like `review_against_playbook` use `ctx.report_progress()` for progress updates
7. **Error handling**: Agent-friendly error messages that guide the AI to fix issues
