---
description: Execute the implementation planning workflow using the plan template to generate design artifacts.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

1. **Setup**: Run `bash .specify/scripts/bash/setup-plan.sh --json` from repo root and parse JSON for FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH.

2. **Load context**: Read FEATURE_SPEC and `.specify/memory/constitution.md`. Load IMPL_PLAN template (already copied).

3. **Execute plan workflow**: Follow the structure in IMPL_PLAN template to:
 - Fill Technical Context (mark unknowns as "NEEDS CLARIFICATION")
 - Fill Constitution Check section from constitution
 - Evaluate gates (ERROR if violations unjustified)
 - Phase 0: Generate research.md (resolve all NEEDS CLARIFICATION)
 - Phase 1: Generate data-model.md, contracts/, quickstart.md
 - Phase 1: Update agent context by running: `bash .specify/scripts/bash/update-agent-context.sh cursor-agent`
 - Re-evaluate Constitution Check post-design

4. **Stop and report**: Command ends after Phase 2 planning. Report branch, IMPL_PLAN path, and generated artifacts.

## Phases

### Phase 0: Outline & Research

1. Extract unknowns from Technical Context above
2. Generate and dispatch research agents for each unknown
3. Consolidate findings in `research.md`

**Output**: research.md with all NEEDS CLARIFICATION resolved

### Phase 1: Design & Contracts

**Prerequisites:** `research.md` complete

1. Extract entities from feature spec -> `data-model.md`
2. Generate API contracts from functional requirements -> `/contracts/`
3. Agent context update: Run `bash .specify/scripts/bash/update-agent-context.sh cursor-agent`

**Output**: data-model.md, /contracts/*, quickstart.md, agent-specific file

## Key rules

- Use absolute paths
- ERROR on gate failures or unresolved clarifications
