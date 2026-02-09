---
description: Create or update the feature specification from a natural language feature description.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

The text the user typed after the command **is** the feature description. Assume you always have it available in this conversation. Do not ask the user to repeat it unless they provided an empty command.

Given that feature description, do this:

1. **Generate a concise short name** (2-4 words) for the branch:
 - Analyze the feature description and extract the most meaningful keywords
 - Create a 2-4 word short name that captures the essence of the feature
 - Use action-noun format when possible (e.g., "add-user-auth", "fix-payment-bug")
 - Preserve technical terms and acronyms (OAuth2, API, JWT, etc.)

2. **Create the feature branch and directory**:
 a. Find the highest feature number across local branches, remote branches, and specs directories.
 b. Use N+1 for the new branch number (zero-padded to 3 digits).
 c. Run: `bash .specify/scripts/bash/create-new-feature.sh --json --number N+1 --short-name "your-short-name" "Feature description"`
 d. Parse JSON output for BRANCH_NAME and SPEC_FILE paths.

 **IMPORTANT**:
 - Check all three sources (remote branches, local branches, specs directories) to find the highest number
 - Only run this script once per feature
 - The JSON output will contain BRANCH_NAME and SPEC_FILE paths

3. Load `.specify/templates/spec-template.md` to understand required sections.

4. Follow this execution flow:
 1. Parse user description from Input. If empty: ERROR "No feature description provided"
 2. Extract key concepts from description. Identify: actors, actions, data, constraints
 3. For unclear aspects:
 - Make informed guesses based on context and industry standards
 - Only mark with [NEEDS CLARIFICATION: specific question] if the choice significantly impacts feature scope
 - **LIMIT: Maximum 3 [NEEDS CLARIFICATION] markers total**
 4. Fill User Scenarios & Testing section
 5. Generate Functional Requirements (each must be testable)
 6. Define Success Criteria (measurable, technology-agnostic outcomes)
 7. Identify Key Entities (if data involved)

5. Write the specification to SPEC_FILE using the template structure.

6. **Specification Quality Validation**: Validate against quality criteria and create `FEATURE_DIR/checklists/requirements.md`.

7. Report completion with branch name, spec file path, checklist results, and readiness for next phase (`/speckit.clarify` or `/speckit.plan`).

## General Guidelines

- Focus on **WHAT** users need and **WHY**.
- Avoid HOW to implement (no tech stack, APIs, code structure).
- Written for business stakeholders, not developers.
- DO NOT create any checklists that are embedded in the spec. That will be a separate command.

### Success Criteria Guidelines

Success criteria must be:
1. **Measurable**: Include specific metrics (time, percentage, count, rate)
2. **Technology-agnostic**: No mention of frameworks, languages, databases, or tools
3. **User-focused**: Describe outcomes from user/business perspective
4. **Verifiable**: Can be tested/validated without knowing implementation details
