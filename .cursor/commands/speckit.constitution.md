# /speckit.constitution — Create or Update Project Constitution

Create or update the project's governing principles and development guidelines that will guide all subsequent development.

## Objective

You are executing the Spec-Driven Development **constitution** command. This creates or updates the project constitution — the foundational principles that govern all decisions during specification, planning, and implementation phases.

## Execution

1. Read the full command specification at `.specify/templates/commands/constitution.md` and follow it precisely.
2. Load the existing constitution template at `.specify/memory/constitution.md`.
3. Identify every placeholder token of the form `[ALL_CAPS_IDENTIFIER]`.
4. Collect/derive values for placeholders from user input or repo context.
5. Draft the updated constitution content — replace every placeholder with concrete text.
6. Propagate consistency across dependent templates (plan, spec, tasks templates).
7. Validate — no remaining unexplained bracket tokens, proper versioning, ISO dates.
8. Write the completed constitution back to `.specify/memory/constitution.md`.
9. Report summary with version, bump rationale, and suggested commit message.

## Key Paths

- Constitution file: `.specify/memory/constitution.md`
- Plan template: `.specify/templates/plan-template.md`
- Spec template: `.specify/templates/spec-template.md`
- Tasks template: `.specify/templates/tasks-template.md`
- Command templates: `.specify/templates/commands/*.md`

## Versioning Rules

- MAJOR: Backward incompatible governance/principle removals or redefinitions
- MINOR: New principle/section added or materially expanded guidance
- PATCH: Clarifications, wording, typo fixes, non-semantic refinements

## Important

- The user might require fewer or more principles than in the template — respect that.
- If critical info is missing, insert `TODO(): explanation`.
- Do not create a new template; always operate on the existing `.specify/memory/constitution.md` file.

## Next Steps

After this command, proceed with `/speckit.specify` to define what you want to build.
