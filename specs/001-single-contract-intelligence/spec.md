# Feature Specification: Single-Contract Intelligence

**Feature Branch**: `001-single-contract-intelligence`
**Created**: 2025-02-09
**Status**: Draft
**Input**: Phase 1 of ContractOS — enable a procurement professional to open a contract in Word or PDF, ask questions, and receive grounded, explainable answers about that document.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Document Ingestion & Fact Extraction (Priority: P1)

A procurement category manager opens a supplier contract (Word or PDF) in the
Copilot interface. ContractOS parses the document, extracts structured facts
(parties, dates, amounts, products, locations, clause boundaries), and stores
them in the TrustGraph. The user can see what was extracted.

**Why this priority**: Without fact extraction, nothing else works. This is the
foundational data pipeline that every other capability depends on.

**Independent Test**: Upload a 30-page procurement contract. Verify that
parties, dates, monetary values, product names, location names, and clause
headings are extracted with correct character offsets and structural paths.

**Acceptance Scenarios**:

1. **Given** a Word (.docx) procurement contract, **When** the user opens it
   in the Copilot, **Then** the system extracts all entities (parties, dates,
   amounts, products, locations) with precision > 93%.
2. **Given** a PDF procurement contract, **When** the user opens it in the
   Copilot, **Then** the system extracts the same fact types with precision
   > 90% (lower due to PDF parsing complexity).
3. **Given** a contract with tables (pricing schedules, product lists),
   **When** parsed, **Then** each table cell is extracted as a separate fact
   with row/column metadata.
4. **Given** the same document re-parsed, **When** extraction runs again,
   **Then** identical facts are produced (deterministic extraction).

---

### User Story 2 — Binding Resolution (Priority: P1)

After fact extraction, ContractOS identifies definition clauses (e.g.,
"'Service Provider' shall mean Acme Corp") and resolves them as Bindings.
Every defined term is mapped throughout the document so that subsequent
queries use resolved names, not raw defined terms.

**Why this priority**: P1 alongside extraction because bindings transform how
every clause is interpreted. Without binding resolution, the system cannot
correctly attribute obligations to parties.

**Independent Test**: Parse a contract with 10+ defined terms. Verify that
each "X shall mean Y" pattern is captured as a Binding with correct scope.
Verify that queries about "the supplier" resolve to the actual entity name.

**Acceptance Scenarios**:

1. **Given** a contract with a Definitions section containing 10 defined terms,
   **When** BindingResolver runs, **Then** all 10 are captured with correct
   term → resolves_to mappings.
2. **Given** a query "Who is the supplier?", **When** the document defines
   "'Supplier' shall mean Dell Technologies Inc.", **Then** the answer is
   "Dell Technologies Inc." with provenance pointing to the Definitions
   section.
3. **Given** a contract where "Effective Date" is defined as "January 15,
   2024", **When** a user asks "When does this contract start?", **Then** the
   system resolves through the binding and answers with the date + source.

---

### User Story 3 — Single-Document Question Answering (Priority: P1)

A procurement user asks a natural language question about the open contract.
ContractOS searches its TrustGraph for relevant facts and bindings, generates
an inference if needed, and returns a grounded answer with a full provenance
chain.

**Why this priority**: This is the core value proposition — the user asks a
question and gets an answer. Without this, the system is just a parser.

**Independent Test**: Ask 10 common procurement questions against a parsed
contract. Verify each answer references specific clauses and facts. Verify
confidence scores are assigned. Verify provenance chains are navigable.

**Acceptance Scenarios**:

1. **Given** a parsed contract with indemnification clause at §12.1, **When**
   user asks "Does this contract indemnify the buyer for data breach?",
   **Then** the system returns a grounded answer citing §12.1, with confidence
   and reasoning chain.
2. **Given** a parsed contract with payment terms "Net 90" in §5.2, **When**
   user asks "What are the payment terms?", **Then** the system returns
   "Net 90 from invoice date" citing §5.2.
3. **Given** a query whose answer is NOT in the contract, **When** user asks
   "What is the force majeure clause?", **Then** the system responds "No force
   majeure clause found in this contract" with confidence and the sections it
   searched.
4. **Given** a question requiring inference (not direct extraction), **When**
   user asks "Does this contract cover IT equipment?", **Then** the system
   generates an inference citing the products in the item table, with
   confidence < 1.0 and a reasoning chain explaining the inference.

---

### User Story 4 — Provenance Display (Priority: P2)

Every answer the Copilot displays includes an expandable provenance chain.
The user can click on any fact to navigate to its location in the source
document. Confidence indicators are shown. Reasoning chains are readable by
non-technical procurement professionals.

**Why this priority**: P2 because the system can answer questions without
provenance display (P1 handles the reasoning), but provenance is what makes
the answer trustworthy and auditable.

**Independent Test**: Ask a question that produces an inference. Verify the
provenance chain shows: supporting facts with document locations, any bindings
used, confidence score, and a human-readable reasoning chain.

**Acceptance Scenarios**:

1. **Given** an answer with 3 supporting facts, **When** displayed, **Then**
   each fact shows the clause reference, text excerpt, and a clickable link
   to the source location.
2. **Given** an inference answer, **When** displayed, **Then** confidence is
   shown as a visual indicator (e.g., high/medium/low bar), the reasoning
   chain is shown in plain English, and the user can expand/collapse details.
3. **Given** an answer involving a binding, **When** displayed, **Then** the
   binding resolution is shown (e.g., "'Supplier' resolves to 'Dell
   Technologies' per §1.2").

---

### User Story 5 — Workspace Persistence (Priority: P2)

When the user closes and reopens the Copilot, the previously parsed document
is already indexed. Facts and bindings are retrieved from the TrustGraph
without re-extraction. Prior questions and answers are accessible.

**Why this priority**: P2 because the system works without persistence (just
re-parse each time), but persistence is critical for the "operating system"
experience and for sub-5-second response times.

**Independent Test**: Parse a contract, close the Copilot, reopen it with the
same document. Verify that facts are already available, questions answer
instantly, and prior sessions are listed.

**Acceptance Scenarios**:

1. **Given** a previously parsed document, **When** the user reopens it in the
   Copilot, **Then** facts and bindings load from TrustGraph in < 1 second.
2. **Given** a workspace with 3 prior Q&A sessions, **When** the user opens
   the workspace, **Then** session history is displayed with question, answer
   summary, and timestamp.
3. **Given** a document that has changed since last parse, **When** reopened,
   **Then** the system detects the change and offers to re-parse.

---

### Edge Cases

- What happens when a PDF is scanned (image-only, no text layer)? → Return
  an error: "This PDF does not contain extractable text. OCR support is
  planned for a future release."
- What happens when the document has no definitions section? → BindingResolver
  returns zero bindings. Inference engine proceeds with raw terms.
- What happens when the document is in a non-English language? → Phase 1
  supports English only. Non-English documents return: "Language not supported
  in this version. Multi-language support is planned."
- What happens when the LLM API is unreachable? → Fact extraction and binding
  resolution still work (deterministic tools). Inference engine returns:
  "Unable to generate inference — LLM service unavailable. Facts and bindings
  are available."
- What happens when the document is very large (100+ pages)? → Parse in
  chunks. Show progress indicator. Warn if extraction takes > 60 seconds.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST parse Word (.docx) documents and extract structured
  facts (text spans, entities, clauses, table cells, headings, metadata).
- **FR-002**: System MUST parse PDF documents and extract the same fact types,
  with graceful degradation for complex layouts.
- **FR-003**: System MUST identify and extract named entities: parties, dates,
  monetary amounts, product/service names, location names, durations.
- **FR-004**: System MUST identify clause boundaries and classify clause types
  (indemnity, termination, payment, liability, confidentiality, IP, force
  majeure, warranty, SLA, assignment, governing law, penalty, price
  escalation, schedule adherence).
- **FR-004a**: Each classified clause MUST be assigned a type from the Clause
  Type Registry. The registry MUST be configurable (organizations can add
  custom clause types).
- **FR-004b**: System MUST extract cross-references within clauses (references
  to other sections, appendices, schedules, and external documents) and
  resolve them to target clauses where possible.
- **FR-004c**: System MUST track mandatory and optional facts per clause type
  (e.g., termination clause expects notice_period, termination_reasons).
  Missing mandatory facts MUST be flagged as completeness gaps.
- **FR-005**: System MUST extract table data as structured facts with
  row/column metadata.
- **FR-006**: System MUST identify definition clauses and resolve them as
  Bindings with term → resolves_to mappings scoped to the document.
- **FR-006a**: System MUST detect entity aliasing patterns within clauses
  (e.g., "A, hereinafter referred to as 'Buyer'") and capture them as
  Bindings.
- **FR-007**: System MUST persist facts and bindings in a local TrustGraph
  (SQLite) keyed by document ID.
- **FR-008**: System MUST answer natural language questions about a single
  contract by searching the TrustGraph and generating inferences via LLM.
- **FR-009**: Every answer MUST include a provenance chain: supporting facts
  with document locations, bindings used, confidence score, and reasoning
  chain.
- **FR-010**: System MUST classify each output as Fact, Binding, Inference,
  or Opinion per the truth model. No untyped outputs.
- **FR-011**: System MUST persist workspace state (indexed documents, sessions)
  across Copilot restarts.
- **FR-012**: System MUST support configurable LLM provider (Claude API as
  default, switchable via configuration).
- **FR-013**: Fact extraction MUST be deterministic — re-parsing the same
  document MUST produce identical facts.
- **FR-014**: System MUST handle documents up to 200 pages without failure.
- **FR-015**: System MUST return "not found" with searched-sections evidence
  when a query has no answer in the document, rather than hallucinating.

### Key Entities

- **Contract**: A document (Word or PDF) representing a legal agreement.
  Attributes: document_id, title, parties, effective_date, file_path, format.
- **Fact**: An immutable, source-addressable claim extracted from document text.
  Attributes: fact_id, fact_type, value, evidence (with offsets), extraction_method.
- **Clause**: A structured unit of legal meaning within a contract, typed by
  a configurable Clause Type Registry. Contains facts, cross-references, and
  mandatory fact slots. Attributes: clause_id, clause_type, heading,
  section_number, contained_facts, cross_references.
- **CrossReference**: A reference from one clause to another section, appendix,
  or schedule. Attributes: reference_id, source_clause, target_reference,
  target_clause (resolved), effect (modifies, overrides, conditions, etc.).
- **ClauseType**: A registry entry defining what facts a clause type is
  expected to contain (mandatory and optional). Configurable per organization.
- **Binding**: A deterministic semantic mapping from a defined term to its
  resolution. Attributes: binding_id, term, resolves_to, source_fact_id, scope.
- **Inference**: A probabilistic derived claim. Attributes: inference_id, claim,
  supporting_facts, confidence, reasoning_chain.
- **Workspace**: A persistent user context containing active documents, indexed
  knowledge, and session history.
- **ReasoningSession**: A single query lifecycle — from question to provenance-
  backed answer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Fact extraction Precision@10 > 93% and Recall@20 > 90% on a
  benchmark of 20 procurement contracts (measured by entity, clause boundary,
  and table cell accuracy). MRR > 0.85.
- **SC-002**: Binding resolution captures > 90% of defined terms in contracts
  with a Definitions section, including entity aliasing patterns.
- **SC-003**: Q&A answers are rated "correct" or "partially correct" by a
  procurement professional for > 80% of 50 benchmark questions. Correctness@1
  (top-ranked answer) > 85%.
- **SC-004**: Every answer includes a provenance chain with at least one
  source-document citation (100% — hard requirement). Supporting fact
  Precision@5 > 90%.
- **SC-005**: Response time < 5 seconds for questions on a previously parsed
  document; < 30 seconds for first parse of a 30-page document.
- **SC-006**: Confidence calibration error < 10% (stated confidence vs. actual
  correctness correlation).
- **SC-007**: The system correctly returns "not found" (rather than hallucinating)
  for > 90% of questions whose answers do not exist in the document.
- **SC-008**: Clause type classification accuracy > 90%. Cross-reference
  extraction precision > 92%. Mandatory fact Recall@N > 85% per clause type.
- **SC-009**: Completeness gap detection (missing mandatory facts) correctly
  flagged for > 75% of actual gaps in benchmark contracts.
