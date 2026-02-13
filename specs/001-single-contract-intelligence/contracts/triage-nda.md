# API Contract: NDA Triage

## Endpoint

```
POST /contracts/{document_id}/triage
```

## Description

Rapid triage of an uploaded NDA against a 10-point screening checklist. Classifies the NDA as GREEN (standard approval), YELLOW (counsel review needed), or RED (significant issues). Returns per-item checklist results with evidence and routing recommendations.

## Request

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | string | Yes | ID of the uploaded NDA |

### Request Body

```json
{
  "checklist": "default",
  "context": "Incoming NDA from new vendor for SaaS evaluation"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `checklist` | string | No | `"default"` | Checklist name or path |
| `context` | string | No | `""` | Business context for the NDA |

## Response

### Success (200 OK)

```json
{
  "document_id": "doc-nda-456",
  "classification": {
    "level": "yellow",
    "routing": "Send to designated reviewer with specific issues flagged",
    "timeline": "1-2 business days",
    "rationale": "NDA is generally standard but has a broad residuals clause and missing independent development carveout that need counsel review."
  },
  "checklist_results": [
    {
      "item_id": "agreement_structure",
      "name": "Agreement Structure",
      "status": "pass",
      "finding": "Mutual NDA identified. Standalone agreement.",
      "evidence": "MUTUAL NON-DISCLOSURE AGREEMENT between...",
      "fact_ids": ["fact-101"]
    },
    {
      "item_id": "standard_carveouts",
      "name": "Standard Carveouts",
      "status": "fail",
      "finding": "Missing independent development carveout. 4 of 5 standard carveouts present.",
      "evidence": "Section 3 defines exclusions: (a) publicly available, (b) prior possession, (c) third-party receipt, (d) legal compulsion. No independent development carveout found.",
      "fact_ids": ["fact-115", "fact-116", "fact-117", "fact-118"]
    },
    {
      "item_id": "problematic_provisions",
      "name": "Problematic Provisions",
      "status": "review",
      "finding": "Residuals clause present in Section 7. Scope appears narrow (unaided memory) but needs counsel verification.",
      "evidence": "Section 7: 'Nothing herein shall prevent either party from using ideas, concepts, or know-how retained in the unaided memory of its personnel...'",
      "fact_ids": ["fact-130"]
    }
  ],
  "key_issues": [
    "Missing independent development carveout (Section 3)",
    "Residuals clause present — needs scope verification (Section 7)"
  ],
  "summary": "This mutual NDA is generally standard but requires counsel review for two issues: (1) missing independent development carveout, which could create claims against internally-developed products, and (2) a residuals clause that appears narrowly scoped but should be verified.",
  "pass_count": 7,
  "fail_count": 1,
  "review_count": 2,
  "triage_time_ms": 5230,
  "confidence": {
    "score": 0.78,
    "label": "high",
    "color": "#22c55e"
  }
}
```

### Error Responses

| Status | Condition | Body |
|--------|-----------|------|
| 404 | Contract not found | `{ "detail": "Contract doc-nda-456 not found" }` |
| 400 | Not an NDA | `{ "detail": "Document does not appear to be an NDA. Triage is designed for NDAs." }` |
| 500 | LLM failure | `{ "detail": "Triage failed: LLM service unavailable" }` |

## Behavior

1. Load NDA checklist configuration (default or specified)
2. Retrieve extracted facts, clauses, and bindings from TrustGraph
3. For each checklist item:
   a. Run automated checks (pattern matching, fact queries) where `automation != "llm_only"`
   b. Run LLM verification where `automation != "auto"`
   c. Classify as PASS / FAIL / REVIEW / N/A
4. Aggregate results:
   - All PASS → GREEN
   - Any FAIL but no critical failures → YELLOW
   - Critical failures (missing carveouts, non-compete, non-solicitation, etc.) → RED
5. Generate routing recommendation and timeline
6. Return complete TriageResult

## Checklist Items (Default)

| # | Item | Automation |
|---|------|-----------|
| 1 | Agreement Structure | hybrid |
| 2 | Definition of Confidential Information | hybrid |
| 3 | Obligations of Receiving Party | hybrid |
| 4 | Standard Carveouts | hybrid |
| 5 | Permitted Disclosures | hybrid |
| 6 | Term and Duration | auto |
| 7 | Return and Destruction | hybrid |
| 8 | Remedies | llm_only |
| 9 | Problematic Provisions | llm_only |
| 10 | Governing Law and Jurisdiction | auto |
