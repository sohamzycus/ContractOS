# Implementation Plan: Phase 13 — ContractOS MCP Server

**Branch**: `001-single-contract-intelligence` | **Date**: 2026-02-09 | **Spec**: [spec.md](./spec.md)  
**Input**: Expose ContractOS as an MCP server for AI assistant integration (Cursor, Claude Desktop, Claude Code)

## Summary

Create a Model Context Protocol (MCP) server that wraps all ContractOS capabilities — contract upload, extraction, playbook review, NDA triage, hidden fact discovery, obligation extraction, risk memo generation, semantic Q&A, and TrustGraph access — as MCP tools, resources, and prompts. This enables any MCP-compatible AI assistant to perform contract intelligence operations natively, without needing the Copilot UI.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: `mcp[cli]>=1.26.0`, FastMCP, existing ContractOS stack (FastAPI, Anthropic, FAISS, sentence-transformers, PyMuPDF, python-docx)  
**Storage**: SQLite (TrustGraph), FAISS (vector index) — shared with existing FastAPI server  
**Testing**: pytest, pytest-asyncio, httpx, mcp SDK test utilities  
**Target Platform**: macOS/Linux (stdio for local, Streamable HTTP for remote/Docker)  
**Project Type**: Single project — new `src/contractos/mcp/` package alongside existing `src/contractos/api/`  
**Performance Goals**: Tool response <5s for extraction queries, <30s for full analysis (review/triage/discover)  
**Constraints**: Single-process SQLite (no concurrent writers), embedding model ~250MB RAM  
**Scale/Scope**: Same as existing — 1K–10K contracts, single user per MCP session

## Constitution Check

*GATE: Pre-design check*

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Evidence Before Intelligence | ✅ PASS | Every MCP tool returns provenance chains |
| 2 | Truth Model Integrity | ✅ PASS | Tools return typed outputs (Fact/Binding/Inference/Opinion) |
| 3 | Inference Over Extraction | ✅ PASS | `discover_hidden_facts`, `review_against_playbook` perform reasoning |
| 4 | Auditability By Design | ✅ PASS | Confidence scores + reasoning chains in every response |
| 5 | Repository-Level Reasoning | ✅ PASS | `ask_question` supports multi-doc, `compare_clauses` is cross-doc |
| 6 | Configuration Over Code | ✅ PASS | Transport, port, LLM provider via env vars |
| 7 | Context Is Persistent | ✅ PASS | TrustGraph + workspaces persist across sessions |
| 8 | Test-Driven Development | ✅ PASS | TDD for all tools, resources, prompts |

## Project Structure

### Documentation (this feature)

```text
specs/001-single-contract-intelligence/
├── plan.md                    # This file
├── research-mcp.md            # Phase 0 research
├── data-model-mcp.md          # Phase 1 data model
├── contracts/mcp-server.md    # Phase 1 API contract
└── quickstart-mcp.md          # Phase 1 quickstart
```

### Source Code

```text
src/contractos/
├── mcp/                       # NEW — MCP server package
│   ├── __init__.py
│   ├── server.py              # FastMCP server + startup + transport selection
│   ├── tools.py               # 13 @mcp.tool() definitions
│   ├── resources.py           # 10 @mcp.resource() definitions
│   ├── prompts.py             # 5 @mcp.prompt() definitions
│   └── context.py             # Shared AppState initialization (reuses fabric/)
├── api/                       # EXISTING — FastAPI HTTP server (unchanged)
├── agents/                    # EXISTING — reused by MCP tools
├── tools/                     # EXISTING — reused by MCP tools
├── fabric/                    # EXISTING — reused by MCP context
└── models/                    # EXISTING — reused for typed responses

tests/
├── unit/test_mcp_tools.py     # Unit tests for each MCP tool
├── unit/test_mcp_resources.py # Unit tests for each MCP resource
├── unit/test_mcp_prompts.py   # Unit tests for each MCP prompt
└── integration/test_mcp_server.py  # End-to-end MCP protocol tests

.cursor/mcp.json.example       # NEW — Cursor MCP client config template (checked in)
.cursor/mcp.json               # LOCAL — actual config with API keys (gitignored)
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│     MCP Clients                                      │
│  ┌──────────┐  ┌───────────────┐  ┌──────────────┐  │
│  │  Cursor   │  │ Claude Desktop│  │  Claude Code  │  │
│  └─────┬────┘  └──────┬────────┘  └──────┬───────┘  │
└────────┼───────────────┼──────────────────┼──────────┘
         │               │                  │
         └───────────────┼──────────────────┘
                         │  MCP Protocol
┌────────────────────────▼────────────────────────────┐
│              MCP Server (src/contractos/mcp/)         │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │  server.py — FastMCP("ContractOS")               │ │
│  │  Transport: stdio (local) | http (remote)        │ │
│  └─────────────────────────────────────────────────┘ │
│                                                       │
│  ┌──────────┐   ┌───────────┐   ┌─────────────────┐ │
│  │ tools.py │   │resources.py│   │   prompts.py    │ │
│  │ 13 tools │   │10 resources│   │   5 prompts     │ │
│  └────┬─────┘   └─────┬─────┘   └───────┬─────────┘ │
│       │                │                 │            │
│  ┌────▼────────────────▼─────────────────▼─────────┐ │
│  │  context.py — Shared AppState                    │ │
│  │  TrustGraph │ EmbeddingIndex │ Config │ LLM      │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────┘
                       │ Direct Python calls
┌──────────────────────▼──────────────────────────────┐
│              Existing ContractOS Core                 │
│  fabric/  │  agents/  │  tools/  │  models/          │
└─────────────────────────────────────────────────────┘
```

## Tool Inventory (13 Tools)

| # | Tool | Intent | Input | Output |
|---|------|--------|-------|--------|
| 1 | `upload_contract` | Ingest a contract | file path or base64 | doc_id, fact_count, clause_count |
| 2 | `load_sample_contract` | Load built-in sample | filename | doc_id, metadata |
| 3 | `ask_question` | Q&A with provenance | question, doc_ids? | answer, provenance, confidence |
| 4 | `review_against_playbook` | Compliance review | doc_id | findings[], risk_profile, strategy |
| 5 | `triage_nda` | NDA screening | doc_id | checklist[], classification, summary |
| 6 | `discover_hidden_facts` | LLM fact discovery | doc_id | discovered_facts[], categories |
| 7 | `extract_obligations` | Obligation extraction | doc_id | obligations[], summary |
| 8 | `generate_risk_memo` | Risk assessment | doc_id | risk_memo, key_risks[], recommendations |
| 9 | `get_clause_gaps` | Gap analysis | doc_id | gaps_by_clause[] |
| 10 | `search_contracts` | Semantic search | query, top_k? | results[] with scores |
| 11 | `compare_clauses` | Cross-doc comparison | doc_id_1, doc_id_2, clause_type | comparison, differences |
| 12 | `generate_report` | HTML report | doc_id, report_type | HTML content |
| 13 | `clear_workspace` | Reset all data | — | confirmation |

## Resource Inventory (10 Resources)

| # | URI | Description |
|---|-----|-------------|
| 1 | `contractos://contracts` | List indexed contracts |
| 2 | `contractos://contracts/{id}` | Contract metadata |
| 3 | `contractos://contracts/{id}/facts` | Extracted facts |
| 4 | `contractos://contracts/{id}/clauses` | Classified clauses |
| 5 | `contractos://contracts/{id}/bindings` | Definitions + aliases |
| 6 | `contractos://contracts/{id}/graph` | TrustGraph view |
| 7 | `contractos://samples` | Available sample contracts |
| 8 | `contractos://chat/history` | Q&A history |
| 9 | `contractos://health` | Server health |
| 10 | `contractos://playbook` | Active playbook config |

## Prompt Inventory (5 Prompts)

| # | Prompt | Description | Params |
|---|--------|-------------|--------|
| 1 | `full_contract_analysis` | Complete pipeline: extract → triage → review → obligations → risk | doc_id |
| 2 | `due_diligence_checklist` | Structured due diligence | doc_id |
| 3 | `negotiation_prep` | Negotiation strategy from findings | doc_id |
| 4 | `risk_summary` | Executive risk summary | doc_id |
| 5 | `clause_comparison` | Compare clauses across contracts | doc_id_1, doc_id_2, clause_type |

## Server Strategy

ContractOS runs **two servers from the same codebase**, sharing a single `AppState`:

| Mode | What runs | Use case |
|------|-----------|----------|
| **MCP stdio** (default) | MCP server only, no FastAPI | Cursor / Claude Desktop local integration |
| **Container (Docker)** | FastAPI (port 8742) + MCP HTTP (port 8743) in **one container** | VDI / remote deployment |

**Single-container strategy:** Both servers run in the same container via `entrypoint.sh` to share a single SQLite connection (SQLite doesn't support concurrent writers across processes). FastAPI is the main process; MCP HTTP starts as a background process. Both import the same `AppState` singleton.

**Container engine agnostic:** All deployment docs use OCI-standard commands. Works with Docker Desktop, Rancher Desktop (`nerdctl`), Podman, or any OCI-compliant runtime. The `docker-compose.yml` / `compose.yaml` format is supported by all engines.

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Separate `mcp/` package (not inline in `api/`) | Clean separation of concerns; MCP and FastAPI are independent interaction layers |
| `MCPContext` wraps `AppState` (composition) | Reuses existing singleton; no duplication of TrustGraph/EmbeddingIndex/LLM |
| All LLM calls via `AppState.llm` provider | Constitution §6: Configuration Over Code — provider-agnostic |
| stdio as default transport | Lowest latency for local Cursor/Claude Desktop use |
| Single container for Docker | SQLite single-writer constraint; shared `AppState` singleton |
| 13 tools (not 25+) | Grouped by user intent, not raw API surface; within MCP best practices |
| `.cursor/mcp.json.example` checked in, `.cursor/mcp.json` gitignored | API keys never committed |
