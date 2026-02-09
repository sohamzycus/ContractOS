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
