# Data Model: Phase 9 — Playbook Intelligence & Risk Framework

**Addendum to Phase 1 data model** — New entities for playbook review, risk scoring, NDA triage, and redline generation.

---

## Entity Relationship Overview (Phase 9 Additions)

```
Contract ──── 1:N ──── ReviewResult
                          │
                          ├── 1:N ── ReviewFinding
                          │             │
                          │             ├── M:1 ── Clause (reviewed clause)
                          │             ├── 1:1 ── PlaybookPosition (compared against)
                          │             ├── 1:1 ── RiskScore
                          │             └── 0:1 ── RedlineSuggestion
                          │
                          └── 1:1 ── RiskProfile (aggregate)

Contract ──── 0:1 ──── TriageResult
                          │
                          ├── 1:N ── ChecklistResult
                          │             │
                          │             └── 1:1 ── ChecklistItem (from config)
                          │
                          └── 1:1 ── TriageClassification

PlaybookConfig ── 1:N ── PlaybookPosition
                            │
                            └── M:1 ── ClauseTypeEnum (maps to existing clause types)

NDAChecklist ── 1:N ── ChecklistItem
```

---

## New Entities

### PlaybookConfig

```python
class PlaybookConfig(BaseModel):
    """Root configuration for an organization's contract review playbook."""
    name: str                                    # "Standard Commercial Playbook"
    version: str = "1.0"
    positions: dict[str, PlaybookPosition]       # keyed by clause_type
```

### PlaybookPosition

```python
class NegotiationTier(StrEnum):
    TIER_1 = "tier_1"    # Must-have (deal breakers)
    TIER_2 = "tier_2"    # Should-have (strong preferences)
    TIER_3 = "tier_3"    # Nice-to-have (concession candidates)

class PlaybookPosition(BaseModel):
    """An organization's standard position for a specific clause type."""
    clause_type: str                             # Maps to ClauseTypeEnum
    standard_position: str                       # Preferred terms (human-readable)
    acceptable_range: AcceptableRange | None = None
    escalation_triggers: list[str] = []          # Patterns that force RED
    review_guidance: str = ""                     # Instructions for reviewer
    priority: NegotiationTier = NegotiationTier.TIER_2
    required: bool = False                       # Is this clause mandatory?
```

### AcceptableRange

```python
class AcceptableRange(BaseModel):
    """Defines the acceptable range for a clause position."""
    min_position: str                            # Minimum acceptable
    max_position: str                            # Maximum acceptable
    description: str = ""                        # Human-readable range description
```

### Severity (Review Classification)

```python
class ReviewSeverity(StrEnum):
    GREEN = "green"      # Acceptable — aligns with or better than standard
    YELLOW = "yellow"    # Negotiate — outside standard but within range
    RED = "red"          # Escalate — outside acceptable range or triggers escalation
```

### ReviewFinding

```python
class ReviewFinding(BaseModel):
    """A single clause-level finding from a playbook review."""
    finding_id: str                              # Unique ID
    clause_id: str                               # Reference to extracted Clause
    clause_type: str                             # ClauseTypeEnum value
    clause_heading: str                          # From extracted clause
    severity: ReviewSeverity                     # GREEN / YELLOW / RED
    current_language: str                        # Exact text from TrustGraph
    playbook_position: str                       # Standard position from playbook
    deviation_description: str                   # What deviates and why
    business_impact: str                         # Practical impact of accepting
    risk_score: RiskScore | None = None          # Severity × Likelihood
    redline: RedlineSuggestion | None = None     # For YELLOW/RED findings
    provenance_facts: list[str] = []             # Fact IDs supporting this finding
    char_start: int = 0                          # Source text location
    char_end: int = 0
```

### RiskScore

```python
class RiskLevel(StrEnum):
    LOW = "low"          # Score 1-4 (GREEN)
    MEDIUM = "medium"    # Score 5-9 (YELLOW)
    HIGH = "high"        # Score 10-15 (ORANGE)
    CRITICAL = "critical"  # Score 16-25 (RED)

class RiskScore(BaseModel):
    """5×5 Severity × Likelihood risk assessment."""
    severity: int = Field(ge=1, le=5)            # Impact if risk materializes
    likelihood: int = Field(ge=1, le=5)          # Probability of materialization
    score: int = Field(ge=1, le=25)              # severity × likelihood
    level: RiskLevel                             # Derived from score
    severity_rationale: str = ""                 # Why this severity rating
    likelihood_rationale: str = ""               # Why this likelihood rating
```

### RedlineSuggestion

```python
class RedlineSuggestion(BaseModel):
    """Specific alternative language for a YELLOW/RED finding."""
    proposed_language: str                       # LLM-generated alternative
    rationale: str                               # Suitable for counterparty
    priority: NegotiationTier                    # Must-have / Should-have / Nice-to-have
    fallback_language: str | None = None         # If primary is rejected
```

### ReviewResult

```python
class ReviewResult(BaseModel):
    """Complete playbook review result for a contract."""
    document_id: str
    playbook_name: str
    findings: list[ReviewFinding]                # Per-clause findings
    summary: str                                 # Executive summary
    risk_profile: RiskProfile                    # Aggregate risk
    negotiation_strategy: str                    # Tier 1/2/3 recommendations
    review_time_ms: int = 0
    green_count: int = 0
    yellow_count: int = 0
    red_count: int = 0
    missing_clauses: list[str] = []              # Required clauses not found
```

### RiskProfile

```python
class RiskProfile(BaseModel):
    """Aggregate risk profile for a contract."""
    overall_level: RiskLevel
    overall_score: float                         # Average risk score
    highest_risk_finding: str                    # Finding ID of highest risk
    risk_distribution: dict[str, int]            # { "low": 5, "medium": 3, "high": 2, "critical": 1 }
    tier_1_issues: int                           # Must-have issues count
    tier_2_issues: int
    tier_3_issues: int
```

---

## NDA Triage Entities

### ChecklistItem

```python
class AutomationLevel(StrEnum):
    AUTO = "auto"          # Fully automated (pattern matching)
    HYBRID = "hybrid"      # Automated + LLM verification
    LLM_ONLY = "llm_only"  # Requires LLM judgment

class ChecklistStatus(StrEnum):
    PASS = "pass"          # Meets criteria
    FAIL = "fail"          # Does not meet criteria
    REVIEW = "review"      # Needs human review
    NOT_APPLICABLE = "n/a"  # Not relevant to this NDA

class ChecklistItem(BaseModel):
    """A single item in the NDA triage checklist."""
    item_id: str
    name: str                                    # "Agreement Structure"
    automation: AutomationLevel
    description: str = ""
```

### ChecklistResult

```python
class ChecklistResult(BaseModel):
    """Result of evaluating a single checklist item."""
    item_id: str
    name: str
    status: ChecklistStatus                      # PASS / FAIL / REVIEW / N/A
    finding: str = ""                            # What was found
    evidence: str = ""                           # Supporting text from contract
    fact_ids: list[str] = []                     # Provenance
```

### TriageClassification

```python
class TriageLevel(StrEnum):
    GREEN = "green"        # Standard — route for signature
    YELLOW = "yellow"      # Counsel review needed
    RED = "red"            # Significant issues — full review

class TriageClassification(BaseModel):
    """Overall NDA triage classification."""
    level: TriageLevel
    routing: str                                 # "Approve and route for signature" etc.
    timeline: str                                # "Same day" / "1-2 business days" / "3-5 business days"
    rationale: str                               # Why this classification
```

### TriageResult

```python
class TriageResult(BaseModel):
    """Complete NDA triage result."""
    document_id: str
    classification: TriageClassification
    checklist_results: list[ChecklistResult]
    key_issues: list[str]                        # Top issues for YELLOW/RED
    summary: str
    triage_time_ms: int = 0
    pass_count: int = 0
    fail_count: int = 0
    review_count: int = 0
```

---

## Relationship to Existing Entities

| New Entity | Relates To | Relationship |
|-----------|-----------|-------------|
| `ReviewFinding.clause_id` | `Clause.clause_id` | M:1 — finding references extracted clause |
| `ReviewFinding.provenance_facts` | `Fact.fact_id` | M:N — finding backed by extracted facts |
| `ReviewFinding.clause_type` | `ClauseTypeEnum` | Maps to existing clause type system |
| `PlaybookPosition.clause_type` | `ClauseTypeEnum` | Playbook positions keyed by clause type |
| `ChecklistResult.fact_ids` | `Fact.fact_id` | M:N — checklist result backed by facts |
| `ReviewResult` | `ReasoningSession` | Review stored as a reasoning session |

---

## Truth Model Classification

| Entity | Truth Layer | Rationale |
|--------|------------|-----------|
| Extracted clause text | **Fact** | Directly from document |
| Playbook position | **Configuration** | Organization-defined, not from document |
| ReviewFinding severity | **Opinion** | Role-dependent, policy-dependent judgment |
| RiskScore | **Inference** | Derived from facts + playbook + LLM reasoning |
| RedlineSuggestion | **Opinion** | Generated alternative, not grounded in document |
| ChecklistResult status | **Inference** | Derived from extraction + checklist criteria |
| TriageClassification | **Opinion** | Aggregate judgment based on checklist |
