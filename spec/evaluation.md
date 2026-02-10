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

#### Why Recall@N and Precision@N

Simple precision and recall treat extraction as a binary problem — but in
practice, ContractOS returns **ranked lists** of facts, clauses, and entities.
A user asking "What are the payment terms?" gets a ranked set of relevant
facts. The quality of that ranking matters as much as completeness.

- **Precision@N**: Of the top N results returned, how many are correct?
  This measures whether the most prominent results are trustworthy.
- **Recall@N**: Of all relevant items, how many appear in the top N results?
  This measures whether important items are surfaced early.
- **F1@N**: Harmonic mean of Precision@N and Recall@N at a given cutoff.

These are standard information retrieval metrics (used in search engines,
recommendation systems, and legal tech benchmarks like LegalBench).

#### Extraction Metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| Precision@5 (entities) | Of top 5 extracted entities per type, % correct | > 95% |
| Precision@10 (entities) | Of top 10 extracted entities per type, % correct | > 93% |
| Recall@20 (entities) | Of all annotated entities, % found in top 20 results | > 90% |
| Precision@N (clauses) | Of top N identified clauses, % correctly typed | > 92% |
| Recall@N (clauses) | Of all annotated clauses, % found in top N results | > 88% |
| Span accuracy | % of facts with correct character offsets (exact match) | > 98% |
| Table extraction P@N | Of top N table cells extracted, % correctly parsed | > 90% |
| Structural accuracy | % of sections/headings correctly identified | > 95% |
| MRR (Mean Reciprocal Rank) | Average 1/rank of first correct result per query | > 0.85 |
| MAP (Mean Average Precision) | Mean of average precision across all queries | > 0.82 |
| NDCG@10 | Normalized Discounted Cumulative Gain at 10 | > 0.88 |

#### Clause-Specific Extraction Metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| Clause type accuracy | % of clauses assigned the correct type | > 90% |
| Mandatory fact recall@N | Of mandatory facts per clause type, % extracted in top N | > 85% |
| Cross-reference precision | % of extracted cross-references that are valid | > 92% |
| Cross-reference resolution | % of valid cross-references resolved to target clause | > 80% |
| Completeness gap detection | % of missing mandatory facts correctly flagged | > 75% |

**Evaluation method**:
1. Maintain a benchmark set of 50–100 annotated procurement contracts
2. Each contract has human-annotated ground truth: entities (ranked by
   importance), clauses (with types and mandatory facts), tables, structure,
   and cross-references
3. Run FactExtractor on benchmark set
4. Compute Precision@N, Recall@N, F1@N, MRR, MAP, NDCG per fact type
5. Compute clause-specific metrics (type accuracy, mandatory fact coverage,
   cross-reference resolution)
6. Track over time — extraction quality must never regress

**N values by context**:
- Entity extraction: N = 5, 10, 20 (most contracts have <50 key entities)
- Clause identification: N = 10, 20 (most contracts have 10–30 clauses)
- Table cells: N = 50, 100 (large tables can have hundreds of cells)
- Cross-references: N = 10, 20 (per clause)

**Frequency**: On every change to extraction pipeline.

### Tier 2: Inference Quality

**What**: Are derived claims correct, well-supported, and appropriately
confident?

**How**: Expert-rated evaluation. Procurement and legal professionals score
inference quality. Ranked retrieval metrics measure whether the best
inferences surface first.

| Metric | Definition | Target |
|--------|-----------|--------|
| Correctness@1 | Is the top-ranked inference correct? | > 85% |
| Correctness@3 | Of top 3 inferences, % rated "correct" by experts | > 80% |
| Precision@5 (supporting facts) | Of top 5 facts cited per inference, % actually relevant | > 90% |
| Recall@10 (supporting facts) | Of all relevant facts, % cited in top 10 | > 85% |
| Grounding | % of inferences with valid supporting facts | 100% (hard requirement) |
| Confidence calibration | Correlation between stated confidence and actual correctness | > 0.85 |
| Explanation quality | Expert rating of reasoning chain clarity (1-5) | > 3.5 |
| False positive rate@high_conf | % of incorrect inferences with confidence > 0.80 | < 5% |
| MRR (inference ranking) | Average 1/rank of first correct inference per query | > 0.88 |
| NDCG@5 (fact relevance) | Quality of fact ranking within provenance chains | > 0.85 |

**Evaluation method**:
1. Generate inferences on benchmark contracts
2. Present each inference to 3 domain experts (blind — they don't see
   confidence scores)
3. Experts rate: correct / partially correct / incorrect
4. Experts also rate supporting fact relevance (relevant / partially / irrelevant)
5. Compare expert ratings against system confidence
6. Compute calibration curve
7. Compute Precision@N and Recall@N for supporting fact selection

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

**How**: User feedback, task completion metrics, and ranked answer quality.

| Metric | Definition | Target |
|--------|-----------|--------|
| User satisfaction | % of answers rated "helpful" or "very helpful" | > 75% |
| Answer precision@1 | % of first answers that directly address the question | > 80% |
| Task completion | % of users who completed their task using the answer | > 70% |
| Follow-up rate | % of answers that required clarification or correction | < 25% |
| Provenance usefulness | % of users who found provenance chain helpful (when expanded) | > 60% |
| Time saved | Estimated time saved vs. manual review | Track and report |
| Adoption | % of available users actively using the system weekly | > 50% |

**Evaluation method**:
1. Thumbs up/down on every answer (minimal friction)
2. Optional: "Was this answer complete?" / "Did you need to verify manually?"
3. Monthly user interviews (sample of active users)
4. Task-level tracking (if integrated with workflow)

**Frequency**: Continuous (feedback), monthly (analysis), quarterly (interviews).

---

## Ranked Retrieval Metrics — Reference

ContractOS uses information retrieval (IR) metrics because contract analysis
is fundamentally a **retrieval + reasoning** problem. The system retrieves
facts, ranks them, and reasons over the top results.

| Metric | What It Measures | Formula (simplified) |
|--------|-----------------|---------------------|
| **Precision@N** | Of the top N results, how many are relevant? | relevant_in_top_N / N |
| **Recall@N** | Of all relevant items, how many are in the top N? | relevant_in_top_N / total_relevant |
| **F1@N** | Balance of Precision@N and Recall@N | 2 * (P@N * R@N) / (P@N + R@N) |
| **MRR** | How high is the first correct result? | Average of 1/rank_of_first_correct |
| **MAP** | Average precision across all recall levels | Mean of AP per query |
| **NDCG@N** | Quality of ranking considering graded relevance | Accounts for position and relevance grade |

**Why not just Precision and Recall?**

Flat precision/recall treats all results equally — finding a party name at
rank 1 and rank 100 are the same. But for a procurement user, the **order
matters**. If the correct answer is buried at position 15, the system has
failed even if recall is technically high. Precision@N and NDCG@N capture
this: the best results must appear first.

**Choosing N values:**

N should reflect the user's attention budget. A procurement user reviewing
extracted entities will look at 5–10 results. A user scanning clauses will
review 10–20. N is set per task type to match realistic usage patterns.

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
    precision_at_5: 0.93       # alert if drops below 93%
    recall_at_20: 0.88
    span_accuracy: 0.96
    mrr: 0.82
    map: 0.80
    ndcg_at_10: 0.85
    clause_type_accuracy: 0.88
    mandatory_fact_recall_at_n: 0.82
    cross_reference_precision: 0.90
  
  inference:
    correctness_at_1: 0.82
    correctness_at_3: 0.78
    grounding: 1.00            # hard requirement — never ship ungrounded inferences
    confidence_calibration: 0.80
    false_positive_rate_high_conf: 0.07
    supporting_fact_precision_at_5: 0.88
  
  answer_quality:
    user_satisfaction: 0.70
    answer_precision_at_1: 0.78
    follow_up_rate: 0.30       # alert if rises above 30%
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
