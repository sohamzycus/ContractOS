# /speckit.analyze — Cross-Artifact Consistency Analysis

Perform a non-destructive cross-artifact consistency and quality analysis across `spec.md`, `plan.md`, and `tasks.md`. Run after `/speckit.tasks`, before `/speckit.implement`. **Read-only — does not modify files.**

## Objective

You are executing the Spec-Driven Development **analyze** command. This identifies inconsistencies, duplications, ambiguities, and underspecified items across the three core artifacts before implementation.

## Execution

1. Read the full command specification at `.specify/templates/commands/analyze.md` and follow it precisely.
2. Run `bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` and parse `FEATURE_DIR`.
3. Load artifacts: `spec.md`, `plan.md`, `tasks.md`, and `.specify/memory/constitution.md`.
4. Build semantic models:
   - Requirements inventory
   - User story/action inventory
   - Task coverage mapping
   - Constitution rule set
5. Run detection passes:
   - **Duplication Detection** — near-duplicate requirements
   - **Ambiguity Detection** — vague terms, unresolved placeholders
   - **Underspecification** — missing outcomes, undefined references
   - **Constitution Alignment** — conflicts are automatically CRITICAL
   - **Coverage Gaps** — requirements with no tasks, tasks with no requirements
   - **Inconsistency** — terminology drift, entity mismatches, ordering conflicts
6. Assign severity: CRITICAL, HIGH, MEDIUM, LOW.
7. Produce compact analysis report with findings table, coverage summary, and metrics.
8. Recommend next actions and offer remediation suggestions.

## Constraints

- **STRICTLY READ-ONLY** — Do NOT modify any files.
- **Constitution is non-negotiable** — conflicts are always CRITICAL.
- Limit to 50 findings total.

## Next Steps

- Fix any CRITICAL issues before proceeding.
- `/speckit.implement` — Execute implementation (if no CRITICAL issues).
