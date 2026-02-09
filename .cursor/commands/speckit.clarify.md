# /speckit.clarify — Clarify Spec Requirements

Identify underspecified areas in the current feature spec by asking up to 5 highly targeted clarification questions and encoding answers back into the spec. **Run BEFORE** `/speckit.plan`.

## Objective

You are executing the Spec-Driven Development **clarify** command. This detects and reduces ambiguity or missing decision points in the active feature specification, then records clarifications directly in the spec file.

## Execution

1. Read the full command specification at `.specify/templates/commands/clarify.md` and follow it precisely.
2. Run `bash .specify/scripts/bash/check-prerequisites.sh --json --paths-only` and parse JSON for `FEATURE_DIR` and `FEATURE_SPEC`.
3. Load the current spec file and perform a structured ambiguity & coverage scan across:
   - Functional Scope & Behavior
   - Domain & Data Model
   - Interaction & UX Flow
   - Non-Functional Quality Attributes
   - Integration & External Dependencies
   - Edge Cases & Failure Handling
   - Constraints & Tradeoffs
   - Terminology & Consistency
   - Completion Signals
4. Generate a prioritized queue of max 5 clarification questions.
5. Ask **ONE question at a time** with a recommended option and reasoning.
6. After each answer: record in `## Clarifications` section and update relevant spec sections.
7. Save the spec file after each integration.
8. Report completion with coverage summary and suggested next command.

## Rules

- Maximum 5 total questions across the session.
- Each question: multiple-choice OR short answer (<=5 words).
- Present ONE question at a time — never reveal future queued questions.
- Respect user early termination signals ("done", "stop", "proceed").
- If no meaningful ambiguities found, say so and suggest proceeding.

## Next Steps

- `/speckit.plan` — Create technical implementation plan
