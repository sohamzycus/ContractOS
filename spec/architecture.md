# ContractOS Architecture

> Agents reason. Tools execute. Graphs remember. Evidence grounds everything.

## Architectural Thesis

ContractOS is a **layered, agent-driven ecosystem** where each layer has a
single responsibility and a strict interface contract with adjacent layers.

The system is designed to be:

- **LLM-agnostic** — Claude, GPT, local models, configured per deployment
- **UI-agnostic** — Word Copilot, PDF Copilot, CLI, API are all shells
- **Scale-adaptive** — runs locally for 1K contracts, horizontally for 100K+
- **Plugin-extensible** — Claude knowledge-work-plugins, MCP, custom tools

---

## System Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     INTERACTION LAYER                         │
│              Word Copilot · PDF Copilot · CLI · API          │
│                                                              │
│  Responsibilities: Accept queries, provide context,          │
│  display results, apply edits. NEVER reasons.                │
├──────────────────────────────────────────────────────────────┤
│                     WORKSPACE LAYER                           │
│           WorkspaceManager · ContextMemory · SessionStore    │
│                                                              │
│  Responsibilities: Persistent document context, user         │
│  preferences, reasoning session lifecycle, auto-discovery    │
│  of related contracts. Like Cursor's project context.        │
├──────────────────────────────────────────────────────────────┤
│                 QUERY PLANNING LAYER                          │
│        QueryPlanner · ScopeResolver · SubQueryRouter         │
│                                                              │
│  Responsibilities: Decompose questions, determine scope      │
│  (single-doc / family / repository), plan execution,         │
│  manage partial results and streaming.                        │
├──────────────────────────────────────────────────────────────┤
│              AGENT ORCHESTRATION LAYER                        │
│                                                              │
│   DocumentAgent    — deep single-contract reasoning          │
│   RepositoryAgent  — cross-contract search and aggregation   │
│   ClauseAgent      — clause-level extraction and comparison  │
│   ComplianceAgent  — policy and benchmark comparison         │
│   DraftAgent       — clause suggestion and rewriting         │
│                                                              │
│  Responsibilities: Reason over facts/bindings/inferences,    │
│  call tools, synthesize explanations. Agents do NOT persist  │
│  data directly.                                              │
├──────────────────────────────────────────────────────────────┤
│                    TOOLING LAYER                              │
│                                                              │
│   FactExtractor         — parse documents, extract facts     │
│   BindingResolver       — resolve definitions and terms      │
│   InferenceEngine       — generate inferences from facts     │
│   DomainBridge          — ontological resolution             │
│   SimilarityEngine      — embedding-based contract matching  │
│   PolicyMatcher         — compare against standard terms     │
│   PrecedenceResolver    — determine effective terms across   │
│                           amendment chains                   │
│   ConfidenceCalibrator  — validate confidence scores         │
│                                                              │
│  Responsibilities: Execute deterministic operations.         │
│  Tools enforce the truth model. Every tool output is typed   │
│  as Fact, Binding, Inference, or Opinion.                    │
├──────────────────────────────────────────────────────────────┤
│            CONTRACT INTELLIGENCE FABRIC                       │
│                                                              │
│   TrustGraph     — stores facts, bindings, inferences,       │
│                    provenance chains                          │
│   ContractGraph  — DAG of contract relationships             │
│                    (MSA→SOW→Amendment→Schedule)               │
│   EmbeddingIndex — vector store for similarity search        │
│   DomainStore    — ontology mappings, external knowledge     │
│                                                              │
│  Responsibilities: Persistent memory of the system.          │
│  Enables cross-contract reasoning, similarity, aggregation.  │
├──────────────────────────────────────────────────────────────┤
│                      DATA LAYER                               │
│                                                              │
│   ContractStore   — raw documents (Word, PDF)                │
│   PolicyStore     — organization's standard terms, policies  │
│   OntologyStore   — UNSPSC, CPV, geographic, industry        │
│   AuditLog        — every query, every answer, every         │
│                     reasoning chain                           │
│                                                              │
│  Responsibilities: Durable storage. Source of truth for      │
│  raw materials. Never modified by agents.                    │
└──────────────────────────────────────────────────────────────┘
```

---

## Layer Contracts

### Rule 1: Downward-Only Data Flow for Mutations

Agents call tools. Tools write to the Intelligence Fabric. The Fabric persists
to the Data Layer. No layer reaches up.

```
Interaction → Workspace → QueryPlanner → Agent → Tool → Fabric → Data
                                                    ↑
                                              reads from Fabric
```

### Rule 2: Every Tool Output Is Typed

A tool never returns raw text. It returns one of:

- `FactResult` — with document evidence
- `BindingResult` — with scope and source fact
- `InferenceResult` — with supporting facts, confidence, explanation
- `OpinionResult` — with policy reference, role context, severity

The type determines where and how it is stored.

### Rule 3: Agents Are Stateless Between Sessions

An agent receives a query + context, reasons, calls tools, and returns a
result. It does not maintain state. All state lives in:

- Workspace (user context, document working set)
- TrustGraph (facts, bindings, inferences)
- ContractGraph (document relationships)

### Rule 4: The Interaction Layer Never Reasons

Word Copilot, CLI, API — these are display and input shells. They:

- Accept user queries
- Pass context (current document, cursor position, selection)
- Display results with provenance
- Apply edits (if drafting)

All reasoning happens in the Agent layer. All execution in the Tool layer.

---

## Agent Responsibilities

### DocumentAgent

**Scope**: Single contract (possibly with governing documents)

**Capabilities**:
- Answer questions about a specific contract
- Extract and index facts when a new document enters the workspace
- Resolve bindings within the document
- Generate inferences about obligations, coverage, terms

**Example query**: "Does this contract indemnify the buyer for data breach?"

**Behavior**:
1. Check if document is already indexed in TrustGraph
2. If not, invoke FactExtractor → BindingResolver → store results
3. Search TrustGraph for indemnity-related facts and bindings
4. Check if governing MSA needs to be consulted (scope escalation)
5. Generate inference with confidence and provenance
6. Return answer with full reasoning chain

### RepositoryAgent

**Scope**: Entire contract repository or filtered subset

**Capabilities**:
- Cross-contract search with semantic understanding
- Aggregate analysis (e.g., "How many contracts expire this quarter?")
- Supplier intelligence across contracts
- Pattern detection (common clause types, unusual terms)

**Example query**: "Find all contracts with IT equipment maintenance clauses"

**Behavior**:
1. Parse query to understand intent and entities
2. Use DomainBridge to expand "IT equipment" → product categories
3. Search EmbeddingIndex for semantically similar clauses
4. Filter results through TrustGraph for fact-grounded matches
5. Rank by relevance and confidence
6. Return results with provenance per match

### ClauseAgent

**Scope**: Clause-level operations across one or more contracts

**Capabilities**:
- Clause extraction and classification
- Clause comparison across contracts
- Clause suggestion for drafting
- Missing clause detection (vs. standard template)

**Example query**: "Show me termination clauses from similar contracts that
could apply here"

### ComplianceAgent

**Scope**: Contract vs. policy/standard

**Capabilities**:
- Compare contract terms against organization's standard
- Identify gaps, deviations, and risks
- Generate compliance reports
- Flag non-standard terms

**Example query**: "What's missing from this contract compared to our standard
procurement template?"

### DraftAgent

**Scope**: Clause generation and editing

**Capabilities**:
- Suggest clause language based on precedent
- Rewrite clauses to meet policy requirements
- Generate redline suggestions
- Incorporate learnings from repository

**Example query**: "Rewrite the termination clause to match our standard with
stronger buyer protections"

---

## Tool Specifications

### FactExtractor

**Input**: Raw document (Word/PDF)
**Output**: `[FactResult]`
**Behavior**:
- Parse document structure (headings, paragraphs, tables, lists)
- Extract text spans with precise offsets
- Identify entities (parties, dates, amounts, products, locations)
- Classify sections (definitions, obligations, terms, schedules)
- Deterministic — same input always produces same output

### BindingResolver

**Input**: `[FactResult]` from a document
**Output**: `[BindingResult]`
**Behavior**:
- Identify definition clauses
- Parse "X shall mean Y" patterns
- Resolve assignment clauses
- Build scope mappings
- Deterministic

### InferenceEngine

**Input**: Facts + Bindings + Query context
**Output**: `[InferenceResult]`
**Behavior**:
- Combine facts and bindings to answer questions
- Apply DomainBridge for ontological resolution
- Generate reasoning chains
- Calculate confidence scores
- Non-deterministic (LLM-assisted) — but grounded in facts

### DomainBridge

See `domain-bridge.md` for full specification.

### SimilarityEngine

**Input**: Clause or contract + repository
**Output**: Ranked list of similar items with scores
**Behavior**:
- Embedding-based similarity search
- Structural similarity (clause type matching)
- Entity overlap analysis

### PrecedenceResolver

See `contract-graph.md` for full specification.

---

## Configuration Model

ContractOS is configuration-driven. No architecture change is needed for:

| Dimension | Configuration |
|-----------|--------------|
| LLM provider | `config.llm.provider: claude / openai / local` |
| LLM model | `config.llm.model: claude-sonnet-4-20250514` |
| Deployment mode | `config.deployment: local / cloud / hybrid` |
| Plugin integration | `config.plugins: [claude-knowledge-work]` |
| Ontology sources | `config.domain.ontologies: [unspsc, cpv, custom]` |
| Confidentiality | `config.access.cross_repo: true/false` per repository |
| Language support | `config.languages: [en, de, fr, hi, ...]` |
| Fact extraction pipeline | `config.extraction.pipeline: [docx_parser, pdf_parser, ocr]` |

---

## Deployment Topology

### Local (Phase 1 Default)

```
User's Machine
├── Word/PDF with Copilot extension
├── ContractOS Service (local process)
│   ├── Agent Orchestration
│   ├── Tools
│   └── SQLite/DuckDB (TrustGraph + ContractGraph)
├── Embedding Index (local vector store)
└── LLM API calls (Claude/OpenAI, external)
    OR local model (Ollama, etc.)
```

### Cloud / Enterprise (Future)

```
Client Network
├── Copilot Extensions (Word, PDF, Web)
│
├── ContractOS API Gateway
│   ├── Auth / RBAC
│   ├── Workspace Service
│   └── Query Router
│
├── Agent Cluster
│   ├── DocumentAgent pool
│   ├── RepositoryAgent pool
│   └── ClauseAgent pool
│
├── Intelligence Fabric
│   ├── TrustGraph (PostgreSQL + graph extensions)
│   ├── EmbeddingIndex (Pinecone/Qdrant/pgvector)
│   └── ContractGraph (PostgreSQL)
│
├── Data Layer
│   ├── ContractStore (S3/Azure Blob)
│   ├── PolicyStore
│   └── AuditLog
│
└── LLM Gateway (configurable per client)
```

---

## Security Boundaries

| Boundary | Enforcement |
|----------|------------|
| User can only query contracts they have access to | Workspace-level ACL |
| Cross-repository queries respect confidentiality config | RepositoryAgent checks `config.access.cross_repo` |
| LLM calls never include contracts from other tenants | Query context is scoped to authorized documents |
| Audit log captures every query and response | AuditLog is append-only, tamper-evident |
| Raw documents are never sent to LLM in full | Relevant excerpts only, with fact references |
