# ContractOS Evaluation Framework

> If you can't measure it, you can't trust it.

## Why Evaluation Is Non-Negotiable

Legal AI systems fail when they:
1. Don't know they're wrong
2. Express false confidence
3. Can't explain their reasoning
4. Aren't tested against expert judgment

ContractOS builds evaluation into the DNA — not as an afterthought, but as a
core system component that runs continuously.

---

## Three-Tier Evaluation

### Tier 1: Fact Extraction Accuracy

**What**: Did we correctly extract text spans, entities, clauses, and
structural elements from documents?

**How**: Deterministic, automated evaluation against annotated contracts.

| Metric | Definition | Target |
|--------|-----------|--------|
| Precision | % of extracted facts that are correct | > 95% |
| Recall | % of actual facts that were extracted | > 90% |
| Span accuracy | % of facts with correct character offsets | > 98% |
| Entity accuracy | % of entities correctly identified and typed | > 92% |
| Table extraction | % of table cells correctly parsed | > 90% |
| Structural accuracy | % of sections/headings correctly identified | > 95% |

**Evaluation method**:
1. Maintain a benchmark set of 50–100 annotated procurement contracts
2. Each contract has human-annotated ground truth: entities, clauses, tables,
   structure
3. Run FactExtractor on benchmark set
4. Compute precision/recall/F1 per fact type
5. Track over time — extraction quality must never regress

**Frequency**: On every change to extraction pipeline.

### Tier 2: Inference Quality

**What**: Are derived claims correct, well-supported, and appropriately
confident?

**How**: Expert-rated evaluation. Procurement and legal professionals score
inference quality.

| Metric | Definition | Target |
|--------|-----------|--------|
| Correctness | % of inferences rated "correct" by experts | > 80% |
| Grounding | % of inferences with valid supporting facts | 100% (hard requirement) |
| Confidence calibration | Correlation between stated confidence and actual correctness | > 0.85 |
| Explanation quality | Expert rating of reasoning chain clarity (1-5) | > 3.5 |
| False positive rate | % of incorrect inferences stated with high confidence | < 5% |

**Evaluation method**:
1. Generate inferences on benchmark contracts
2. Present each inference to 3 domain experts (blind — they don't see
   confidence scores)
3. Experts rate: correct / partially correct / incorrect
4. Compare expert ratings against system confidence
5. Compute calibration curve

**Confidence calibration**:
A well-calibrated system means:
- Of all inferences rated 0.90+ confidence, ~90% should be correct
- Of all inferences rated 0.70-0.80, ~75% should be correct
- Of all inferences rated 0.50-0.60, ~55% should be correct

If the system says 0.90 but only 60% are correct — it's overconfident and
dangerous.

**Frequency**: Quarterly, or when inference engine changes.

### Tier 3: Answer Usefulness

**What**: Did the user get what they needed? Was the answer actionable?

**How**: User feedback and task completion metrics.

| Metric | Definition | Target |
|--------|-----------|--------|
| User satisfaction | % of answers rated "helpful" or "very helpful" | > 75% |
| Task completion | % of users who completed their task using the answer | > 70% |
| Follow-up rate | % of answers that required clarification or correction | < 25% |
| Time saved | Estimated time saved vs. manual review | Track and report |
| Adoption | % of available users actively using the system weekly | > 50% |

**Evaluation method**:
1. Thumbs up/down on every answer (minimal friction)
2. Optional: "Was this answer complete?" / "Did you need to verify manually?"
3. Monthly user interviews (sample of active users)
4. Task-level tracking (if integrated with workflow)

**Frequency**: Continuous (feedback), monthly (analysis), quarterly (interviews).

---

## ContractOS Benchmark (COBench)

A curated evaluation dataset specifically for procurement contract intelligence.

### Benchmark Structure

```
cobench/
├── contracts/              # 50-100 real procurement contracts (anonymized)
│   ├── msa/               # Master service agreements
│   ├── sow/               # Statements of work
│   ├── amendments/         # Amendments and change orders
│   └── families/          # Complete contract families (linked)
│
├── annotations/           # Ground truth annotations
│   ├── facts/             # Entity, clause, table, structure annotations
│   ├── bindings/          # Definition and term mappings
│   ├── relationships/     # Contract family relationships
│   └── inferences/        # Expert-validated inference ground truth
│
├── queries/               # Standard evaluation queries
│   ├── single_doc/        # Questions about individual contracts
│   │   ├── entity_extraction.json
│   │   ├── clause_identification.json
│   │   ├── obligation_detection.json
│   │   └── term_interpretation.json
│   │
│   ├── cross_doc/         # Questions requiring family traversal
│   │   ├── effective_terms.json
│   │   ├── amendment_impact.json
│   │   └── precedence_resolution.json
│   │
│   ├── repository/        # Questions across multiple contracts
│   │   ├── similarity_search.json
│   │   ├── supplier_aggregation.json
│   │   └── pattern_detection.json
│   │
│   └── inference/         # Questions requiring domain knowledge
│       ├── implicit_obligations.json
│       ├── ontological_resolution.json
│       └── coverage_determination.json
│
└── baselines/             # Results from existing tools for comparison
    ├── keyword_search.json
    ├── embedding_search.json
    └── generic_llm.json
```

### Benchmark Query Types

| Category | Example Query | What It Tests |
|----------|--------------|--------------|
| Direct extraction | "Who are the parties?" | Fact extraction |
| Term resolution | "Who is the 'Service Provider'?" | Binding resolution |
| Clause finding | "Where is the indemnity clause?" | Structural understanding |
| Obligation detection | "What are the payment obligations?" | Inference from clause text |
| Implicit coverage | "Does this cover IT equipment?" | DomainBridge + inference |
| Effective terms | "What's the current liability cap?" | Precedence resolution |
| Cross-contract | "Find contracts with similar SLAs" | Similarity + classification |
| Compliance | "Is this compliant with our standard terms?" | Policy matching |

### Building COBench

**Phase 1** (with first 50 contracts):
- Annotate facts and bindings (can be partially automated)
- Create 200 single-document queries with ground truth
- Create 50 cross-document queries with ground truth
- Establish baselines (keyword search, raw LLM)

**Phase 2** (with 200+ contracts):
- Add repository-level queries
- Add inference quality benchmarks
- Add domain knowledge resolution benchmarks
- Establish inter-annotator agreement metrics

---

## Confidence Calibration Framework

### The Problem

When ContractOS says "confidence: 0.85", that number must mean something
reliable. Uncalibrated confidence is worse than no confidence — it gives
false assurance.

### Calibration Method

```
1. COLLECT predictions with confidence scores from evaluation runs
2. BIN predictions into confidence buckets (0.5-0.6, 0.6-0.7, ..., 0.9-1.0)
3. COMPUTE actual accuracy within each bucket
4. PLOT calibration curve (predicted confidence vs. actual accuracy)
5. If curve deviates from diagonal → adjust confidence scoring
```

**Perfect calibration**: The diagonal — 80% confidence means 80% correct.

**Overconfident**: Curve below diagonal — says 80% but only 60% correct.
This is **dangerous** and must be corrected immediately.

**Underconfident**: Curve above diagonal — says 60% but actually 80% correct.
This is safe but reduces user trust. Should be improved.

### Calibration Actions

| Deviation | Action |
|-----------|--------|
| Overconfident by > 10% | Reduce confidence scores across the board; investigate inference pipeline |
| Overconfident by 5-10% | Apply temperature scaling to confidence outputs |
| Well-calibrated (within 5%) | No action needed |
| Underconfident by 5-10% | Acceptable; may improve confidence display thresholds |
| Underconfident by > 10% | Investigate why system is too conservative |

### Calibration Frequency

- After every inference engine change
- Quarterly on production data
- Whenever user feedback indicates confidence issues

---

## Regression Testing

Every evaluation metric has a **regression threshold** — the minimum acceptable
value. If a system change causes any metric to fall below its threshold, the
change is rolled back.

```yaml
regression_thresholds:
  fact_extraction:
    precision: 0.93        # alert if drops below 93%
    recall: 0.88
    span_accuracy: 0.96
  
  inference:
    correctness: 0.78
    grounding: 1.00        # hard requirement — never ship ungrounded inferences
    confidence_calibration: 0.80
    false_positive_rate: 0.07
  
  answer_quality:
    user_satisfaction: 0.70
    follow_up_rate: 0.30   # alert if rises above 30%
```

---

## Evaluation as a System Component

Evaluation is not a separate activity — it is a **running system component**:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   COBench    │────▶│  Evaluator   │────▶│  Dashboard   │
│  (dataset)   │     │  (automated) │     │  (metrics)   │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Calibrator  │
                     │  (adjusts    │
                     │  confidence) │
                     └──────────────┘
```

The Evaluator runs:
- On every CI/CD pipeline (fact extraction regression)
- On every inference engine change (full benchmark)
- Continuously in production (user feedback aggregation)
- Quarterly (expert review sessions)
