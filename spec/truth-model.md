# ContractOS Truth Model

> This is the most important file in the entire system.

ContractOS strictly distinguishes between **Facts**, **Bindings**,
**Inferences**, and **Opinions**.

This separation is foundational and non-negotiable.

---

## Overview

```
                    GROUND TRUTH (persisted, immutable)
                    ┌─────────────────────────────┐
                    │           FACTS              │
                    │  directly grounded in text   │
                    └──────────────┬──────────────┘
                                   │
                    RESOLVED TRUTH (persisted, scoped, deterministic)
                    ┌──────────────┴──────────────┐
                    │          BINDINGS            │
                    │  explicit semantic mappings   │
                    └──────────────┬──────────────┘
                                   │
                    DERIVED TRUTH (persisted, probabilistic, revisable)
                    ┌──────────────┴──────────────┐
                    │         INFERENCES           │
                    │  claims combining facts +    │
                    │  domain knowledge            │
                    └──────────────┬──────────────┘
                                   │
                    CONTEXTUAL JUDGMENT (computed on demand, never persisted)
                    ┌──────────────┴──────────────┐
                    │          OPINIONS            │
                    │  role/policy/risk-dependent  │
                    └─────────────────────────────┘
```

Each layer depends on the layers above it. No layer may contradict a higher
layer. Opinions never overwrite inferences. Inferences never overwrite facts.

---

## 1. Facts

### Definition

A fact is a claim that can be:

- Directly grounded in contract text
- Reproduced by re-parsing the document
- Cited with precise evidence

Facts **do not require interpretation**. They are what the document says, not
what it means.

### Examples

| Fact | Evidence |
|------|----------|
| The string "Net 90" appears in §5.2 | Character offsets 1,203–1,209 in `contract-2024-001.docx` |
| The product "Dell Inspiron 15" appears in Schedule A, row 3 | Table cell at row 3, column "Product Name" |
| The location "Bangalore" appears in Schedule B, paragraph 2 | Character offsets 4,501–4,510 |
| §12.1 contains the heading "Indemnification" | Heading element at document structure level |
| An amendment dated 2024-03-15 exists | Document metadata + text content |

### Schema

```
Fact {
  fact_id:        string       // globally unique
  fact_type:      enum         // text_span, entity, clause, table_cell,
                               // heading, metadata, structural
  value:          string       // the extracted content
  evidence: {
    document_id:  string       // which document
    text_span:    string       // exact text
    char_start:   int          // start offset
    char_end:     int          // end offset
    location_hint: string      // human-readable: "§5.2, paragraph 3"
    structural_path: string    // machine-readable: "body > section[5] > para[3]"
  }
  extraction_method: string    // "parser_v2", "table_extractor", "ocr_v1"
  extracted_at:   timestamp
}
```

### Fact Rules

1. Facts are **immutable** — once extracted, they never change (the document
   doesn't change)
2. Facts are **source-addressable** — every fact points to exact document
   location
3. Facts are **safe to persist** indefinitely
4. Facts from different documents may **contradict** each other — this is
   expected (see Fact Precedence in `contract-graph.md`)
5. Facts have **no confidence score** — they either exist in the text or they
   don't
6. Re-extraction of the same document MUST produce the same facts
   (deterministic)

---

## 1b. Clause Structure

### Why Clauses Are More Than Text Spans

A clause is not just a text span with a heading — it is a **structured unit of
legal meaning** with internal components, cross-references, and type-specific
mandatory facts.

Consider this real contract text:

> *"Subject to termination clause 3.1(a). If the lessee violates the building
> by-laws referred in Appendix A, the notice period as mentioned in section
> 3.2.1 will not be applicable and the lessee may be asked to vacate the
> property immediately."*

This single clause contains:

| Component | What it is | Truth Layer |
|-----------|-----------|-------------|
| "termination clause 3.1(a)" | **Cross-reference** to another clause | Fact (type: cross_reference) |
| "building by-laws referred in Appendix A" | **Cross-reference** to an appendix | Fact (type: cross_reference) |
| "notice period as mentioned in section 3.2.1" | **Cross-reference** to another section | Fact (type: cross_reference) |
| "lessee may be asked to vacate immediately" | **Consequence** (an obligation/right) | Fact (extractable) → Inference (what it means) |
| The clause itself | **Clause type**: termination exception | Fact (type: clause) with clause_type tag |

### Cross-References

Clauses frequently reference other clauses, sections, appendices, and
schedules. These cross-references are **facts** — they are explicitly stated
in the text — but they create a **reference graph within the document** that
is essential for reasoning.

```
CrossReference {
  source_clause_id:   string    // the clause containing the reference
  target_reference:   string    // "section 3.2.1", "Appendix A", "clause 3.1(a)"
  target_clause_id:   string?   // resolved FK → Clause (if resolvable)
  reference_type:     enum      // section_ref, appendix_ref, schedule_ref,
                                // clause_ref, external_doc_ref
  context:            string    // surrounding text explaining the reference
  effect:             enum      // modifies, overrides, conditions, incorporates,
                                // exempts, delegates
}
```

Cross-references are extracted as facts and then **resolved** to link source
and target clauses. Unresolvable references (e.g., "as per applicable law")
are flagged but not guessed.

### Entity Aliasing Within Clauses

Contracts routinely introduce aliases for parties and entities:

> *"This agreement is between Alpha Corp, hereinafter referred to as 'Buyer',
> and Beta Inc, hereinafter referred to as 'Vendor'."*

This is a **binding** (Alpha Corp → Buyer), but it is also a structural
pattern: the alias is introduced within a specific clause and applies
throughout the document. The BindingResolver must detect these patterns:

- `"X, hereinafter referred to as 'Y'"`
- `"X (the 'Y')"`
- `"X, hereafter 'Y'"`
- `"X shall mean Y"`

These are all binding-creation patterns that produce `Binding` records.

### Clause Typing and Mandatory Facts

Every clause has a **type**, and each type has a **schema** of facts that it
is expected to contain. This is critical for two reasons:

1. **Completeness checking** — if a termination clause has no notice period,
   that is a gap worth flagging
2. **Structured extraction** — knowing the clause type tells the extractor
   what to look for

```
ClauseType {
  type_id:           string     // "termination", "payment", "indemnity", etc.
  display_name:      string     // "Termination Clause"
  mandatory_facts:   [MandatoryFact]  // facts this clause type MUST contain
  optional_facts:    [MandatoryFact]  // facts this clause type MAY contain
  common_cross_refs: [string]         // clause types it commonly references
}

MandatoryFact {
  fact_name:         string     // "notice_period", "termination_reasons"
  fact_description:  string     // human-readable description
  entity_type:       EntityType // duration, money, party, etc.
  required:          bool       // true = mandatory, false = optional
}
```

### Clause Type Registry (Phase 1)

| Clause Type | Mandatory Facts | Optional Facts |
|-------------|----------------|----------------|
| **Termination** | notice_period (duration), termination_reasons (text) | cure_period (duration), termination_fee (money), survival_clauses (cross_ref) |
| **Payment** | payment_terms (text), payment_amount or pricing_model | late_payment_penalty (money/percent), currency, payment_method |
| **Indemnity** | indemnifying_party (party), indemnified_party (party), covered_losses (text) | indemnity_cap (money), exclusions (text), survival_period (duration) |
| **Liability** | liability_cap (money or formula) | exclusions (text), consequential_damages (bool) |
| **Confidentiality** | definition_of_confidential (text), obligations (text) | duration (duration), exclusions (text), return_obligations (text) |
| **SLA / Service Level** | service_metrics (text), measurement_method (text) | penalties (money/percent), reporting_frequency (duration), remedy (text) |
| **Price Escalation** | escalation_trigger (text), escalation_threshold (percent/money) | escalation_cap (percent), escalation_frequency (duration), index_reference (text) |
| **Penalty** | penalty_trigger (text), penalty_value (money/percent) | penalty_cap (money), cure_period (duration), waiver_conditions (text) |
| **Force Majeure** | qualifying_events (text), notification_requirement (duration) | termination_right (bool), mitigation_obligation (text) |
| **Assignment** | consent_required (bool) | permitted_assignments (text), change_of_control (text) |
| **Governing Law** | jurisdiction (location), governing_law (text) | dispute_resolution (text), arbitration_venue (location) |
| **Warranty** | warranty_scope (text), warranty_period (duration) | remedy (text), exclusions (text), warranty_cap (money) |
| **IP / Intellectual Property** | ip_ownership (text) | license_scope (text), background_ip (text), foreground_ip (text) |
| **Schedule Adherence** | milestones (text), delivery_dates (date) | penalties (money/percent), acceptance_criteria (text), delay_remedy (text) |

### How Clause Structure Flows Through the Truth Model

```
1. FACT EXTRACTION
   FactExtractor identifies clause boundaries and text
   → Fact (type: clause, clause_type: "termination")

2. CROSS-REFERENCE EXTRACTION
   FactExtractor identifies "section 3.2.1", "Appendix A"
   → Fact (type: cross_reference) for each reference
   → CrossReference records linking source → target

3. MANDATORY FACT EXTRACTION
   Given clause_type = "termination", extractor looks for:
   - notice_period → found: "30 days" → Fact (type: entity, entity_type: duration)
   - termination_reasons → found: "material breach" → Fact (type: text_span)
   - Missing: cure_period → flagged as absent (optional, not an error)

4. BINDING RESOLUTION
   BindingResolver processes alias patterns within clauses
   → Binding ("Buyer" := "Alpha Corp")

5. COMPLETENESS CHECK
   Compare extracted facts against ClauseType.mandatory_facts
   → If mandatory fact missing → flag as gap (this is an Inference, not a Fact)
   → "Termination clause at §3.1 is missing a notice period" (confidence: 0.95)
```

### Clause Structure Rules

1. Every clause MUST be assigned a `clause_type` — either by pattern matching
   or LLM classification
2. Cross-references within clauses MUST be extracted as facts and resolved
   where possible
3. Mandatory facts per clause type are **expected, not enforced** — a missing
   mandatory fact is flagged as a gap (inference), not treated as an error
4. The Clause Type Registry is **configurable** — organizations can add custom
   clause types and modify mandatory fact schemas
5. Entity aliases introduced in clauses MUST be captured as Bindings

---

## 2. Bindings

### Definition

A binding is an **explicitly stated semantic mapping** found in a contract. It
is deterministic (not probabilistic) but requires resolution logic to apply
throughout the document.

Bindings sit between Facts and Inferences because they are:
- **Grounded in text** (like facts) — the definition clause is a fact
- **Semantically transformative** (like inferences) — they change how every
  other clause is interpreted

### Why Bindings Are Separate

Consider: *"'Service Provider' shall mean Acme Corp and its affiliates."*

- The **fact** is: this text exists at §1.2
- The **binding** is: every occurrence of "Service Provider" in this contract
  resolves to "Acme Corp and its affiliates"
- An **inference** would be: "Acme Corp is responsible for the maintenance
  obligations in §7.3"

Without the binding layer, every inference that involves defined terms would
need to re-derive the definition resolution. Bindings make this explicit,
cached, and auditable.

### Examples

| Binding | Source | Scope |
|---------|--------|-------|
| "Service Provider" := "Acme Corp and its affiliates" | §1.2 Definitions | This contract |
| "Effective Date" := "2024-01-15" | §1.5 Definitions | This contract |
| "Territory" := "India, United States, United Kingdom" | Schedule C | This contract family |
| "Confidential Information" := [full definition text] | §1.8 | This contract + SOWs |
| Assignment: All obligations transferred from "OldCo" to "NewCo" per Amendment-003 | Amendment-003, §2 | This contract family, post-amendment |

### Schema

```
Binding {
  binding_id:     string       // globally unique
  binding_type:   enum         // definition, assignment, incorporation,
                               // delegation, scope_limitation
  term:           string       // the defined term
  resolves_to:    string       // what it resolves to
  source_fact_id: string       // the fact that grounds this binding
  scope:          enum         // contract, contract_family, repository
  scope_filter: {
    document_ids: [string]     // which documents this binding applies to
    effective_from: date       // when binding becomes active (for assignments)
    effective_until: date      // when binding expires (if applicable)
  }
  is_overridden_by: string?    // binding_id of a later binding that supersedes
}
```

### Binding Rules

1. Bindings are **deterministic** — no confidence score; they are explicitly
   stated
2. Bindings are **scoped** — a definition in Contract A does not apply to
   Contract B unless explicitly incorporated
3. Bindings can be **overridden** — an amendment may redefine a term; the later
   binding supersedes the earlier one (see `contract-graph.md` for precedence)
4. Bindings are **persisted** and indexed — they are resolved once and reused
   across all queries within scope
5. Binding resolution is a **prerequisite** for inference — agents must resolve
   bindings before generating inferences

### Binding Resolution Order

When a term appears in a document, resolve in this order:

1. Check bindings within the same document
2. Check bindings in the governing document (e.g., MSA for a SOW)
3. Check bindings in the latest amendment
4. If still unresolved, flag as ambiguous (do not guess)

---

## 3. Inferences

### Definition

An inference is a derived claim that:

- Is not explicitly stated in any single location
- Emerges from combining facts, bindings, and/or domain knowledge
- Is **probabilistic**, not absolute
- Must always reference its supporting evidence

### Examples

| Inference | Supporting Evidence | Confidence |
|-----------|-------------------|------------|
| "This contract includes a maintenance obligation for IT equipment" | Fact: §7.3 text describes support obligations; Fact: Schedule A lists Dell Inspiron; DomainBridge: Dell Inspiron → IT Equipment | 0.92 |
| "The supplier provides multi-location support in India" | Fact: Schedule B lists Bangalore, Pune, Mumbai; DomainBridge: all three → cities in India | 0.95 |
| "The payment terms are Net 60" (effective, post-amendment) | Fact: MSA §5.2 says Net 90; Fact: Amendment-002 §1 says Net 60; Precedence: amendment > MSA | 0.98 |
| "This contract is similar to Contract-2023-047" | Embedding similarity: 0.89; Shared entities: same supplier, same category; Structural similarity: matching clause types | 0.85 |

### Schema

```
Inference {
  inference_id:      string
  inference_type:    enum       // obligation, coverage, similarity,
                                // compliance_gap, risk_indicator,
                                // entity_resolution, scope_determination
  claim:             string     // human-readable statement
  supporting_facts:  [string]   // fact_ids
  supporting_bindings: [string] // binding_ids
  domain_sources:    [string]   // DomainBridge source references
  reasoning_chain:   string     // step-by-step explanation
  confidence:        float      // 0.0 – 1.0, calibrated (see evaluation.md)
  confidence_basis:  string     // why this confidence level
  generated_by:      string     // which agent/tool
  generated_at:      timestamp
  invalidated_by:    string?    // if new evidence invalidated this inference
}
```

### Inference Rules

1. Inferences **must reference supporting facts** — no inference without
   evidence
2. Inferences **may change** with new evidence — they are revisable
3. Inferences **must never overwrite facts** — if an inference contradicts a
   fact, the inference is wrong
4. Inferences **carry confidence scores** — calibrated against expert judgment
   (see `evaluation.md`)
5. Inferences from **external knowledge** must declare the source explicitly
   in `domain_sources`
6. An inference with **confidence < 0.5** is flagged as "low confidence" and
   requires human review before being used in further reasoning
7. Inferences are **safe to persist** but must be re-evaluated when source
   facts or bindings change

### Confidence Calibration

Confidence is not a magic number. It is calibrated:

- **0.95–1.0**: Effectively certain — all evidence is direct and unambiguous
- **0.80–0.94**: High confidence — strong evidence with minor gaps or domain
  knowledge dependency
- **0.60–0.79**: Moderate — evidence supports the claim but alternative
  interpretations exist
- **0.40–0.59**: Low — plausible but significant uncertainty; flag for review
- **Below 0.40**: Speculative — do not use without human confirmation

See `evaluation.md` for how these thresholds are validated.

---

## 4. Opinions (Judgments / Risk Assessments)

### Definition

An opinion is a contextual judgment based on:

- Policy (organization's standard contract terms)
- Risk tolerance (what level of exposure is acceptable)
- Role (legal sees differently from procurement)
- Jurisdiction (US law vs. EU law vs. Indian law)
- Benchmarks (what is "normal" for this contract type)

Opinions are **never ground truth**. They are always relative to a context.

### Examples

| Opinion | Depends On |
|---------|-----------|
| "This indemnity clause is high risk" | Organization's risk policy |
| "Termination rights are weaker than standard" | Benchmark: standard procurement template |
| "This contract is non-compliant with GDPR" | Jurisdiction: EU; Policy: data protection requirements |
| "The payment terms are unfavorable" | Benchmark: industry average for this category |
| "This supplier has concentrated risk across 7 contracts" | Role: procurement category manager; Risk policy |

### Schema

```
Opinion {
  opinion_id:        string
  opinion_type:      enum       // risk_assessment, compliance_check,
                                // benchmark_comparison, policy_alignment,
                                // recommendation
  judgment:          string     // human-readable statement
  supporting_inferences: [string]  // inference_ids
  supporting_facts:  [string]      // fact_ids (direct)
  policy_reference:  string?       // which policy was applied
  benchmark:         string?       // what was compared against
  role_context:      string        // who this opinion is for
  jurisdiction:      string?       // if jurisdiction-dependent
  severity:          enum          // critical, high, medium, low, info
  generated_at:      timestamp
}
```

### Opinion Rules

1. Opinions are **computed on demand** — never pre-computed and stored as truth
2. Opinions are **never persisted as facts or inferences** — this prevents
   legal hallucinations becoming "truth"
3. Opinions **may reference facts and inferences** — they build on the truth
   layers
4. Opinions are **role-dependent** — the same contract may produce different
   opinions for legal vs. procurement
5. Opinions are **policy-dependent** — changing the policy changes the opinion
6. Opinions have **no confidence score** — they are judgments, not predictions;
   instead they have **severity**

---

## 5. Provenance Chain

Every answer ContractOS produces is backed by a provenance chain:

```
Answer: "Yes, this contract covers maintenance for IT equipment at India offices"
│
├── Opinion: "Coverage is adequate" (severity: info)
│   └── based on: organization's coverage policy
│
├── Inference: "Maintenance obligation applies to IT equipment at India locations"
│   ├── confidence: 0.92
│   ├── Fact: §7.3 describes "ongoing support obligations" [char 3201–3456]
│   ├── Binding: "Service Provider" := "Dell Technologies" [§1.2]
│   ├── Fact: Schedule A row 3 lists "Dell Inspiron 15" [table cell]
│   ├── DomainBridge: Dell Inspiron 15 → Laptop → IT Equipment [source: UNSPSC]
│   ├── Fact: Schedule B lists "Bangalore, Pune, Mumbai" [char 4501–4540]
│   └── DomainBridge: Bangalore, Pune, Mumbai → India [source: geographic_db]
│
└── Reasoning chain: "§7.3 establishes support obligations for items in
    Schedule A at locations in Schedule B. Dell Inspiron (IT Equipment per
    UNSPSC classification) is in Schedule A. Bangalore, Pune, Mumbai (India)
    are in Schedule B. Therefore, maintenance for IT equipment at India
    offices is covered."
```

This provenance chain is:
- **Always available** to the user
- **Navigable** — click any fact to see the source document
- **Auditable** — a legal reviewer can verify every step
- **Reproducible** — re-running the same query produces the same chain

---

## 6. What Breaking This Model Looks Like

| Violation | Consequence |
|-----------|------------|
| Storing an inference as a fact | Future reasoning treats uncertain claims as ground truth |
| Storing an opinion as an inference | Policy-dependent judgments become "objective" claims |
| Inference without supporting facts | Hallucination — no way to verify or audit |
| Ignoring bindings during inference | "Service Provider" remains unresolved; wrong entity attributed |
| Persisting opinions | Legal hallucinations become permanent "truth" in the system |
| Confidence without calibration | 0.85 means nothing if not validated against expert judgment |

**Breaking this model breaks ContractOS.**
