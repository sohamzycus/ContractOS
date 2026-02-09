---
description: Perform a non-destructive cross-artifact consistency and quality analysis across spec.md, plan.md, and tasks.md after task generation.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Identify inconsistencies, duplications, ambiguities, and underspecified items across the three core artifacts (`spec.md`, `plan.md`, `tasks.md`) before implementation. This command MUST run only after `/speckit.tasks` has successfully produced a complete `tasks.md`.

## Operating Constraints

**STRICTLY READ-ONLY**: Do **not** modify any files. Output a structured analysis report.

**Constitution Authority**: The project constitution (`.specify/memory/constitution.md`) is **non-negotiable**. Constitution conflicts are automatically CRITICAL.

## Execution Steps

1. Run `bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` and parse JSON for FEATURE_DIR.

2. Load artifacts: spec.md, plan.md, tasks.md, and constitution.

3. Build semantic models: requirements inventory, user story inventory, task coverage mapping, constitution rule set.

4. Detection passes: Duplication, Ambiguity, Underspecification, Constitution Alignment, Coverage Gaps, Inconsistency.

5. Assign severity: CRITICAL, HIGH, MEDIUM, LOW.

6. Produce compact analysis report with findings table, coverage summary, constitution alignment issues, unmapped tasks, and metrics.

7. Provide next actions and offer remediation suggestions.

## Operating Principles

- **NEVER modify files** (this is read-only analysis)
- **NEVER hallucinate missing sections**
- **Prioritize constitution violations** (always CRITICAL)
- **Report zero issues gracefully** (emit success report with coverage statistics)
