# Requirements Checklist: Single-Contract Intelligence

## Spec Quality

- [x] Feature has clear, non-overlapping user stories
- [x] Each user story has acceptance scenarios in Given/When/Then format
- [x] Priorities (P1/P2) are assigned with justification
- [x] Edge cases identified and handled
- [x] Success criteria are measurable and technology-agnostic
- [x] Key entities defined with relationships
- [x] No more than 3 NEEDS CLARIFICATION markers (0 present)

## Functional Requirements Coverage

- [ ] FR-001: Word document parsing and fact extraction
- [ ] FR-002: PDF document parsing and fact extraction
- [ ] FR-003: Named entity extraction (parties, dates, amounts, products, locations)
- [ ] FR-004: Clause boundary identification and classification
- [ ] FR-005: Table data extraction with row/column metadata
- [ ] FR-006: Binding resolution from definition clauses
- [ ] FR-007: TrustGraph persistence (local SQLite)
- [ ] FR-008: Natural language Q&A via LLM
- [ ] FR-009: Provenance chain in every answer
- [ ] FR-010: Truth model type classification on all outputs
- [ ] FR-011: Workspace state persistence
- [ ] FR-012: Configurable LLM provider
- [ ] FR-013: Deterministic fact extraction
- [ ] FR-014: Support documents up to 200 pages
- [ ] FR-015: "Not found" with evidence rather than hallucination

## User Story Coverage

- [ ] US-1: Document Ingestion & Fact Extraction (P1)
- [ ] US-2: Binding Resolution (P1)
- [ ] US-3: Single-Document Question Answering (P1)
- [ ] US-4: Provenance Display (P2)
- [ ] US-5: Workspace Persistence (P2)

## Success Criteria

- [ ] SC-001: Fact extraction precision > 93%
- [ ] SC-002: Binding resolution captures > 90% of defined terms
- [ ] SC-003: Q&A correctness > 80% on benchmark
- [ ] SC-004: 100% provenance chain coverage
- [ ] SC-005: < 5s query; < 30s first parse
- [ ] SC-006: Confidence calibration error < 10%
- [ ] SC-007: "Not found" accuracy > 90%
