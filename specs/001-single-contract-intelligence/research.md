# Research: Phase 9 — Playbook Intelligence & Risk Framework

**Phase 0 Output** — Resolves all design decisions before implementation.

---

## R1: Playbook Schema Design

### Question
What schema should `playbook.yaml` use to define organizational positions, acceptable ranges, and escalation triggers per clause type?

### Research

Anthropic's legal plugin uses a free-form markdown file (`legal.local.md`) with nested sections per clause type. Each section defines:
- **Standard position**: The organization's preferred terms
- **Acceptable range**: What can be agreed without escalation
- **Escalation trigger**: Terms requiring senior review

This is human-readable but not machine-parseable. ContractOS needs a **structured YAML schema** that can be validated with Pydantic and compared programmatically against extracted clauses.

### Decision

Use a typed YAML schema with Pydantic validation:

```yaml
# config/default_playbook.yaml
playbook:
  name: "Standard Commercial Playbook"
  version: "1.0"
  positions:
    limitation_of_liability:
      clause_type: "limitation_of_liability"
      standard_position: "Mutual cap at 12 months of fees paid/payable"
      acceptable_range:
        min: "6 months of fees"
        max: "24 months of fees"
      escalation_triggers:
        - "Uncapped liability"
        - "No consequential damages exclusion"
        - "Asymmetric carveouts"
      review_guidance: "Check for mutual vs. unilateral, carveouts, consequential damages exclusion"
      priority: "tier_1"  # must-have | should-have | nice-to-have

    indemnification:
      clause_type: "indemnification"
      standard_position: "Mutual indemnification for IP infringement and data breach"
      acceptable_range:
        min: "Indemnification limited to third-party claims"
        max: "Mutual indemnification for all material breaches"
      escalation_triggers:
        - "Unilateral indemnification obligations"
        - "Uncapped indemnification"
        - "Indemnification for 'any breach'"
      priority: "tier_1"

    # ... more clause types
```

### Rationale
- YAML is human-editable and version-controllable
- Pydantic validation catches schema errors at load time
- `clause_type` maps directly to our existing `ClauseTypeEnum`
- `priority` enables negotiation strategy (Tier 1/2/3)
- `escalation_triggers` are string patterns that the LLM can match against extracted clause text

---

## R2: GREEN/YELLOW/RED Classification Logic

### Question
How should the ComplianceAgent determine severity? Pure LLM judgment, rule-based, or hybrid?

### Research

Anthropic's plugin uses pure LLM judgment — the system prompt describes what GREEN/YELLOW/RED mean and the LLM classifies. This is fast but non-deterministic and non-auditable.

### Decision

**Hybrid approach**:

1. **Rule-based pre-classification** (deterministic):
   - Clause type present in contract AND matches playbook → candidate for review
   - Clause type missing from contract but required by playbook → automatic RED (missing clause)
   - Clause type present but not in playbook → skip (no position defined)

2. **LLM-assisted classification** (grounded):
   - For each candidate clause, send to LLM with:
     - Extracted clause text (from TrustGraph, with char offsets)
     - Playbook position (standard, acceptable range, escalation triggers)
     - Extracted facts within the clause (monetary values, durations, parties)
   - LLM returns: severity (GREEN/YELLOW/RED), deviation description, confidence
   - Every classification includes provenance back to the extracted clause text

3. **Escalation trigger matching** (deterministic override):
   - If any escalation trigger pattern matches the clause text → force RED regardless of LLM classification
   - This ensures critical issues are never missed

### Rationale
- Deterministic rules catch structural issues (missing clauses, missing facts)
- LLM handles nuanced judgment (is this indemnification scope reasonable?)
- Escalation triggers provide a safety net against LLM under-classification
- Full provenance chain for every classification

---

## R3: Risk Scoring Framework

### Question
How should the 5×5 Severity × Likelihood matrix integrate with existing confidence scoring?

### Research

Anthropic's plugin defines a 5×5 matrix (Severity 1-5 × Likelihood 1-5 = Risk Score 1-25) with four risk levels:
- GREEN (1-4), YELLOW (5-9), ORANGE (10-15), RED (16-25)

ContractOS currently has `confidence_label()` returning `ConfidenceDisplay` with score (0.0-1.0) and label (high/medium/low).

### Decision

Extend the existing confidence system with a parallel risk scoring system:

```python
class RiskScore(BaseModel):
    severity: int = Field(ge=1, le=5)        # Impact if risk materializes
    likelihood: int = Field(ge=1, le=5)      # Probability of materialization
    score: int                                # severity × likelihood (1-25)
    level: RiskLevel                          # GREEN/YELLOW/ORANGE/RED
    severity_rationale: str                   # Why this severity
    likelihood_rationale: str                 # Why this likelihood
```

- **Severity** is derived from the playbook priority tier and deviation magnitude
- **Likelihood** is derived from the clause specificity and market norms
- Both are LLM-assessed but grounded in extracted facts
- Risk scores are typed as **Inferences** (derived from facts + playbook)

### Rationale
- Keeps existing confidence system for Q&A answers
- Adds risk scoring specifically for playbook review findings
- Risk scores are Inferences (not Opinions) because they're grounded in extracted facts + playbook positions
- 4-level system (GREEN/YELLOW/ORANGE/RED) matches Anthropic's framework and is intuitive for legal teams

---

## R4: NDA Triage Checklist Design

### Question
How should the NDA triage checklist be structured, and how much can be automated vs. requiring LLM?

### Research

Anthropic's plugin defines 10 screening sections with specific criteria. Many of these map to our existing extraction capabilities:

| Checklist Item | Can We Automate? | How? |
|---------------|-----------------|------|
| Agreement structure (mutual/unilateral) | Partial | Clause classifier + LLM |
| Definition scope | Yes | Binding resolver (count and scope of definitions) |
| Standard carveouts | Partial | Pattern matching for known carveout phrases |
| Permitted disclosures | Partial | Clause text search |
| Term and duration | Yes | Fact extractor (duration patterns) |
| Return/destruction | Partial | Clause classifier |
| Remedies | LLM | Nuanced legal judgment |
| Problematic provisions | LLM | Non-solicitation, non-compete detection |
| Governing law | Yes | Fact extractor (jurisdiction patterns) |
| Overall classification | LLM | Aggregate judgment |

### Decision

Use a YAML-configurable checklist with mixed automation:

```yaml
# config/nda_checklist.yaml
checklist:
  - id: "agreement_structure"
    name: "Agreement Structure"
    automation: "hybrid"  # auto | hybrid | llm_only
    auto_checks:
      - "mutual_nda_detected"  # from clause classifier
      - "standalone_agreement"  # not embedded in larger contract
    llm_prompt: "Is this NDA type appropriate for the business relationship?"

  - id: "standard_carveouts"
    name: "Standard Carveouts"
    automation: "hybrid"
    required_carveouts:
      - "public_knowledge"
      - "prior_possession"
      - "independent_development"
      - "third_party_receipt"
      - "legal_compulsion"
    auto_checks:
      - pattern: "publicly available|public knowledge|publicly known"
        carveout: "public_knowledge"
      # ... more patterns
```

### Rationale
- Maximizes deterministic automation (faster, reproducible)
- LLM fills gaps where pattern matching is insufficient
- YAML config allows organizations to customize the checklist
- Tested against our 50 real NDAs from ContractNLI

---

## R5: Redline Generation Approach

### Question
How should the DraftAgent generate redline suggestions?

### Decision

The DraftAgent receives a `ReviewFinding` (YELLOW or RED) and generates:

```python
class RedlineSuggestion(BaseModel):
    clause_id: str
    current_language: str          # Exact text from TrustGraph
    proposed_language: str         # LLM-generated alternative
    rationale: str                 # Suitable for sharing with counterparty
    priority: str                  # "must_have" | "should_have" | "nice_to_have"
    fallback_language: str | None  # Alternative if primary is rejected
```

**LLM prompt structure**:
1. System prompt: "You are a contract drafting assistant..."
2. Context: current clause text, playbook position, deviation type, contract type, user's side
3. Instruction: "Generate specific alternative language that brings this clause to the standard position"

**Grounding**: The `current_language` is always the exact extracted text from TrustGraph (with char offsets). The LLM only generates the proposed alternative — it cannot misquote the original.

---

## R6: API Design for Review Endpoints

### Question
What should the new API endpoints look like?

### Decision

Two new endpoints on the existing `/contracts` router:

```
POST /contracts/{document_id}/review
  Body: { "playbook_path": "config/default_playbook.yaml" }  (optional, uses default)
  Response: ReviewResult (findings[], summary, risk_profile, negotiation_strategy)

POST /contracts/{document_id}/triage
  Body: { "checklist_path": "config/nda_checklist.yaml" }  (optional, uses default)
  Response: TriageResult (classification, checklist_results[], routing, summary)
```

Both follow the existing pattern of `POST /contracts/{document_id}/discover`.

---

## R7: Copilot UI Integration

### Question
How should playbook review results be displayed in the Copilot?

### Decision

Add a new quick-action button "Review Against Playbook" alongside the existing "Discover Hidden Facts". Results display as:

1. **Summary bar**: Overall risk profile (e.g., "3 RED, 5 YELLOW, 8 GREEN")
2. **Clause-by-clause cards**: Each finding as a card with:
   - Color-coded severity badge (GREEN/YELLOW/RED)
   - Clause heading and section reference
   - Deviation description
   - Clickable to highlight source text in document
   - Expandable redline suggestion (for YELLOW/RED)
3. **Risk matrix**: Small 5×5 grid visualization showing where findings cluster
4. **Negotiation strategy**: Tier 1/2/3 priority list

For NDA triage, a simpler view:
1. **Classification badge**: GREEN/YELLOW/RED with routing recommendation
2. **Checklist**: 10-item checklist with pass/fail/review status per item
3. **Key issues**: Specific findings for YELLOW/RED items
