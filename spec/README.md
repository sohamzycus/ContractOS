# ContractOS Specification

> The operating system for contract intelligence.

## Document Index

Read in this order:

| # | Document | What It Defines |
|---|----------|----------------|
| 1 | [vision.md](vision.md) | What ContractOS is, why it exists, design principles |
| 2 | [truth-model.md](truth-model.md) | Fact / Binding / Inference / Opinion — the most important file |
| 3 | [architecture.md](architecture.md) | Layered ecosystem: agents, tools, fabric, data |
| 4 | [domain-bridge.md](domain-bridge.md) | How contract text connects to real-world meaning |
| 5 | [contract-graph.md](contract-graph.md) | Contract families as a DAG with precedence |
| 6 | [workspace.md](workspace.md) | Persistent context, reasoning sessions, memory |
| 7 | [evaluation.md](evaluation.md) | Benchmarking, confidence calibration, COBench |
| 8 | [phases.md](phases.md) | Phased delivery roadmap: Phase 1 through 6 |

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| First user | Procurement | Highest volume of cross-contract queries, clearest ROI |
| Document formats | Word (.docx) + PDF | Procurement standard; start with Word Copilot |
| Entry point | In-document Copilot | User stays in their document; ContractOS reasons around them |
| Truth model | 4-layer (Fact/Binding/Inference/Opinion) | Prevents hallucination, enables auditability |
| External knowledge | Allowed, declared, auditable | DomainBridge uses external ontologies but marks provenance |
| Context model | Persistent workspace (like Cursor) | User adds docs once; system remembers and auto-discovers |
| Deployment | Local-first, config-driven | Sensitive legal data; LLM provider is configuration |
| Scale target | 1K–10K contracts (Phase 1–3) | Architecture supports 100K+ but doesn't optimize for it yet |
| Languages | Global (multi-language) | Procurement is international; support from Phase 3 |

## Architecture At a Glance

```
Interaction    →  Word/PDF Copilot · CLI · API
Workspace      →  Persistent context · Auto-discovery · Session memory
Query Planning →  Decompose · Scope · Route
Agents         →  Document · Repository · Clause · Compliance · Draft
Tools          →  FactExtractor · BindingResolver · InferenceEngine · DomainBridge
Fabric         →  TrustGraph · ContractGraph · EmbeddingIndex · DomainStore
Data           →  ContractStore · PolicyStore · OntologyStore · AuditLog
```
