# Requirements Management

This folder contains shared guidance for managing changing ConnectSphere
requirements and, where the team later chooses, customer-release references.
Individual story acceptance criteria remain in their canonical user-story
files.

## Source-of-Truth Priority

1. Latest confirmed customer clarification
2. Latest customer release or change
3. Earlier confirmed customer clarifications
4. Original customer briefing
5. Approved User Story and Acceptance Criteria
6. Approved Functional Test Specification
7. Shared project context and architecture
8. Current implementation or prototype

A newer confirmed customer requirement overrides an older requirement where
they conflict. Existing code or passing tests do not override confirmed
customer requirements.

## Handling a New Customer Release

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
