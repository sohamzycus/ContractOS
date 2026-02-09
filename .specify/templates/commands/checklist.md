---
description: Generate a custom quality checklist for the current feature based on user requirements. Checklists are "unit tests for requirements writing."
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Checklist Purpose: "Unit Tests for English"

**CRITICAL CONCEPT**: Checklists are **UNIT TESTS FOR REQUIREMENTS WRITING** - they validate the quality, clarity, and completeness of requirements in a given domain.

**NOT for verification/testing**:
- NOT "Verify the button clicks correctly"
- NOT "Test error handling works"

**FOR requirements quality validation**:
- "Are visual hierarchy requirements defined for all card types?" (completeness)
- "Is 'prominent display' quantified with specific sizing/positioning?" (clarity)
- "Are hover state requirements consistent across all interactive elements?" (consistency)

## Execution Steps

1. **Setup**: Run `bash .specify/scripts/bash/check-prerequisites.sh --json` from repo root and parse JSON for FEATURE_DIR.

2. **Clarify intent**: Derive up to THREE contextual clarifying questions from the user's phrasing + spec/plan/tasks signals.

3. **Understand user request**: Derive checklist theme, consolidate items, map focus selections.

4. **Load feature context**: Read spec.md, plan.md (if exists), tasks.md (if exists) from FEATURE_DIR.

5. **Generate checklist**: Create `FEATURE_DIR/checklists/[domain].md` following the checklist template structure.

6. **Report**: Output full path to created checklist, item count, and summary.

### Item Structure

Each item should follow this pattern:
- Question format asking about requirement quality
- Focus on what's WRITTEN (or not written) in the spec/plan
- Include quality dimension in brackets [Completeness/Clarity/Consistency/etc.]
- Reference spec section `[Spec §X.Y]` when checking existing requirements
- Use `[Gap]` marker when checking for missing requirements

### ABSOLUTELY PROHIBITED:
- Any item starting with "Verify", "Test", "Confirm", "Check" + implementation behavior
- References to code execution, user actions, system behavior
- Test cases, test plans, QA procedures

### REQUIRED PATTERNS:
- "Are [requirement type] defined/specified/documented for [scenario]?"
- "Is [vague term] quantified/clarified with specific criteria?"
- "Are requirements consistent between [section A] and [section B]?"
