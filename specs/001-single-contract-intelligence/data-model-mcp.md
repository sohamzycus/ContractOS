# Data Model: Phase 13 — ContractOS MCP Server

**Date**: 2026-02-09

## Overview

The MCP server introduces no new persistent entities. It is a protocol adapter that exposes existing ContractOS models through MCP primitives. This document defines the **MCP-specific response shapes** that wrap existing models for MCP tool/resource outputs.

---

## MCP Tool Response Models

### UploadResult

Returned by `upload_contract` and `load_sample_contract`.

```python
class UploadResult(BaseModel):
    document_id: str
    filename: str
    page_count: int
    fact_count: int
    clause_count: int
    binding_count: int
    extraction_time_ms: int
    message: str
```

### QuestionResult

Returned by `ask_question`.

```python
class QuestionResult(BaseModel):
    answer: str
    confidence: float          # 0.0–1.0
    confidence_label: str      # "High", "Medium", "Low"
    provenance: list[ProvenanceNode]
    sources: list[str]         # document IDs referenced
    follow_up_suggestions: list[str]
```

### ReviewResult (existing)

Returned by `review_against_playbook`. Reuses `models.review.ReviewResult`:
- `findings: list[ReviewFinding]` — each with severity (GREEN/YELLOW/RED), clause, explanation, redline suggestion
- `risk_profile: RiskProfile`
- `negotiation_strategy: str`

### TriageResult (existing)

Returned by `triage_nda`. Reuses `models.triage.TriageResult`:
- `checklist: list[ChecklistResult]` — 10 items, each PASS/FAIL/PARTIAL
- `classification: TriageClassification` — GREEN/YELLOW/RED
- `summary: str`

### DiscoveryResult (existing)

Returned by `discover_hidden_facts`. Reuses `tools.fact_discovery.DiscoveryResult`:
- `discovered_facts: list[DiscoveredFact]`
- `summary: str`
- `categories_found: str`

### ObligationResult

Returned by `extract_obligations`.

```python
class ObligationItem(BaseModel):
    obligation: str
    type: str                  # "affirmative", "negative", "conditional"
    party: str
    clause_reference: str
    risk_level: str            # "low", "medium", "high"

class ObligationResult(BaseModel):
    obligations: list[ObligationItem]
    summary: str
    total_affirmative: int
    total_negative: int
    total_conditional: int
```

### RiskMemoResult

Returned by `generate_risk_memo`.

```python
class RiskItem(BaseModel):
    risk: str
    severity: str              # "low", "medium", "high", "critical"
    clause_reference: str
    mitigation: str

class RiskMemoResult(BaseModel):
    executive_summary: str
    overall_risk_rating: str
    key_risks: list[RiskItem]
    missing_protections: list[str]
    recommendations: list[str]
    escalation_items: list[str]
```

### ClauseGapResult

Returned by `get_clause_gaps`.

```python
class ClauseGap(BaseModel):
    clause_type: str
    clause_heading: str
    missing_facts: list[str]
    present_facts: list[str]

class ClauseGapResult(BaseModel):
    gaps: list[ClauseGap]
    total_gaps: int
    total_clauses: int
```

### SearchResult

Returned by `search_contracts`.

```python
class SearchHit(BaseModel):
    document_id: str
    chunk_text: str
    score: float
    clause_type: str | None
    section: str | None

class SearchResult(BaseModel):
    query: str
    results: list[SearchHit]
    total_documents_searched: int
```

### ComparisonResult

Returned by `compare_clauses`.

```python
class ClauseDifference(BaseModel):
    aspect: str
    contract_1: str
    contract_2: str
    significance: str          # "minor", "moderate", "major"

class ComparisonResult(BaseModel):
    clause_type: str
    contract_1_id: str
    contract_2_id: str
    differences: list[ClauseDifference]
    summary: str
    recommendation: str
```

### ReportResult

Returned by `generate_report`.

```python
class ReportResult(BaseModel):
    html_content: str
    report_type: str           # "review", "triage", "discovery"
    document_id: str
    generated_at: str          # ISO 8601
```

---

## MCP Resource Response Models

Resources return JSON-serialized versions of existing models:

| Resource | Response Model |
|----------|---------------|
| `contractos://contracts` | `list[Contract]` (from `models.document`) |
| `contractos://contracts/{id}` | `Contract` |
| `contractos://contracts/{id}/facts` | `list[Fact]` (from `models.fact`) |
| `contractos://contracts/{id}/clauses` | `list[Clause]` (from `models.clause`) |
| `contractos://contracts/{id}/bindings` | `list[Binding]` (from `models.binding`) |
| `contractos://contracts/{id}/graph` | `dict` with `nodes` and `edges` |
| `contractos://samples` | `list[dict]` from `manifest.json` |
| `contractos://chat/history` | `list[dict]` with sessions |
| `contractos://health` | `dict` with status, version, config |
| `contractos://playbook` | `PlaybookConfig` (from `models.playbook`) |

---

## Entity Relationship (MCP Layer)

```
MCP Client
    │
    ├── calls Tool ──► returns Pydantic model (serialized to JSON)
    │                    │
    │                    └── wraps existing: ReviewResult, TriageResult,
    │                        DiscoveryResult, QueryResult, etc.
    │
    ├── reads Resource ──► returns JSON (existing models serialized)
    │
    └── invokes Prompt ──► returns Message[] (orchestrates multiple tools)
```

No new database tables. No schema migrations. The MCP layer is purely a protocol adapter.
