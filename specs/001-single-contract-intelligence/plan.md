# Implementation Plan: Single-Contract Intelligence

**Branch**: `001-single-contract-intelligence` | **Date**: 2025-02-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-single-contract-intelligence/spec.md`

## Summary

Build the foundational phase of ContractOS: a local service that parses Word
and PDF procurement contracts, extracts structured facts, resolves defined-term
bindings, answers natural language questions via LLM, and returns every answer
with a full provenance chain. Deployed as a local Python service with a Word
Copilot as the primary interaction surface, using SQLite for the TrustGraph and
Claude as the default LLM.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: python-docx (Word parsing), PyMuPDF/pdfplumber (PDF
parsing), Anthropic SDK (Claude API), SQLite3 (built-in), Pydantic (data
models), FastAPI (local API server), spaCy (NER), pytest (testing)
**Storage**: SQLite (TrustGraph — facts, bindings, inferences; Workspace state;
session history)
**Testing**: pytest with custom fixtures for contract parsing; COBench v0.1 for
accuracy benchmarks
**Target Platform**: macOS / Linux local deployment; Word Copilot via Office
Add-in (TypeScript/React sidebar)
**Project Type**: Single project — Python backend + Office Add-in frontend
**Performance Goals**: < 5 seconds Q&A on cached documents; < 30 seconds first
parse for a 30-page document; > 93% fact extraction precision
**Constraints**: Must run locally; LLM API calls are the only external
dependency; document contents never leave the local machine except as
excerpts to LLM; configurable LLM provider
**Scale/Scope**: 1 document at a time (Phase 1); workspace supports multiple
indexed documents; target 100–500 documents per workspace

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Evidence Before Intelligence | PASS | Every tool output includes source evidence; provenance chains mandatory |
| Truth Model Integrity | PASS | Schema enforces Fact/Binding/Inference/Opinion typing; Pydantic models |
| Inference Over Extraction | PASS | InferenceEngine combines facts+bindings+LLM to derive claims |
| Auditability By Design | PASS | ProvenanceChain is a first-class data structure; every answer includes one |
| Repository-Level Reasoning | N/A | Phase 1 is single-document; architecture supports future expansion |
| Configuration Over Code | PASS | LLM provider, extraction pipeline via YAML config |
| Context Is Persistent | PASS | SQLite workspace persists across restarts |

| Constraint | Status | Notes |
|------------|--------|-------|
| Layered architecture | PASS | Interaction → Workspace → Agent → Tool → Fabric → Data |
| Agents are stateless | PASS | DocumentAgent receives context per query |
| Tools enforce truth model | PASS | Every tool returns typed results (FactResult, etc.) |
| Interaction Layer never reasons | PASS | Word Copilot is display-only; reasoning in Agent layer |
| External knowledge declared | N/A | DomainBridge not in Phase 1 |
| Scale deferred not ignored | PASS | SQLite now; schema supports PostgreSQL migration |

## Project Structure

### Documentation (this feature)

```text
specs/001-single-contract-intelligence/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: Technology decisions
├── data-model.md        # Phase 1: Entity schemas
├── quickstart.md        # Phase 1: Getting started guide
├── contracts/           # Phase 1: API specifications
│   ├── api-server.md    # FastAPI endpoints
│   └── copilot-api.md   # Office Add-in communication
├── checklists/
│   └── requirements.md  # Requirements tracking
└── tasks.md             # Phase 2: Task breakdown
```

### Source Code (repository root)

```text
src/
├── contractos/
│   ├── __init__.py
│   ├── config.py              # Configuration loading (YAML)
│   ├── models/                # Pydantic data models
│   │   ├── __init__.py
│   │   ├── fact.py            # Fact, FactResult
│   │   ├── binding.py         # Binding, BindingResult
│   │   ├── inference.py       # Inference, InferenceResult
│   │   ├── opinion.py         # Opinion, OpinionResult
│   │   ├── document.py        # Contract document metadata
│   │   ├── provenance.py      # ProvenanceChain, ProvenanceNode
│   │   ├── workspace.py       # Workspace, ReasoningSession
│   │   └── query.py           # Query, QueryResult
│   ├── tools/                 # Tooling layer (deterministic operations)
│   │   ├── __init__.py
│   │   ├── fact_extractor.py  # Document parsing + fact extraction
│   │   ├── docx_parser.py     # Word-specific parsing
│   │   ├── pdf_parser.py      # PDF-specific parsing
│   │   ├── binding_resolver.py # Definition resolution
│   │   ├── inference_engine.py # LLM-assisted inference
│   │   └── confidence.py      # Confidence calculation
│   ├── agents/                # Agent orchestration layer
│   │   ├── __init__.py
│   │   └── document_agent.py  # Single-contract reasoning
│   ├── fabric/                # Intelligence fabric
│   │   ├── __init__.py
│   │   ├── trust_graph.py     # TrustGraph (SQLite backend)
│   │   └── schema.sql         # Database schema
│   ├── workspace/             # Workspace management
│   │   ├── __init__.py
│   │   ├── manager.py         # WorkspaceManager
│   │   └── session.py         # ReasoningSession lifecycle
│   ├── api/                   # FastAPI server
│   │   ├── __init__.py
│   │   ├── server.py          # Main FastAPI application
│   │   ├── routes/
│   │   │   ├── documents.py   # Document upload/status
│   │   │   ├── query.py       # Q&A endpoints
│   │   │   └── workspace.py   # Workspace management
│   │   └── middleware/
│   │       └── provenance.py  # Ensures all responses have provenance
│   └── llm/                   # LLM abstraction
│       ├── __init__.py
│       ├── provider.py        # Base LLM provider interface
│       └── claude.py          # Claude implementation
├── config/
│   └── default.yaml           # Default configuration
├── copilot/                   # Word Add-in (TypeScript/React)
│   ├── package.json
│   ├── src/
│   │   ├── taskpane/          # Sidebar UI
│   │   ├── services/          # API client
│   │   └── components/        # Provenance display, Q&A
│   └── manifest.xml           # Office Add-in manifest
tests/
├── conftest.py                # Shared fixtures
├── fixtures/                  # Test contracts (anonymized)
│   ├── simple-procurement.docx
│   ├── complex-it-services.docx
│   └── simple-nda.pdf
├── unit/
│   ├── test_fact_extractor.py
│   ├── test_binding_resolver.py
│   ├── test_inference_engine.py
│   └── test_trust_graph.py
├── integration/
│   └── test_document_agent.py
└── benchmark/
    ├── cobench_v01.py         # COBench runner
    └── annotations/           # Ground truth annotations
```

**Structure Decision**: Single Python project with a colocated TypeScript
Office Add-in under `copilot/`. The Python backend runs as a local FastAPI
service that the Word Add-in communicates with over localhost.

## Complexity Tracking

No constitution violations identified. No complexity justifications needed.
