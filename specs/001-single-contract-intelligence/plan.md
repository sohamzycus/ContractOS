# Implementation Plan: Phase 9 — Playbook Intelligence & Risk Framework

**Branch**: `001-single-contract-intelligence` | **Date**: 2026-02-09 | **Spec**: [spec.md](spec.md)
**Input**: Competitive analysis of [Anthropic's Legal Productivity Plugin](https://github.com/anthropics/knowledge-work-plugins/tree/main/legal) + existing ContractOS architecture (Phases 1–8d complete, 666 tests passing).

## Summary

Phase 9 introduces **playbook-based contract review**, **risk assessment**, **NDA triage**, and **redline generation** — domain workflows identified in Anthropic's legal plugin, re-implemented as grounded agents built on ContractOS's existing extraction pipeline, TrustGraph, and FAISS semantic search. Where Anthropic relies on a single LLM pass with no verification, ContractOS grounds every assessment in deterministic extraction with full provenance.

**Key deliverables**:
1. `ComplianceAgent` — compares extracted clauses against a configurable playbook, producing GREEN/YELLOW/RED severity per clause
2. `DraftAgent` — generates specific redline language for deviations
3. `NDATriageAgent` — automated 10-point NDA screening with routing
4. Risk scoring framework — 5×5 Severity × Likelihood matrix
5. New API endpoints: `/contracts/{id}/review`, `/contracts/{id}/triage`
6. Copilot UI: playbook review results with color-coded clauses and risk matrix

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, Pydantic v2, anthropic SDK, sentence-transformers, faiss-cpu, PyMuPDF, python-docx
**Storage**: SQLite with WAL mode (TrustGraph, WorkspaceStore)
**Testing**: pytest, pytest-asyncio, httpx (AsyncClient), respx — TDD mandatory
**Target Platform**: Docker Compose on any VDI, macOS/Linux dev
**Project Type**: Single project (src/contractos/ + tests/ + demo/)
**Performance Goals**: Playbook review < 15s per contract, NDA triage < 10s, redline generation < 5s per clause
**Constraints**: Must work with existing SQLite storage, must not break existing 666 tests
**Scale/Scope**: Single-contract review initially, multi-contract comparison in Phase 10

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Evidence Before Intelligence | PASS | Every GREEN/YELLOW/RED classification is backed by extracted facts with char offsets and provenance chains |
| Truth Model Integrity | PASS | Playbook deviations are typed as Opinions (role-dependent, policy-dependent). Risk scores are Inferences (derived from facts + playbook). Extracted clause text remains Facts. |
| Inference Over Extraction | PASS | ComplianceAgent reasons about what clauses mean relative to organizational policy, not just what they say |
| Auditability By Design | PASS | Every review finding includes: the clause text, the playbook position, the deviation, and the provenance chain |
| Repository-Level Reasoning | PASS (deferred) | Phase 9 is single-contract. Phase 10 adds cross-contract playbook comparison |
| Configuration Over Code | PASS | Playbook is a YAML config file, not hardcoded. Clause positions, ranges, and triggers are user-defined |
| Context Is Persistent | PASS | Review results stored in TrustGraph as ReasoningSessions. Prior reviews retrievable |
| Test-Driven Development | PASS | All features TDD: unit tests for agents/models, integration tests for endpoints, contract tests for API schemas |

## Project Structure

### Documentation (this feature)

```text
specs/001-single-contract-intelligence/
├── plan.md                 # This file
├── research.md             # Phase 0: Anthropic plugin analysis + design decisions
├── data-model.md           # Phase 1: New entities (PlaybookPosition, ReviewFinding, RiskScore)
├── quickstart.md           # Phase 1: Integration scenarios
├── contracts/              # Phase 1: API specifications for new endpoints
│   ├── review-contract.md
│   └── triage-nda.md
└── tasks.md                # Phase 2: Task breakdown (to be updated)
```

### Source Code (new/modified files)

```text
src/contractos/
├── agents/
│   ├── document_agent.py       # Existing — no changes
│   ├── compliance_agent.py     # NEW — playbook-based clause review
│   ├── draft_agent.py          # NEW — redline generation
│   └── nda_triage_agent.py     # NEW — NDA screening
├── models/
│   ├── playbook.py             # NEW — PlaybookPosition, PlaybookConfig
│   ├── review.py               # NEW — ReviewFinding, ReviewResult, Severity
│   └── risk.py                 # NEW — RiskScore, RiskLevel, RiskMatrix
├── tools/
│   └── playbook_loader.py      # NEW — YAML playbook parser + validator
├── api/routes/
│   └── contracts.py            # MODIFIED — add /review and /triage endpoints

config/
├── default_playbook.yaml       # NEW — default playbook with standard commercial positions
└── nda_checklist.yaml          # NEW — NDA triage checklist configuration

demo/
└── copilot.html                # MODIFIED — review results UI, risk matrix

tests/
├── unit/
│   ├── test_compliance_agent.py    # NEW
│   ├── test_draft_agent.py         # NEW
│   ├── test_nda_triage_agent.py    # NEW
│   ├── test_playbook_models.py     # NEW
│   ├── test_risk_models.py         # NEW
│   └── test_playbook_loader.py     # NEW
└── integration/
    ├── test_review_endpoint.py     # NEW
    └── test_triage_endpoint.py     # NEW
```

## Complexity Tracking

No constitution violations. All new features align with existing principles.
