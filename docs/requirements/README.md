# Requirements Management

This folder contains shared guidance for managing changing ConnectSphere
requirements and, where the team later chooses, customer-release references.
Individual story acceptance criteria remain in their canonical user-story
files.

## Source-of-Truth Priority

1. Latest confirmed customer clarification
2. Latest customer release/change
3. Earlier confirmed customer clarifications
4. Original customer briefing
5. Approved User Story / Acceptance Criteria
6. Approved Functional Test Specification
7. Shared project context / architecture
8. Current implementation / prototype

A newer confirmed customer requirement overrides an older requirement where
they conflict. Existing code, prototype behaviour or passing tests do not
override confirmed customer requirements.

## Documentation Responsibilities

| Document | Responsibility |
| --- | --- |
| `README.md` | Repository overview, setup and navigation |
| `AGENTS.md` | Development and AI-agent guardrails |
| `docs/requirements/README.md` | Requirement precedence and customer-change process |
| `docs/architecture/project_context.md` | Current reconciled shared project baseline |
| `docs/architecture/database_schema.md` | Current approved/documented database structure |
| `docs/user-stories/<story-name>.md` | Approved story-specific requirement scope |
| `docs/test-cases/<story-name>.md` | Approved functional test scenarios and Acceptance Criterion traceability |
| `docs/test-cases/functional-test-case-prompt.md` | AI functional-test procedure |
| `docs/implementation/user-story-implementation-prompt.md` | AI implementation and orchestration procedure |

Current database limitations do not override newer confirmed customer
requirements. If the current architecture cannot support an approved
requirement, that is an implementation dependency to flag later, not a reason
to weaken the requirement.

## Handling a New Customer Release

The normal AI-assisted entry point is
`docs/implementation/user-story-implementation-prompt.md`. It orchestrates the
documented human approval gates for story/Acceptance Criteria, functional tests
and any required shared-architecture change.

```text
New or updated customer requirement
-> identify affected existing stories
-> identify genuinely new stories
-> agent reconciles or creates the canonical story file
-> human approves the story and acceptance criteria
-> agent generates or updates the functional test specification
-> human approves the tests
-> implementation-readiness audit
-> flag shared database, RLS or architecture dependencies where required
-> team approval
-> implementation, testing and Pull Request
```

## Existing vs New Stories

For an existing story, update its canonical file in place; Git preserves its
version history. For a genuinely new capability, create one new canonical story
file.

Do not create `-v2`, `-final`, `-latest` or `-new` variants unless specifically
approved. Apply the same principle to functional test specifications.

## Shared Architecture Dependencies

Requirement reconciliation must not weaken customer requirements merely to fit
the current database. Potential impacts to schema, RLS, roles, constraints,
statuses, notification routing or shared workflow must first be flagged.

Detailed feasibility is assessed during implementation. If a shared change is
required, stop before inventing or applying an unapproved schema, RLS or shared
design change.

## Ownership Boundaries

- The story owner owns reconciliation, implementation and testing for their
  story.
- Cross-story impacts must be flagged.
- Do not silently take over another developer's story.
- Shared architecture decisions require team agreement.
