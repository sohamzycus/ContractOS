---
description: Identify underspecified areas in the current feature spec by asking up to 5 highly targeted clarification questions and encoding answers back into the spec.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

Goal: Detect and reduce ambiguity or missing decision points in the active feature specification and record the clarifications directly in the spec file.

Note: This clarification workflow is expected to run (and be completed) BEFORE invoking `/speckit.plan`. If the user explicitly states they are skipping clarification, you may proceed but must warn that downstream rework risk increases.

Execution steps:

1. Run `bash .specify/scripts/bash/check-prerequisites.sh --json --paths-only` from repo root. Parse JSON for FEATURE_DIR, FEATURE_SPEC.

2. Load the current spec file. Perform a structured ambiguity & coverage scan using this taxonomy:
 - Functional Scope & Behavior
 - Domain & Data Model
 - Interaction & UX Flow
 - Non-Functional Quality Attributes
 - Integration & External Dependencies
 - Edge Cases & Failure Handling
 - Constraints & Tradeoffs
 - Terminology & Consistency
 - Completion Signals

3. Generate a prioritized queue of candidate clarification questions (maximum 5). Each question must be answerable with either a short multiple-choice selection or a one-word/short-phrase answer.

4. Sequential questioning loop (interactive):
 - Present EXACTLY ONE question at a time
 - For multiple-choice questions, provide a recommended option with reasoning
 - After user answers, validate and record
 - Stop when all critical ambiguities resolved, user signals completion, or 5 questions asked

5. Integration after EACH accepted answer:
 - Maintain `## Clarifications` section in spec
 - Apply clarification to appropriate section(s) of spec
 - Save spec file after each integration

6. Validation after each write.

7. Write updated spec back to FEATURE_SPEC.

8. Report completion with number of questions asked, path to updated spec, sections touched, and coverage summary.

Behavior rules:
- Never exceed 5 total asked questions
- If no meaningful ambiguities found, respond accordingly and suggest proceeding
- Respect user early termination signals
