# ContractOS Phased Delivery Roadmap

> Build depth first, then breadth. Each phase is independently valuable.

## Philosophy

Each phase delivers a **usable, valuable product** — not a skeleton that needs
future phases to work. A procurement user benefits from Phase 1 alone. Each
subsequent phase compounds the value.

---

## Phase Overview

```
Phase 1: Single-Contract Intelligence         ← "The Document Brain"
   ↓
Phase 2: Contract Family Reasoning            ← "The Family Lawyer"
   ↓
Phase 3: Repository Search & Discovery        ← "The Knowledge Base"
   ↓
Phase 4: Compliance & Risk                    ← "The Policy Engine"
   ↓
Phase 5: Drafting & Negotiation Support       ← "The Co-Counsel"
   ↓
Phase 6: Enterprise Scale & Analytics         ← "The Operating System"
```

---

## Phase 1: Single-Contract Intelligence

> "I have a contract open. Help me understand it."

### What the User Gets

A procurement professional opens a contract in Word or PDF. They can ask
questions and get grounded, explainable answers about **that document**.

### Capabilities

| Capability | Description |
|-----------|-------------|
| Document parsing | Extract facts from Word (.docx) and PDF documents |
| Entity extraction | Parties, dates, amounts, products, locations |
| Clause identification | Classify sections by type (indemnity, termination, payment, liability, etc.) |
| Binding resolution | Resolve defined terms throughout the document |
| Single-doc Q&A | Answer questions grounded in document evidence |
| Provenance display | Every answer shows source clause and reasoning chain |

### Architecture Components Built

- [ ] Interaction Layer: Word Copilot (basic)
- [ ] FactExtractor (Word parser + PDF parser)
- [ ] BindingResolver
- [ ] InferenceEngine (single-document scope)
- [ ] TrustGraph (local SQLite — facts, bindings, inferences)
- [ ] Truth Model enforcement (Fact / Binding / Inference / Opinion separation)
- [ ] Workspace (basic — single document context with persistence)
- [ ] LLM integration (Claude via API, configurable)
- [ ] COBench v0.1 (20 annotated contracts, 100 single-doc queries)

### Example Interactions

```
User: "Who are the parties to this contract?"
→ Fact extraction: §1.1 identifies "ClientCo Ltd" (buyer) and
  "Dell Technologies" (supplier)

User: "What are the payment terms?"
→ Fact: §5.2 states "Net 90 from invoice date"
→ Binding: "Invoice Date" defined in §1.4 as "date of goods receipt"

User: "Does this contract cover data breach indemnity?"
→ Fact: §12.1 contains indemnification clause
→ Inference: The clause covers "losses arising from unauthorized access
  to Confidential Information" — data breach is a form of unauthorized
  access to confidential information (confidence: 0.85)
→ Provenance: [§12.1 text] + [§1.8 definition of Confidential Information]

User: "What products are covered?"
→ Facts: Schedule A table with 12 line items
→ Presented as structured table with product names, quantities, pricing
```

### Success Criteria

- Fact extraction precision > 93% on COBench v0.1
- Users can ask 5 common procurement questions and get grounded answers
- Every answer includes clickable provenance to source text
- Response time < 5 seconds for cached documents, < 30 seconds for first parse

### Not in Phase 1

- Cross-document reasoning
- Contract family awareness
- Repository search
- DomainBridge (ontological resolution)
- Compliance checking
- Drafting

---

## Phase 2: Contract Family Reasoning

> "This SOW has a governing MSA. Help me understand the full picture."

### What the User Gets

ContractOS now understands that contracts exist in families. When a user opens
a SOW, the system automatically finds the governing MSA, amendments, and
schedules — and reasons across the family.

### New Capabilities (additive to Phase 1)

| Capability | Description |
|-----------|-------------|
| Contract Graph | DAG of contract relationships (MSA → SOW → Amendment) |
| Auto-discovery | Automatically find related documents when one is opened |
| Precedence resolution | Determine effective terms across amendment chains |
| Family-scoped Q&A | Answer questions that require multiple documents |
| Scope escalation | Automatically check governing MSA when answer isn't in SOW |
| Workspace memory | Persistent context across sessions |

### Architecture Components Built

- [ ] ContractGraph (nodes + typed edges in SQLite)
- [ ] Auto-discovery engine (party matching, cross-references, naming patterns)
- [ ] PrecedenceResolver
- [ ] Workspace layer (full — context management, session persistence)
- [ ] ReasoningSession lifecycle (with scope escalation)
- [ ] COBench v0.2 (add 30 contracts in 10 families, 50 cross-doc queries)

### Example Interactions

```
User opens SOW-2024-003:
→ "Found related documents: MSA-2024-001 (governing), Amendment-001,
   Amendment-002, Schedule A, Schedule B"

User: "What are the effective payment terms?"
→ MSA §5.2: Net 90 (fact)
→ Amendment-001 §1: changes to Net 60 (fact)
→ PrecedenceResolver: Amendment supersedes MSA for §5.2
→ Answer: "Net 60, per Amendment-001 (overriding original MSA terms of Net 90)"

User: "What's the liability cap?"
→ SOW has no liability cap (searched, not found)
→ Scope escalation to MSA
→ MSA §14.2: $5M aggregate liability cap
→ Answer: "The liability cap is $5M per §14.2 of the governing MSA.
   The SOW does not define its own cap."
→ Provenance shows the escalation path
```

### Success Criteria

- Auto-discovery finds 80%+ of related documents with confidence > 0.80
- Precedence resolution correct for 90%+ of effective term queries
- Users don't need to manually specify which MSA governs their SOW
- Workspace context persists across sessions with no loss

---

## Phase 3: Repository Search & Discovery

> "Search across all our contracts. Find patterns. Surface knowledge."

### New Capabilities

| Capability | Description |
|-----------|-------------|
| DomainBridge | Ontological resolution (Dell Inspiron → IT Equipment) |
| Embedding index | Vector-based similarity search across repository |
| Repository-level Q&A | "Find all contracts with maintenance clauses for IT equipment" |
| Clause comparison | "Show me termination clauses from similar contracts" |
| Supplier intelligence | "What are all our contracts with Dell?" |
| Multi-language support | Process contracts in multiple languages |

### Architecture Components Built

- [ ] DomainBridge (all three layers: universal, organizational, corpus-derived)
- [ ] EmbeddingIndex (local vector store)
- [ ] RepositoryAgent
- [ ] ClauseAgent
- [ ] SimilarityEngine
- [ ] Multi-language extraction pipeline
- [ ] COBench v0.3 (200 contracts, repository-level queries, domain resolution)

### Example Interactions

```
User: "Find contracts for IT Equipment with maintenance clauses
       across multiple locations"
→ DomainBridge expands "IT Equipment" → includes Dell Inspiron,
  HP EliteBook, Lenovo ThinkPad, etc.
→ Repository search finds 8 contracts
→ Each result shows: which clause, which products, which locations
→ Results ranked by relevance with confidence scores

User: "Show me termination clauses from similar contracts to this one"
→ SimilarityEngine finds 5 most similar contracts
→ ClauseAgent extracts termination clauses from each
→ Side-by-side comparison with current contract's termination clause
→ Highlights differences and unique provisions
```

### Success Criteria

- DomainBridge resolves 85%+ of product/service references correctly
- Repository search returns relevant results for 80%+ of queries
- Sub-5-second response for repository queries on 5K contracts
- Multi-language support for at least English, German, French, Hindi

---

## Phase 4: Compliance & Risk

> "Is this contract compliant? What's missing? What's risky?"

### New Capabilities

| Capability | Description |
|-----------|-------------|
| Policy matching | Compare contract against standard terms |
| Gap analysis | What's in our standard but missing from this contract? |
| Risk flagging | Identify high-risk clauses and missing protections |
| Benchmark comparison | How do terms compare to repository average? |
| ComplianceAgent | Automated compliance checking |

### Architecture Components Built

- [ ] PolicyStore (organization's standard contract templates)
- [ ] ComplianceAgent
- [ ] PolicyMatcher tool
- [ ] Risk scoring framework (configurable per organization)
- [ ] Benchmark computation (from repository data)
- [ ] Opinion layer (fully implemented with role + policy context)

### Example Interactions

```
User: "What's missing from this contract compared to our standard?"
→ PolicyMatcher compares clause-by-clause
→ Gap report:
  - Missing: Force majeure clause (required by standard)
  - Missing: Data processing addendum (required for IT services)
  - Weaker: Indemnity cap ($1M vs. standard $5M)
  - Non-standard: Auto-renewal (our standard requires explicit renewal)

User: "Is this contract high risk?"
→ Opinion (not inference — depends on risk policy):
  - Severity: HIGH
  - Reasons:
    1. No data breach indemnity (policy requires it for IT suppliers)
    2. Unlimited liability for buyer (standard caps at contract value)
    3. 60-day termination notice (standard is 30 days)
```

---

## Phase 5: Drafting & Negotiation Support

> "Help me write better contracts. Learn from our history."

### New Capabilities

| Capability | Description |
|-----------|-------------|
| Clause suggestion | Suggest clause language based on repository precedent |
| Redline generation | Propose changes to bring contract in line with standard |
| Negotiation playbook | "Here's how similar clauses were negotiated before" |
| Template generation | Generate contract templates from repository patterns |
| DraftAgent | AI-assisted clause writing with provenance |

---

## Phase 6: Enterprise Scale & Analytics

> "ContractOS as the organizational memory for all contracts."

### New Capabilities

| Capability | Description |
|-----------|-------------|
| Portfolio analytics | Spend by category, supplier concentration, expiry calendars |
| Trend detection | Shifting terms, emerging risk patterns |
| Audit trail | Complete provenance for every query, answer, and decision |
| Multi-tenant | Confidentiality boundaries between business units |
| API platform | Third-party applications built on ContractOS |
| Horizontal scaling | Support 100K+ contracts |

---

## Phase Dependencies

```
Phase 1 ─────────────────────────────────────────────────┐
  │ Single-contract intelligence                         │
  │ Truth Model, FactExtractor, BindingResolver          │
  ▼                                                      │
Phase 2 ──────────────────────────────────────┐          │
  │ Contract family reasoning                 │          │
  │ ContractGraph, PrecedenceResolver         │          │
  │ Workspace                                 │   All phases
  ▼                                           │   build on
Phase 3 ─────────────────────────┐            │   Phase 1
  │ Repository search            │            │   foundations
  │ DomainBridge, Embeddings     │            │
  ▼                              │            │
Phase 4                          │            │
  │ Compliance & Risk            │            │
  │ PolicyMatcher, Opinions      │            │
  ▼                              │            │
Phase 5                          │            │
  │ Drafting & Negotiation       │            │
  ▼                              │            │
Phase 6 ◄────────────────────────┘────────────┘
  Enterprise Scale
```

Key constraint: **Phase 1 must be solid before anything else.** If fact
extraction and the truth model aren't reliable, everything built on top
collapses.

---

## Timeline Estimates

| Phase | Scope | Estimated Duration |
|-------|-------|-------------------|
| Phase 1 | Single-contract intelligence | 6-8 weeks |
| Phase 2 | Contract family reasoning | 4-6 weeks |
| Phase 3 | Repository search & discovery | 6-8 weeks |
| Phase 4 | Compliance & risk | 4-6 weeks |
| Phase 5 | Drafting & negotiation | 6-8 weeks |
| Phase 6 | Enterprise scale | 8-12 weeks |

These are rough estimates. Phase 1 is the most critical — it establishes the
foundation. Better to spend 10 weeks on a solid Phase 1 than rush it in 4.
