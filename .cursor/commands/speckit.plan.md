# /speckit.plan — Create Technical Implementation Plan

Create a technical implementation plan with your chosen tech stack and architecture. Generates research, data model, API contracts, and quickstart docs.

## Objective

You are executing the Spec-Driven Development **plan** command. This takes the feature specification and produces a detailed technical implementation plan.

## Execution

1. Read the full command specification at `.specify/templates/commands/plan.md` and follow it precisely.
2. Run `bash .specify/scripts/bash/setup-plan.sh --json` from repo root and parse JSON for `FEATURE_SPEC`, `IMPL_PLAN`, `SPECS_DIR`, `BRANCH`.
3. Load context: read `FEATURE_SPEC` and `.specify/memory/constitution.md`. Load the `IMPL_PLAN` template (already copied by the script).
4. Execute plan workflow:
   - Fill Technical Context (mark unknowns as "NEEDS CLARIFICATION")
   - Fill Constitution Check section from constitution
   - Evaluate gates (ERROR if violations unjustified)
   - **Phase 0**: Generate `research.md` — resolve all NEEDS CLARIFICATION items
   - **Phase 1**: Generate `data-model.md`, `contracts/`, `quickstart.md`
   - **Phase 1**: Update agent context: `bash .specify/scripts/bash/update-agent-context.sh cursor-agent`
   - Re-evaluate Constitution Check post-design
5. Stop and report: branch, plan path, and generated artifacts.

## Generated Artifacts

| File | Description |
|------|-------------|
| `plan.md` | Technical implementation plan |
| `research.md` | Phase 0: Research findings and decisions |
| `data-model.md` | Phase 1: Entity definitions and relationships |
| `contracts/` | Phase 1: API specifications |
| `quickstart.md` | Phase 1: Integration scenarios |

## Next Steps

- `/speckit.tasks` — Generate actionable task breakdown
