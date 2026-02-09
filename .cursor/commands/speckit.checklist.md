# /speckit.checklist — Generate Quality Checklist

Generate custom quality checklists that validate requirements completeness, clarity, and consistency — "unit tests for English." Specify the domain after the command (e.g., `ux`, `security`, `api`, `performance`).

## Objective

You are executing the Spec-Driven Development **checklist** command. This generates checklists that test the quality of your requirements, NOT the implementation.

## Critical Concept

Checklists are **UNIT TESTS FOR REQUIREMENTS WRITING**:

**CORRECT** (testing requirements quality):
- "Are visual hierarchy requirements defined with measurable criteria?"
- "Is 'prominent display' quantified with specific sizing/positioning?"
- "Are accessibility requirements specified for all interactive elements?"

**WRONG** (testing implementation):
- "Verify the button clicks correctly"
- "Test error handling works"
- "Confirm the API returns 200"

## Execution

1. Read the full command specification at `.specify/templates/commands/checklist.md` and follow it precisely.
2. Run `bash .specify/scripts/bash/check-prerequisites.sh --json` and parse `FEATURE_DIR`.
3. Ask up to 3 contextual clarifying questions about scope, depth, and audience.
4. Load context: `spec.md`, `plan.md`, `tasks.md` from `FEATURE_DIR`.
5. Generate checklist at `FEATURE_DIR/checklists/[domain].md`.
6. Report: path, item count, and summary.

## Item Format

```
- [ ] CHK### - [Question about requirement quality] [Quality Dimension, Source Reference]
```

Quality dimensions: Completeness, Clarity, Consistency, Measurability, Coverage, Edge Cases.

## Example Types

- `ux.md` — UX requirements quality
- `api.md` — API requirements quality  
- `security.md` — Security requirements quality
- `performance.md` — Performance requirements quality

## Prohibited

- Any item starting with "Verify", "Test", "Confirm" + implementation behavior.
- References to code execution, user actions, system behavior.
