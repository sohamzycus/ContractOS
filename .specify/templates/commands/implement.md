---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

1. Run `bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute.

2. **Check checklists status** (if FEATURE_DIR/checklists/ exists):
 - Scan all checklist files in the checklists/ directory
 - If any checklist is incomplete, STOP and ask user whether to proceed
 - If all checklists are complete, automatically proceed

3. Load and analyze the implementation context:
 - **REQUIRED**: Read tasks.md for the complete task list and execution plan
 - **REQUIRED**: Read plan.md for tech stack, architecture, and file structure
 - **IF EXISTS**: Read data-model.md, contracts/, research.md, quickstart.md

4. **Project Setup Verification**:
 - Create/verify ignore files based on actual project setup (.gitignore, .dockerignore, etc.)

5. Parse tasks.md structure and extract task phases, dependencies, and details.

6. Execute implementation following the task plan:
 - **Phase-by-phase execution**: Complete each phase before moving to the next
 - **Respect dependencies**: Run sequential tasks in order, parallel tasks [P] can run together
 - **File-based coordination**: Tasks affecting the same files must run sequentially
 - **Validation checkpoints**: Verify each phase completion before proceeding

7. Implementation execution rules:
 - **Setup first**: Initialize project structure, dependencies, configuration
 - **Tests before code**: If tests are requested, write tests for contracts, entities, and integration scenarios
 - **Core development**: Implement models, services, CLI commands, endpoints
 - **Integration work**: Database connections, middleware, logging, external services
 - **Polish and validation**: Unit tests, performance optimization, documentation

8. Progress tracking and error handling:
 - Report progress after each completed task
 - For completed tasks, mark the task off as [X] in the tasks file
 - Halt execution if any non-parallel task fails

9. Completion validation:
 - Verify all required tasks are completed
 - Check that implemented features match the original specification
 - Validate that tests pass and coverage meets requirements
 - Report final status with summary of completed work

Note: This command assumes a complete task breakdown exists in tasks.md. If tasks are incomplete or missing, suggest running `/speckit.tasks` first.
