# /speckit.implement — Execute Implementation

Execute all tasks and build the feature according to the implementation plan. Processes `tasks.md` phase by phase, respecting dependencies.

## Objective

You are executing the Spec-Driven Development **implement** command. This reads the task breakdown and executes each task in order, building the entire feature.

## Execution

1. Read the full command specification at `.specify/templates/commands/implement.md` and follow it precisely.
2. Run `bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root.
3. Check checklists status (if `FEATURE_DIR/checklists/` exists):
   - If any checklist is incomplete → STOP and ask the user whether to proceed.
   - If all pass → continue automatically.
4. Load context: `tasks.md` (required), `plan.md` (required), plus optional: `data-model.md`, `contracts/`, `research.md`, `quickstart.md`.
5. Create/verify ignore files (`.gitignore`, `.dockerignore`, etc.) based on tech stack.
6. Parse `tasks.md` and extract phases, dependencies, execution order.
7. Execute phase by phase:
   - **Setup first**: Project structure, dependencies, configuration
   - **Tests before code**: If TDD was requested
   - **Core development**: Models, services, endpoints
   - **Integration**: Database, middleware, logging
   - **Polish**: Unit tests, performance, documentation
8. Mark completed tasks as `[X]` in `tasks.md`.
9. Report final status with summary of completed work.

## Execution Rules

- Complete each phase before moving to the next.
- Respect task dependencies — sequential tasks in order.
- Parallel tasks `[P]` can run together.
- Tasks affecting the same files must run sequentially.
- Halt on non-parallel task failure.

## Prerequisites

Requires `tasks.md` to exist. If missing, run `/speckit.tasks` first.
