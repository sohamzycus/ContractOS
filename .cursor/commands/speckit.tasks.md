# /speckit.tasks — Generate Task Breakdown

Generate an actionable, dependency-ordered task list from the implementation plan. Tasks are organized by user story for independent implementation and testing.

## Objective

You are executing the Spec-Driven Development **tasks** command. This breaks down the implementation plan into specific, executable tasks.

## Execution

1. Read the full command specification at `.specify/templates/commands/tasks.md` and follow it precisely.
2. Run `bash .specify/scripts/bash/check-prerequisites.sh --json` from repo root and parse `FEATURE_DIR` and `AVAILABLE_DOCS`.
3. Load design documents from `FEATURE_DIR`:
   - **Required**: `plan.md` (tech stack, libraries, structure), `spec.md` (user stories with priorities)
   - **Optional**: `data-model.md`, `contracts/`, `research.md`, `quickstart.md`
4. Execute task generation:
   - Extract tech stack and user stories
   - Map entities and endpoints to user stories
   - Generate tasks organized by user story
   - Generate dependency graph
   - Validate task completeness
5. Write `tasks.md` to `FEATURE_DIR` using `.specify/templates/tasks-template.md` as structure.
6. Report summary: total task count, tasks per story, parallel opportunities, MVP scope.

## Task Format (Required)

```
- [ ] [TaskID] [P?] [Story?] Description with file path
```

- **Checkbox**: Always `- [ ]`
- **Task ID**: T001, T002, T003...
- **[P]**: Only if parallelizable (different files, no dependencies)
- **[Story]**: [US1], [US2], etc. — required for user story phases only

## Phase Structure

- **Phase 1**: Setup (project initialization)
- **Phase 2**: Foundational (blocking prerequisites — MUST complete before user stories)
- **Phase 3+**: User Stories in priority order (P1, P2, P3...)
- **Final Phase**: Polish & Cross-Cutting Concerns

## Next Steps

- `/speckit.analyze` — Cross-artifact consistency analysis (recommended)
- `/speckit.implement` — Execute implementation
