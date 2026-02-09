# ContractOS Contract Graph

> Contracts don't exist in isolation. They exist in families.

## Why a Graph

A procurement contract is rarely a single document. It is a **family**:

```
Master Services Agreement (MSA)
├── Schedule A: Pricing
├── Schedule B: Service Levels
├── SOW-001: Cloud Infrastructure
│   └── Change Order CO-001: Additional capacity
├── SOW-002: End User Computing
├── Amendment-001: Updated payment terms
├── Amendment-002: Added GDPR clauses
│   └── Side Letter: Clarification on data processing
└── Renewal-2025: Extension with modified terms
```

When a procurement user asks "What are the payment terms?", the answer depends
on walking this graph: the MSA states Net 90, Amendment-001 changed it to
Net 60, and the Renewal might have changed it again.

Without the Contract Graph, ContractOS cannot determine **effective terms**.

---

## Graph Model

The Contract Graph is a **typed directed acyclic graph (DAG)** where:

- **Nodes** are contract documents
- **Edges** are typed relationships with metadata

### Node Schema

```
ContractNode {
  document_id:      string          // globally unique
  document_type:    enum            // msa, sow, amendment, schedule,
                                    // side_letter, change_order, renewal,
                                    // purchase_order, policy, nda
  title:            string          // human-readable name
  parties:          [Party]         // extracted parties
  effective_date:   date?           // when this document takes effect
  expiry_date:      date?           // when it expires
  execution_date:   date?           // when it was signed
  status:           enum            // active, expired, superseded, terminated
  language:         string          // primary language (ISO 639-1)
  source_file:      string          // path to raw document
  fact_count:       int             // number of facts extracted
  indexed_at:       timestamp       // when ContractOS last processed this
}

Party {
  name:             string
  role:             enum            // buyer, supplier, service_provider,
                                    // licensee, licensor, employer, contractor
  normalized_name:  string          // resolved via DomainBridge
  identifiers:      [string]        // DUNS, registration numbers, etc.
}
```

### Edge Types

| Edge Type | From → To | Meaning | Precedence Impact |
|-----------|-----------|---------|-------------------|
| `governs` | MSA → SOW | SOW is governed by MSA | MSA terms apply unless SOW overrides |
| `amends` | Amendment → MSA/SOW | Amendment modifies specific clauses | Amendment overrides amended clauses |
| `supersedes` | Amendment-v2 → Amendment-v1 | Later amendment replaces earlier | Only latest amendment applies |
| `is_schedule_of` | Schedule → MSA/SOW | Schedule is part of parent | Interpreted within parent's context |
| `is_change_order_of` | CO → SOW | Change order modifies SOW | CO overrides specific SOW terms |
| `renews` | Renewal → Original | Continuation with possible changes | Renewal terms override original |
| `references` | Any → Policy/External | Document references external standard | External standard provides context |
| `side_letter_to` | Side Letter → Any | Informal modification or clarification | Depends on explicit clause |
| `replaces` | New Contract → Old Contract | Entirely new agreement | Old contract is superseded |

### Edge Schema

```
ContractEdge {
  edge_id:          string
  edge_type:        enum            // see table above
  from_document:    string          // document_id
  to_document:      string          // document_id
  affected_clauses: [string]?       // specific clauses affected (for amendments)
  effective_date:   date?           // when this relationship takes effect
  metadata:         object          // edge-type-specific additional data
  inferred:         boolean         // was this relationship auto-discovered?
  confidence:       float?          // if inferred, how confident
}
```

---

## Fact Precedence

When facts from different documents in a family conflict, precedence determines
which is **effective**.

### Precedence Rules

**Default precedence order** (later in list = higher precedence):

```
1. Referenced policy/standard     (lowest — provides defaults)
2. Master Services Agreement
3. Schedules
4. Statement of Work
5. Change Orders
6. Amendments (ordered by date)
7. Side Letters
8. Renewal                        (highest — most recent agreement)
```

**Override**: If the contract itself defines precedence (e.g., "In case of
conflict between this SOW and the MSA, the MSA shall prevail"), that explicit
clause creates a Binding that overrides the default order.

### Precedence Resolution Protocol

```
PrecedenceResolver.resolve(fact_topic, contract_family):

  1. Collect all facts about `fact_topic` across the contract family
  2. Check for an explicit precedence Binding in any document
     → If found, use the declared order
  3. If no explicit precedence, apply default order
  4. Apply temporal ordering within the same precedence level
     (later document wins)
  5. Return the effective fact with full provenance:
     - The effective value
     - Which document it comes from
     - Which documents were overridden and why
     - The precedence rule applied
```

### Example

Query: "What are the payment terms?"

```
Contract Family: MSA-2024-001
├── MSA says: "Net 90" (§5.2, fact_id: F001)
├── Amendment-001 says: "Net 60" (§1, amending §5.2, fact_id: F047)
└── Amendment-002 says: nothing about payment terms

PrecedenceResolver result:
  effective_value: "Net 60"
  source: Amendment-001 (F047)
  overrides: MSA §5.2 (F001)
  rule: "Amendment supersedes MSA for amended clauses"
  confidence: 0.98
```

---

## Auto-Discovery of Contract Families

When a user adds a document to their workspace, ContractOS automatically
attempts to discover related documents.

### Discovery Signals

| Signal | How Detected | Confidence |
|--------|-------------|------------|
| Explicit reference | "This SOW is governed by MSA dated 2024-01-15 between..." | 0.99 |
| Matching parties + date range | Same buyer + supplier, overlapping dates | 0.85 |
| Document naming convention | "MSA-2024-001", "SOW-2024-001-A" | 0.80 |
| Cross-references in text | "As defined in the Master Agreement..." | 0.90 |
| Amendment markers | "This Amendment No. 2 to the Agreement dated..." | 0.95 |
| File metadata | Stored in same folder, similar creation dates | 0.60 |

### Discovery Protocol

```
When a new document enters the workspace:

1. EXTRACT parties, dates, references, document type
2. SEARCH existing ContractGraph for:
   a. Same parties (normalized via DomainBridge)
   b. Explicit cross-references in text
   c. Naming pattern matches
   d. Temporal proximity (within 2 years by default)
3. RANK candidate relationships by confidence
4. For confidence >= 0.80:
   → Automatically add edge to ContractGraph
   → Notify user: "Detected: this SOW is governed by MSA-2024-001"
5. For confidence 0.50–0.79:
   → Suggest to user: "This might be related to MSA-2024-001. Confirm?"
6. For confidence < 0.50:
   → Do not suggest (too speculative)
```

---

## Graph Queries

The Contract Graph supports these query patterns:

### Family Traversal

```
"Give me the complete contract family for SOW-2024-003"

→ Walk edges: SOW → governs → MSA
                    → is_schedule_of → Schedules
                    → amends → Amendments
                    → is_change_order_of → Change Orders
→ Return: complete family tree with status and effective dates
```

### Effective Terms

```
"What is the effective liability cap?"

→ Collect all facts about "liability" across family
→ Apply PrecedenceResolver
→ Return effective value with provenance
```

### Impact Analysis

```
"If I amend §7.3, what else is affected?"

→ Find all documents that reference §7.3
→ Find all SOWs governed by this MSA
→ Find all bindings that include terms defined in §7.3
→ Return: impact map showing affected documents and clauses
```

### Temporal View

```
"Show me the history of payment terms for this supplier"

→ Collect all contracts with this supplier (via ContractGraph)
→ For each, resolve effective payment terms (via PrecedenceResolver)
→ Order by effective date
→ Return: timeline of payment term evolution
```

---

## Storage

At 1K–10K contracts, the Contract Graph fits comfortably in:

- **SQLite/DuckDB** for local deployment (nodes and edges as relational tables
  with JSON columns for metadata)
- **PostgreSQL** for cloud deployment (with recursive CTE support for graph
  traversal)

No specialized graph database is needed at this scale. The graph is relatively
shallow (typical family depth: 3–5 levels) and narrow (typical family width:
10–30 documents).

If scale demands it later, the edge/node schema maps directly to Neo4j or
similar with zero model changes.
