# API Contract: Review Contract Against Playbook

## Endpoint

```
POST /contracts/{document_id}/review
```

## Description

Review a previously uploaded contract against the organization's negotiation playbook. Compares each extracted clause against configured standard positions, acceptable ranges, and escalation triggers. Returns clause-by-clause GREEN/YELLOW/RED severity classification with risk scores, deviation descriptions, and redline suggestions.

Requires the contract to be already uploaded and extracted (facts, clauses, bindings in TrustGraph).

## Request

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | string | Yes | ID of the uploaded contract |

### Request Body

```json
{
  "playbook": "default",
  "user_side": "customer",
  "focus_areas": ["data_protection", "liability"],
  "generate_redlines": true
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `playbook` | string | No | `"default"` | Playbook name or path |
| `user_side` | string | No | `null` | Which side: "customer", "vendor", "licensor", "licensee" |
| `focus_areas` | list[string] | No | `[]` | Clause types to prioritize |
| `generate_redlines` | bool | No | `true` | Whether to generate redline suggestions for YELLOW/RED |

## Response

### Success (200 OK)

```json
{
  "document_id": "doc-abc123",
  "playbook_name": "Standard Commercial Playbook",
  "summary": "Contract review identified 3 RED issues, 5 YELLOW deviations, and 8 GREEN clauses. Key concerns: uncapped indemnification (RED), missing data protection clause (RED), liability cap below standard (YELLOW).",
  "green_count": 8,
  "yellow_count": 5,
  "red_count": 3,
  "missing_clauses": ["data_protection", "force_majeure"],
  "findings": [
    {
      "finding_id": "rf-001",
      "clause_id": "cls-12",
      "clause_type": "indemnification",
      "clause_heading": "12. Indemnification",
      "severity": "red",
      "current_language": "Buyer shall indemnify and hold harmless Vendor against any and all claims, damages, losses...",
      "playbook_position": "Mutual indemnification for IP infringement and data breach",
      "deviation_description": "Unilateral indemnification — only the Buyer indemnifies the Vendor. No mutual obligation.",
      "business_impact": "Buyer bears all indemnification risk with no reciprocal protection. Estimated exposure: uncapped.",
      "risk_score": {
        "severity": 5,
        "likelihood": 4,
        "score": 20,
        "level": "critical",
        "severity_rationale": "Uncapped unilateral indemnification creates unlimited financial exposure",
        "likelihood_rationale": "IP and data breach claims are common in technology contracts"
      },
      "redline": {
        "proposed_language": "Each Party shall indemnify, defend, and hold harmless the other Party from and against any third-party claims arising from (a) infringement of intellectual property rights, or (b) breach of data protection obligations under this Agreement, subject to the limitation of liability in Section [X].",
        "rationale": "Mutual indemnification is market standard for technology agreements and ensures balanced risk allocation.",
        "priority": "tier_1",
        "fallback_language": "Buyer's indemnification obligations shall be subject to the limitation of liability cap in Section [X] and limited to third-party claims only."
      },
      "provenance_facts": ["fact-234", "fact-235", "fact-236"],
      "char_start": 4521,
      "char_end": 4892
    }
  ],
  "risk_profile": {
    "overall_level": "high",
    "overall_score": 12.5,
    "highest_risk_finding": "rf-001",
    "risk_distribution": { "low": 8, "medium": 3, "high": 2, "critical": 1 },
    "tier_1_issues": 3,
    "tier_2_issues": 4,
    "tier_3_issues": 1
  },
  "negotiation_strategy": "Lead with the 3 Tier 1 issues (uncapped indemnification, missing DPA, liability cap). Concede on Tier 3 items (governing law preference, notice period) to secure Tier 2 wins (termination flexibility, audit rights).",
  "review_time_ms": 8432,
  "confidence": {
    "score": 0.82,
    "label": "high",
    "color": "#22c55e"
  }
}
```

### Error Responses

| Status | Condition | Body |
|--------|-----------|------|
| 404 | Contract not found | `{ "detail": "Contract doc-abc123 not found" }` |
| 400 | Contract not yet extracted | `{ "detail": "Contract has no extracted clauses. Upload and extract first." }` |
| 422 | Invalid playbook | `{ "detail": "Playbook 'custom.yaml' not found or invalid" }` |
| 500 | LLM failure | `{ "detail": "Review failed: LLM service unavailable" }` |

## Behavior

1. Load playbook configuration (default or specified)
2. Retrieve all extracted clauses from TrustGraph for the document
3. For each playbook position:
   a. Find matching clause(s) in the document by clause type
   b. If no matching clause and position is required → RED (missing clause)
   c. If matching clause found → send to LLM for comparison against playbook
   d. Check escalation triggers (deterministic pattern match)
   e. Classify as GREEN/YELLOW/RED
   f. If YELLOW/RED and `generate_redlines=true` → generate redline via DraftAgent
4. Calculate aggregate risk profile
5. Generate negotiation strategy summary
6. Return complete ReviewResult

## Notes

- Review results are stored as a ReasoningSession in the WorkspaceStore
- The `current_language` field always contains exact text from TrustGraph (never LLM-generated)
- Escalation triggers are checked deterministically — they override LLM classification upward (never downward)
- The endpoint requires an active LLM provider (not mock) for classification and redline generation
