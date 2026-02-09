# /speckit.specify — Create Feature Specification

Define what you want to build by creating a feature specification from a natural language description. Focus on the **WHAT** and **WHY**, not the tech stack.

## Objective

You are executing the Spec-Driven Development **specify** command. This creates a new feature branch, directory, and specification document from a natural language feature description.

## Execution

1. Read the full command specification at `.specify/templates/commands/specify.md` and follow it precisely.
2. Generate a concise short name (2-4 words) for the feature branch.
3. Find the highest feature number across local branches, remote branches, and `specs/` directories.
4. Create the feature branch and directory by running:
   ```bash
   bash .specify/scripts/bash/create-new-feature.sh --json --number <N+1> --short-name "<name>" "<Feature description>"
   ```
5. Parse the JSON output for `BRANCH_NAME` and `SPEC_FILE` paths.
6. Load `.specify/templates/spec-template.md` for required sections.
7. Parse user description: extract actors, actions, data, constraints.
8. Fill in: User Scenarios & Testing, Functional Requirements, Success Criteria, Key Entities.
9. Write the specification to `SPEC_FILE`.
10. Validate spec quality and create `FEATURE_DIR/checklists/requirements.md`.
11. Report completion with branch name, spec file path, and readiness for next phase.

## Guidelines

- Focus on **WHAT** users need and **WHY** — avoid HOW (no tech stack, APIs, code structure).
- Written for business stakeholders, not developers.
- Maximum 3 `[NEEDS CLARIFICATION]` markers.
- Success criteria must be measurable, technology-agnostic, user-focused, verifiable.
- DO NOT embed checklists in the spec itself.

## Next Steps

- `/speckit.clarify` — Clarify underspecified areas (recommended before planning)
- `/speckit.plan` — Create technical implementation plan
