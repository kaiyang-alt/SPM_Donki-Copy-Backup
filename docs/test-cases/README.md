# Functional Test Cases

This folder stores the human-readable functional test specifications for ConnectSphere user stories.

These files are separate from the automated Python tests stored under:

```text
tests/
```

The documentation responsibilities are:

```text
docs/user-stories/<story-name>.md
-> User Story, Acceptance Criteria and requirement scope

docs/test-cases/<story-name>.md
-> human-readable functional test scenarios and AC traceability

tests/
-> automated pytest implementation tests
```

Functional test bodies must not be duplicated inside the user-story file.

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

## Primary AI-Assisted Workflow

The normal entry point is:

```text
docs/implementation/user-story-implementation-prompt.md
```

The developer supplies the assigned story or new feature area and the latest
customer material where relevant. The orchestrator handles reconciliation or
story creation, Human Gate 1, functional-test generation, Human Gate 2,
implementation readiness, Human Gate 3 where required, and implementation,
testing and verification.

The specialised functional-test prompt remains available at:

```text
docs/test-cases/functional-test-case-prompt.md
```

It is normally invoked by the orchestrator after the canonical story and
Acceptance Criteria pass Human Gate 1, but it may also be used independently as
a focused functional-test design tool.

Human review and approval are required before an AI-generated functional test
specification becomes approved implementation input.

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

## Canonical File Rule

```text
EXISTING TEST SPECIFICATION
-> update the canonical file in place

NEW STORY
-> create the corresponding new functional test specification
```

Git history preserves previous versions. Do not create competing versioned
copies unless explicitly approved.
