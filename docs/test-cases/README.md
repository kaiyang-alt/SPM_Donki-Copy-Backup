# Functional Test Cases

This folder stores the human-readable functional test specifications for ConnectSphere user stories.

These files are separate from the automated Python tests stored under:

```text
tests/
```

## Folder Purpose

Use this folder for:

- Functional test-case specifications
- Traceability between test cases and acceptance criteria
- Approved test scenarios used during story implementation and review
- The shared functional test-case design prompt

## File Naming

Each user story should have a corresponding functional test-case file where applicable.

Recommended format:

```text
<story-name>.md
```

Example:

```text
event-change-request.md
```

The corresponding files may therefore be:

```text
docs/user-stories/event-change-request.md
docs/test-cases/event-change-request.md
docs/uml/event-change-request-sequence.md
```

## Shared Test-Case Prompt

Use:

```text
docs/test-cases/functional-test-case-prompt.md
```

to generate or review functional test cases consistently.

Before using the prompt, provide the AI with:

```text
README.md
AGENTS.md
docs/architecture/project_context.md
docs/user-stories/<relevant-story>.md
docs/test-cases/functional-test-case-prompt.md
```

The generated test specification should then be reviewed by a human before being treated as approved.

## Relationship to Automated Tests

```text
docs/test-cases/
= functional test specifications

tests/
= automated pytest code
```

Not every functional test case must necessarily become a separate pytest test.

Automated tests should be added where appropriate during implementation based on the story requirements and application design.

## Story References

The relevant user-story file should reference its functional test-case file.

Example:

```md
## Test Case Reference

`docs/test-cases/event-change-request.md`
```

Functional test cases should remain within the scope of the relevant user story.

Do not use test design to introduce new requirements, database structures, status values, workflows or permissions.
