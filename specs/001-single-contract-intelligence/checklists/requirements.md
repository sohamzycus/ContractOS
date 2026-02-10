# Requirements Checklist: Single-Contract Intelligence

## Spec Quality

- [x] Feature has clear, non-overlapping user stories
- [x] Each user story has acceptance scenarios in Given/When/Then format
- [x] Priorities (P1/P2) are assigned with justification
- [x] Edge cases identified and handled
- [x] Success criteria are measurable and technology-agnostic
- [x] Key entities defined with relationships
- [x] No more than 3 NEEDS CLARIFICATION markers (0 present)

## TDD Compliance

- [ ] Every module has unit tests written BEFORE implementation
- [ ] Every user story has integration tests written BEFORE implementation
- [ ] Every API endpoint has contract tests written BEFORE implementation
- [ ] Code coverage ≥ 90%
- [ ] All tests are deterministic (no flaky tests)
- [ ] LLM calls are mocked in unit and integration tests
- [ ] Test fixtures use manually crafted contracts with known entities

## Functional Requirements Coverage

| FR | Description | Unit Test | Integration Test | Contract Test |
|----|------------|-----------|-----------------|---------------|
| FR-001 | Word document parsing | T041 | T050 | T052 |
| FR-002 | PDF document parsing | T042 | T050 | T052 |
| FR-003 | Named entity extraction | T043, T044 | T050 | T052 |
| FR-004 | Clause boundary + classification | T045 | T050 | T052 |
| FR-004a | Clause Type Registry | T045 | T050 | T052 |
| FR-004b | Cross-reference extraction | T046 | T050 | T052 |
| FR-004c | Mandatory fact tracking | T047 | T050 | T052 |
| FR-005 | Table data extraction | T041, T042 | T050 | T052 |
| FR-006 | Binding resolution | T067 | T069 | T070 |
| FR-006a | Entity aliasing | T048 | T051 | T070 |
| FR-007 | TrustGraph persistence | T027 | T104 | — |
| FR-008 | Natural language Q&A | T076, T078 | T082 | T085 |
| FR-009 | Provenance chain | T079 | T097 | T098 |
| FR-010 | Truth model typing | T129 | T130 | T098 |
| FR-011 | Workspace persistence | T103 | T104 | T106 |
| FR-012 | Configurable LLM | T034 | — | T037 |
| FR-013 | Deterministic extraction | T049 | T050 | — |
| FR-014 | 200-page documents | T131 | — | — |
| FR-015 | "Not found" handling | T080 | T084 | T085 |

## User Story Coverage

| US | Description | Unit Tests | Integration Tests | Contract Tests |
|----|------------|-----------|-----------------|---------------|
| US-1 | Fact Extraction (P1) | T041–T049 (9) | T050–T051 (2) | T052 (1) |
| US-2 | Binding Resolution (P1) | T067–T068 (2) | T069 (1) | T070 (1) |
| US-3 | Q&A (P1) | T076–T081 (6) | T082–T084 (3) | T085 (1) |
| US-4 | Provenance Display (P2) | T095–T096 (2) | T097 (1) | T098 (1) |
| US-5 | Workspace Persistence (P2) | T102–T103 (2) | T104–T105 (2) | T106 (1) |

## Success Criteria

- [ ] SC-001: Fact extraction Precision@10 > 93%, Recall@20 > 90%, MRR > 0.85
- [ ] SC-002: Binding resolution captures > 90% of defined terms
- [ ] SC-003: Q&A Correctness@1 > 85%, overall > 80%
- [ ] SC-004: 100% provenance chain coverage (enforced by middleware T101)
- [ ] SC-005: < 5s query; < 30s first parse (verified by T131)
- [ ] SC-006: Confidence calibration error < 10%
- [ ] SC-007: "Not found" accuracy > 90%
- [ ] SC-008: Clause type accuracy > 90%, cross-ref precision > 92%
- [ ] SC-009: Completeness gap detection > 75%
