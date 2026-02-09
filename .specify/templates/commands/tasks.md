---
description: Generate an actionable, dependency-ordered tasks.md for the feature based on available design artifacts.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

1. **Setup**: Run `bash .specify/scripts/bash/check-prerequisites.sh --json` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute.

2. **Load design documents**: Read from FEATURE_DIR:
 - **Required**: plan.md (tech stack, libraries, structure), spec.md (user stories with priorities)
 - **Optional**: data-model.md (entities), contracts/ (API endpoints), research.md (decisions), quickstart.md (test scenarios)

3. **Execute task generation workflow**:
 - Load plan.md and extract tech stack, libraries, project structure
 - Load spec.md and extract user stories with their priorities (P1, P2, P3, etc.)
 - If data-model.md exists: Extract entities and map to user stories
 - If contracts/ exists: Map endpoints to user stories
 - Generate tasks organized by user story
 - Generate dependency graph showing user story completion order
 - Validate task completeness

4. **Generate tasks.md**: Use `.specify/templates/tasks-template.md` as structure, fill with:
 - Phase 1: Setup tasks (project initialization)
 - Phase 2: Foundational tasks (blocking prerequisites)
 - Phase 3+: One phase per user story (in priority order)
 - Final Phase: Polish & cross-cutting concerns

5. **Report**: Output path to generated tasks.md and summary.

## Task Generation Rules

**CRITICAL**: Tasks MUST be organized by user story to enable independent implementation and testing.

### Checklist Format (REQUIRED)

Every task MUST strictly follow this format:

```text
- [ ] [TaskID] [P?] [Story?] Description with file path
```

**Format Components**:
1. **Checkbox**: ALWAYS start with `- [ ]`
2. **Task ID**: Sequential number (T001, T002, T003...)
3. **[P] marker**: Include ONLY if task is parallelizable
4. **[Story] label**: REQUIRED for user story phase tasks only (e.g., [US1], [US2])
5. **Description**: Clear action with exact file path
