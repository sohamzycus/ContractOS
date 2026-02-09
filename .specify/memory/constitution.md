<!--
Sync Impact Report
  Version change: 0.0.0 → 1.0.0
  Modified principles: N/A (initial creation)
  Added sections:
    - Core Principles (7 principles)
    - Truth Model Governance
    - Architectural Constraints
    - Governance
  Removed sections: N/A
  Templates requiring updates:
    - .specify/templates/plan-template.md — Constitution Check gates align ✅
    - .specify/templates/spec-template.md — no changes needed ✅
    - .specify/templates/tasks-template.md — no changes needed ✅
  Follow-up TODOs: none
-->

# ContractOS Constitution

## Core Principles

### Evidence Before Intelligence

Every claim ContractOS produces MUST trace to source material. No answer,
inference, or recommendation is valid without a provenance chain linking it to
document-grounded facts or declared external knowledge sources.

Rationale: Legal and procurement decisions carry financial and regulatory
consequences. Ungrounded claims are hallucinations, and hallucinations in
legal contexts are liabilities.

### Truth Model Integrity

The four-layer truth model (Fact → Binding → Inference → Opinion) is
non-negotiable. Every system output MUST be typed as exactly one of these
layers. No layer may contradict a higher layer. Opinions MUST never be
persisted as facts or inferences.

Rationale: This separation prevents legal hallucinations from becoming
"truth" in the system. Breaking this model breaks ContractOS.

### Inference Over Extraction

ContractOS MUST reason about what contracts mean, not just what they say.
Extracting text spans is necessary but insufficient. The system MUST combine
facts, bindings, and domain knowledge to derive actionable claims that are
grounded, probabilistic, and explainable.

Rationale: Contracts encode obligations implicitly. A system that only
extracts explicit text fails at the core problem ContractOS exists to solve.

### Auditability By Design

Every answer MUST include: the facts it relies on, the inferences it made,
the domain knowledge it used, the confidence it assigns, and the reasoning
chain connecting them. A legal reviewer MUST be able to verify every step
without accessing source code.

Rationale: Procurement and legal professionals are accountable for decisions.
They cannot rely on a system they cannot audit.

### Repository-Level Reasoning Is First-Class

Cross-contract queries (search, comparison, aggregation, family traversal)
MUST be supported as primary operations, not afterthoughts bolted onto
single-document analysis. The Contract Graph and TrustGraph MUST enable
reasoning across document boundaries.

Rationale: Procurement professionals work across contract portfolios. The
highest-value questions span multiple documents, suppliers, and time periods.

### Configuration Over Code

Deployment model, LLM provider, ontology sources, confidentiality boundaries,
and language support MUST be configuration changes, not architecture changes.
Switching from Claude to GPT, from local to cloud, or from English-only to
multi-language MUST NOT require code modifications to the core reasoning
pipeline.

Rationale: ContractOS serves diverse organizations with different security
postures, technology preferences, and regulatory environments. Architecture
must accommodate this diversity without forking.

### Context Is Persistent

ContractOS MUST remember the user's working context across sessions. Documents
added to a workspace MUST remain in context until explicitly removed. The
system MUST auto-discover related contracts and suggest them. Prior reasoning
sessions MUST be searchable.

Rationale: Procurement professionals work on the same contract families for
weeks or months. Re-establishing context every session destroys productivity
and breaks the "operating system" promise.

## Truth Model Governance

The truth model defined in `spec/truth-model.md` is the kernel of ContractOS.
The following rules are constitutional:

1. **Facts** are immutable, source-addressable, and carry no confidence score.
   Re-extraction of the same document MUST produce the same facts.
2. **Bindings** are deterministic, scoped, and resolved before inference.
   Binding resolution follows: same document → governing document → latest
   amendment → flag as ambiguous.
3. **Inferences** MUST reference supporting facts. Inferences with
   confidence < 0.5 MUST be flagged for human review. Inferences from external
   knowledge MUST declare the source in `domain_sources`.
4. **Opinions** are computed on demand and MUST NOT be persisted. Opinions are
   role-dependent and policy-dependent.
5. **Provenance chains** are mandatory for every system output. No answer
   without a chain.
6. **Confidence scores** MUST be calibrated against expert judgment per the
   evaluation framework in `spec/evaluation.md`. Uncalibrated confidence
   MUST NOT be displayed to users.

## Architectural Constraints

These constraints are derived from the principles and are binding on all
implementation decisions:

1. **Layered architecture**: Interaction → Workspace → Query Planning →
   Agent Orchestration → Tooling → Intelligence Fabric → Data. No layer
   may bypass an adjacent layer.
2. **Agents are stateless**: All persistent state lives in the Workspace,
   TrustGraph, or ContractGraph. Agents receive context, reason, and return
   results.
3. **Tools enforce the truth model**: Every tool output is typed as
   FactResult, BindingResult, InferenceResult, or OpinionResult. Untyped
   outputs are rejected.
4. **The Interaction Layer never reasons**: Word Copilot, CLI, and API are
   display shells. All reasoning happens in the Agent layer.
5. **External knowledge is declared**: The DomainBridge may use external
   ontologies (UNSPSC, geographic databases, etc.) but every external
   resolution MUST carry `source: external` provenance distinct from
   `source: document`.
6. **Contract Graph is the authority for precedence**: When facts from
   different documents conflict, the PrecedenceResolver in the Contract
   Graph determines the effective value. Facts themselves remain immutable.
7. **Scale is deferred, not ignored**: Phase 1 targets 1K–10K contracts with
   local storage (SQLite/DuckDB). Architecture MUST support migration to
   PostgreSQL + vector store without model changes.

## Governance

### Amendment Procedure

1. Any team member may propose a constitutional amendment via pull request
   to `.specify/memory/constitution.md`.
2. Amendments that modify Core Principles require explicit review and
   approval from the project lead.
3. Amendments that add Architectural Constraints require demonstration that
   the constraint is derived from an existing principle.
4. All amendments MUST update the version number per semantic versioning.

### Versioning Policy

- **MAJOR**: Removal or redefinition of a Core Principle, or removal of a
  truth model layer.
- **MINOR**: Addition of a new principle, new architectural constraint, or
  new governance section.
- **PATCH**: Clarifications, wording improvements, or non-semantic changes.

### Compliance Review

Every `/speckit.plan` execution MUST include a Constitution Check gate that
verifies the implementation plan does not violate any principle or constraint.
Violations MUST be either resolved or explicitly justified in the Complexity
Tracking section of the plan.

**Version**: 1.0.0 | **Ratified**: 2025-02-09 | **Last Amended**: 2025-02-09
