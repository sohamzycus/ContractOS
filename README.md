# ContractOS

> The operating system for contract intelligence.

ContractOS transforms contracts from static legal documents into executable,
explainable legal knowledge that can be queried, reasoned over, and evolved.

## What It Does

- **Ask questions** about contracts and get grounded, explainable answers
- **Reason across** contract families (MSA → SOW → Amendments)
- **Search repositories** with semantic understanding ("IT Equipment" finds "Dell Inspiron")
- **Detect compliance gaps** against organizational standards
- **Full provenance** — every answer traces back to source evidence

## Architecture

```
Interaction    →  Word/PDF Copilot · CLI · API
Workspace      →  Persistent context · Auto-discovery · Session memory
Agents         →  Document · Repository · Clause · Compliance · Draft
Tools          →  FactExtractor · BindingResolver · InferenceEngine · DomainBridge
Fabric         →  TrustGraph · ContractGraph · EmbeddingIndex
Data           →  ContractStore · PolicyStore · OntologyStore · AuditLog
```

## Truth Model

ContractOS strictly separates four layers of truth:

| Layer | What | Persistence |
|-------|------|------------|
| **Fact** | Directly grounded in contract text | Immutable |
| **Binding** | Explicit semantic mapping (definitions) | Persisted, scoped |
| **Inference** | Derived claim with confidence | Persisted, revisable |
| **Opinion** | Contextual judgment (role/policy-dependent) | Computed on demand |

Breaking this model breaks ContractOS.

## Specification

See [`spec/`](spec/) for the complete ecosystem blueprint:

1. [Vision](spec/vision.md) — What and why
2. [Truth Model](spec/truth-model.md) — The most important file
3. [Architecture](spec/architecture.md) — System layers
4. [DomainBridge](spec/domain-bridge.md) — Ontological resolution
5. [Contract Graph](spec/contract-graph.md) — Contract families
6. [Workspace](spec/workspace.md) — Persistent context
7. [Evaluation](spec/evaluation.md) — Benchmarking
8. [Phases](spec/phases.md) — Delivery roadmap

## Status

**Phase: Specification complete. Implementation not yet started.**
