# ConnectSphere Primary AI Story Workflow

This is the primary ConnectSphere AI-assisted workflow for taking one assigned
story or capability from customer material through an implementation-ready,
tested and committed result.

A developer may provide either:

- the latest customer release or clarification material and an existing
  assigned story name/path; or
- the latest customer release or clarification material and a newly assigned
  capability that does not yet have a story file.

The AI agent is responsible for orchestrating the complete staged workflow for
that one assignment. The developer should not need to paste separate prompts at
each stage. The agent must read the repository prompt and guidance files itself.

The workflow is:

```text
Customer material
-> story reconciliation or creation
-> Human Gate 1: story and Acceptance Criterion approval
-> functional-test generation or update
-> Human Gate 2: functional-test approval
-> implementation-readiness, UML review and schema/RLS audit
-> Human Gate 3: shared-architecture approval, when required
-> implementation
-> automated tests
-> traceability
-> project health
-> commit
```

Work on only one assigned story/capability. Follow `AGENTS.md` throughout.

A customer release may affect several stories, but this workflow does not
recursively take ownership of them. Perform blast-radius analysis, record the
dependency, and hand each affected story to its owner. Continue beyond
reconciliation only for the currently assigned story or for a shared change
that the team has explicitly assigned and approved as shared work.

Use risk-proportional depth. Low-risk story work should not be forced through
database, concurrency or architecture design that it does not require. Human
Gate 3 exists only when a genuine shared schema, RLS, status, role, constraint
or workflow decision is needed.

---

# Phase 0 - Working Tree and Input Check

Before changing anything:

1. Confirm the current Git branch.
2. Inspect `git status`.
3. Detect unrelated uncommitted or untracked work.

If unrelated working-tree changes exist, stop and report them. Do not overwrite,
stage, revert, move or commit another developer's work.

Identify:

- the assigned existing story name/path, or the newly assigned capability; and
- the latest customer material supplied in the current session, if any.

Customer material supplied through the current AI session may be used as
requirement evidence without first being committed to the repository. Do not
create repository copies unless the developer explicitly asks for that work.

---

# Phase 1 - Requirement Reconciliation

Read before editing:

- `docs/requirements/README.md`
- `README.md`
- `AGENTS.md`
- `docs/architecture/project_context.md`
- the relevant existing story, if one exists
- its existing functional test specification, if one exists
- relevant customer material supplied in the session
- relevant UML, where applicable
- repository implementation only as supporting context

Follow the canonical requirement precedence in
`docs/requirements/README.md`. Do not reproduce or invent a competing
source-of-truth hierarchy.

Existing code, prototype behaviour, passing tests and current database
limitations are evidence about the implementation, not authority to weaken a
newer confirmed customer requirement.

## Existing Story Classification

For an existing story, determine and explain whether it is:

- KEEP
- MODIFY
- PARTIALLY SUPERSEDED
- REWRITE
- RETIRE / REPLACE

Use this canonical-file rule:

```text
EXISTING STORY
-> update the existing canonical file in place

NEW CAPABILITY
-> create one new canonical story file
```

Do not create `-v2`, `-final`, `-new` or `-latest` copies. Git provides version
history.

## Phase 1 Output - Canonical Story File

Generate or update:

```text
docs/user-stories/<story-name>.md
```

Use the canonical guidance in `docs/user-stories/README.md`. Include, where
applicable:

- User Story
- Acceptance Criteria
- Relevant Customer Clarifications
- Preconditions / Dependencies
- Test Case Reference
- Relevant UML Reference
- Implementation Notes
- Requirement Revision note

Do not embed full functional test cases in the story file.

At this phase:

- flag possible schema, RLS, role, status, constraint, notification or shared
  workflow impacts;
- do not perform detailed schema design;
- do not weaken the requirement to fit the current architecture;
- do not modify runtime code or pytest tests.

Present a concise reconciliation summary covering:

- unchanged requirements
- changed requirements
- removed or superseded requirements
- new requirements
- cross-story impacts
- potential shared dependencies
- genuinely unresolved questions

## Human Gate 1 - Story and Acceptance Criteria Approval

After generating or updating the story, stop.

Do not generate functional tests, implement code, change schema/RLS, write
pytest tests or commit. Wait for explicit developer approval. Silence is not
approval.

Examples of acceptable approval include:

- `Story approved, continue`
- `AC approved, proceed`
- an equivalent explicit instruction

If revisions are requested, update the same canonical story file, present the
revised summary and stop for approval again.

---

# Phase 2 - Functional Test Specification

Begin only after Human Gate 1 is explicitly approved.

Read and follow:

```text
docs/test-cases/functional-test-case-prompt.md
```

Inspect the canonical specification:

```text
docs/test-cases/<story-name>.md
```

Apply these rules:

```text
File does not exist
-> create it

Existing tests remain valid
-> preserve them

Approved behaviour changed
-> update affected tests

Behaviour was removed or superseded
-> remove or replace obsolete tests

Approved behaviour lacks coverage
-> add tests where required
```

Do not create versioned copies. Preserve stable test IDs where practical.
Maintain explicit traceability from Acceptance Criteria to functional test
cases.

## Human Gate 2 - Functional Test Approval

After generating or updating the specification, report:

- tests added
- tests modified
- tests removed
- Acceptance Criterion coverage
- implementation dependencies flagged
- open requirement questions, if any

Then stop. Do not implement runtime code, modify schema/RLS, write pytest tests
or commit. Wait for explicit approval such as `Functional tests approved,
continue` or an equivalent instruction.

If revisions are requested, update the same canonical test specification and
stop for approval again.

---

# Phase 3 - Implementation Readiness Audit

Begin only after Human Gate 2 is explicitly approved.

Inspect all relevant:

- routes and services
- frontend files
- automated pytest files
- Flask application or blueprint registration
- `docs/architecture/database_schema.md`
- constraints and status assumptions
- RLS and permission assumptions
- authentication
- notification dependencies
- duplicate or legacy implementations
- shared files affected by the story

Search the repository for relevant route paths, function names, table/column
names, status strings, business-rule wording, obsolete tests and duplicate
implementations.

## UML Rule

UML is supporting design documentation, not a requirement source. It is not
mandatory for every story.

- Inspect existing relevant UML where applicable.
- Stale UML must never override approved requirements; flag any UML that
  conflicts with the approved story or design.
- Reuse valid UML where possible.
- Create or update UML only when it materially helps explain multi-actor
  interactions, important sequencing, alternative or exception flows, state
  transitions, non-obvious component/service interaction, or an approved shared
  architecture change.
- Prefer just-enough UML. Sequence diagrams are appropriate for
  interaction-heavy workflows.
- Do not duplicate `docs/architecture/database_schema.md` in UML.
- If UML represents a Human Gate 3 shared architecture decision, update it only
  after that design is approved.
- Story-level UML that does not alter shared architecture may be updated after
  the relevant story and functional-test requirements are approved.
- Keep UML consistent with the final approved implementation.

Do not introduce a separate UML approval gate.

For every approved Acceptance Criterion classify readiness as one or more of:

- READY WITH CURRENT ARCHITECTURE
- REQUIRES SHARED SCHEMA CHANGE
- REQUIRES RLS / PERMISSION CHANGE
- REQUIRES STATUS / CONSTRAINT CHANGE
- REQUIRES SHARED ROLE CHANGE
- REQUIRES SHARED WORKFLOW DECISION
- REQUIRES ANOTHER STORY / DEPENDENCY

## Schema and RLS Principle

The current database must not steer or weaken an approved customer requirement.
If approved behaviour cannot be represented correctly, do not:

- overload an unrelated column;
- hard-code fake state;
- store required persistent data only in frontend state;
- invent an unsupported status;
- bypass RLS;
- create a hidden workaround; or
- silently omit the Acceptance Criterion.

Report each limitation using:

```text
Requirement:
<approved behaviour>

Current limitation:
<current schema, RLS or shared limitation>

Minimum shared change required:
<high-level minimum change>

Affected areas:
<tables, policies, services and stories>

Can unaffected implementation proceed independently?
YES / PARTIALLY / NO
```

## Human Gate 3 - Shared Architecture Approval

This gate is required if any shared schema, RLS, status, role, constraint or
workflow change is needed. Otherwise, record that no shared change is required
and continue to Phase 4.

When the gate is required, stop before implementing dependent behaviour.
Prepare a concise proposal that the developer can forward directly to the team:

1. **Requirement affected** - identify the approved Acceptance Criterion or
   customer requirement.
2. **Current limitation** - explain why the current schema, RLS or shared
   architecture cannot support it correctly.
3. **Proposed minimum shared change** - state the smallest required change
   without redesigning unrelated architecture.
4. **Rationale** - explain why the change is necessary and why a workaround
   would be incorrect or unsafe.
5. **Affected areas** - list tables, columns, constraints, RLS, roles, services,
   stories and tests.
6. **Risks / compatibility impact** - identify existing behaviour, migration or
   data concerns.
7. **Cross-story impact** - identify other developers or stories that may
   depend on the shared change.

Wait for the developer to return with the team's explicit decision.

### Rejected or Modified Proposal

If rejected:

- do not implement the proposed shared change;
- identify the blocked Acceptance Criterion; and
- stop for further instruction.

If modified, use only the team's approved design. Restate the final approved
design before proceeding; do not continue with the original proposal.

### Approved Proposal and Execution Instructions

Team approval does not mean the change has already been applied. First provide
exact execution instructions for the approved design. Where applicable include:

- SQL statements or migration commands
- Supabase SQL Editor steps
- RLS policy SQL
- constraint changes
- data-backfill steps
- role or configuration changes
- exact repository files that must later be updated
- verification queries or checks

Use the repository's approved migration workflow when one exists. If no
migration/versioning convention exists, say so and use only the team-approved
execution approach. Do not expand the approved scope.

### Developer Execution Checkpoint

After providing instructions, stop and ask the developer to perform the shared
change. Do not continue until the developer explicitly confirms completion,
for example `Done`, `Schema updated` or `RLS policy applied`.

If the developer reports an error, diagnose only the approved shared change.
Do not resume the story workflow yet.

### Verification and Database Documentation

After confirmation, verify the change where tools or evidence allow, for
example by inspecting an approved migration, supplied schema export, SQL
output, verification query, constraint/RLS policy, or comparison with
`docs/architecture/database_schema.md`.

If direct verification is unavailable, request the minimum evidence needed or
state clearly that live verification could not be independently performed. Do
not claim verification without evidence.

For an approved and actually applied shared schema, RLS, status or constraint
change, one designated developer/shared-change owner must:

1. apply the team-approved change;
2. verify it where possible;
3. update `docs/architecture/database_schema.md` immediately to the resulting
   approved and current structure; and
4. commit the shared change according to the team's agreed migration process.

Other affected story branches must consume, pull or rebase against that shared
change rather than independently recreating or documenting it. If several
stories depend on the same change, they must not each apply it.

Do not document speculative or unapplied schema changes.

Resume the story only after team approval, developer execution, verification
or an explicit verification limitation, and required shared documentation are
complete.

## Shared Baseline Synchronisation Rule

### Individual Story Branches

Individual story branches may update their own canonical artifacts where
applicable:

- `docs/user-stories/<story-name>.md`
- `docs/test-cases/<story-name>.md`
- relevant story-level UML
- relevant runtime files
- relevant pytest files

They must not normally modify `docs/architecture/project_context.md` or
`docs/architecture/common_structure.md` merely because an approved story
changes a shared project fact. Parallel story branches editing those shared
baseline files create unnecessary merge conflicts and inconsistent baseline
edits.

### Shared Baseline Update Required

If an approved story changes a project-wide business rule, role responsibility,
shared workflow, service/domain responsibility or cross-story system fact, do
not automatically update the shared baseline files from the ordinary story
branch. Instead record this item in the story completion report:

```text
## Shared Baseline Update Required

Affected document:
<docs/architecture/project_context.md or docs/architecture/common_structure.md>

Current shared rule/fact:
<current baseline wording>

Approved replacement:
<approved wording>

Origin:
<story and approved requirement>

Why reconciliation is required:
<why the shared baseline needs later synchronisation>
```

Example:

```text
Affected document:
docs/architecture/project_context.md

Current shared rule:
Submitted events are automatically assigned to an Event Coordinator.

Approved replacement:
Submitted events enter the unassigned queue and are assigned by the Event
Coordinator Lead.

Origin:
<story / approved requirement>
```

Carry this item into the end-of-sprint baseline synchronisation task. Deferring
the shared-document update does not mean the approved story requirement is
incomplete.

### End-of-Sprint / Integration Baseline Sync

Synchronise `docs/architecture/project_context.md` through a dedicated shared
baseline task after the relevant approved stories have been merged. Update
`docs/architecture/common_structure.md` only when architecture or repository
navigation genuinely changed.

The baseline-sync task reviews:

- stories merged during the sprint;
- approved customer requirement changes;
- approved Human Gate 3 decisions;
- shared roles and workflows that changed; and
- the existing `project_context.md` and `common_structure.md` content.

It proposes the minimum required shared-document updates. Human/team review is
required before the shared baseline-sync commit. If no shared baseline facts
changed during the sprint, no baseline-document change is required.

Do not automatically create this end-of-sprint commit from an individual story
workflow.

---

# Phase 4 - Story Implementation

After every applicable gate is cleared, implement only the approved assigned
story.

## Architecture and Scope Rules

- Follow `Frontend -> Flask Route -> Service / Business Logic -> Supabase`.
- Put routes in `app/routes/` and business logic in `app/services/`.
- Reuse `app/supabase_client.py`; do not create duplicate Supabase setup.
- Use the current approved/documented database structure in
  `docs/architecture/database_schema.md`.
- Reuse existing authentication; do not create a separate identity mechanism.
- Respect RLS and never use a service-role bypass unless explicitly approved.
- Reuse the established shared frontend, layout and interaction patterns.
- Do not redesign unrelated UI or replace shared frontend files wholesale.
- Do not create a separate Flask application.
- Do not introduce unnecessary repositories, managers, factories, adapters or
  other abstraction layers.
- Keep shared-file changes minimal and coordinate approved shared work.
- Do not perform unrelated refactoring, formatting, renaming or restructuring.
- Do not add or upgrade dependencies unless the story genuinely requires it.
- Do not hard-code secrets, credentials, tokens or test-user passwords.
- Follow all repository-integrity protections in `AGENTS.md`.

The frontend prototype is a visual and interaction baseline, not a source of
new requirements. Replace mock behaviour only where the approved story requires
it.

Routes should handle request input and response concerns while delegating
business decisions to services. Implement clear, scoped error handling without
exposing internal exceptions or secrets.

If implementation reveals a new requirement conflict or shared dependency,
stop and return to the appropriate human gate. Do not silently widen scope.

---

# Phase 5 - Automated Tests

Review existing pytest coverage after implementation:

```text
NEW behaviour
-> add automated tests where meaningful

CHANGED behaviour
-> update or replace affected tests

REMOVED / SUPERSEDED behaviour
-> remove obsolete tests when justified

UNCHANGED behaviour
-> preserve valid existing tests
```

Do not mechanically map one functional test case to one pytest test. Prioritise:

- happy paths
- meaningful negative cases
- genuine boundaries
- conflicts
- authorisation
- state transitions
- story-related regressions

Avoid Cartesian-product parametrisation unless combinations provide genuinely
different behavioural coverage. Mocks and fixtures must reflect the approved
schema shape. Passing obsolete tests is not success.

---

# Phase 6 - Traceability

Before completion, produce:

```text
Acceptance Criterion
-> Functional Test Case(s)
-> Automated pytest evidence or Manual Evidence
```

Account for every Acceptance Criterion. Distinguish clearly between:

- automated test executed and passed;
- implementation supports the behaviour but manual verification is required;
  and
- Acceptance Criterion blocked or not satisfied.

Do not claim execution or automated evidence that did not occur.

---

# Phase 7 - Verification

Run relevant targeted tests first. Then run:

```bash
python scripts/validate_structure.py
python scripts/validate_docs.py
python scripts/project_health.py
```

`project_health.py` already runs the full regression suite. Do not run a
duplicate full pytest command unless it is useful for diagnosis.

If a check fails because of the story, fix only the story-related issue and
rerun it. If a failure is unrelated or pre-existing, stop and report it instead
of changing unrelated code.

---

# Phase 8 - Final Diff Review

Before committing:

- inspect `git status` and the final diff;
- confirm only story-related or approved shared files changed;
- confirm no unrelated tracked file was deleted, renamed or moved;
- confirm no secrets were introduced;
- confirm every human gate was explicitly approved;
- confirm any schema/RLS change matches the approved design;
- confirm `docs/architecture/database_schema.md` was updated if an approved
  schema change was implemented; and
- confirm obsolete tests were not retained only because they previously passed.

---

# Phase 9 - Commit

Commit only if:

- all required human gates are cleared;
- required validation passes; and
- no unrelated working-tree changes are present.

Then:

1. Stage only approved story-related files.
2. Create one coherent final story/task commit.
3. Do not push.

Choose a concise conventional commit message after understanding the completed
change, for example:

```text
feat: implement <story-name>
fix: reconcile <story-name> workflow
docs: reconcile <story-name>
```

After committing, report:

- commit SHA
- commit message
- files included
- story implemented or reconciled
- validation results
- Acceptance Criterion -> functional test -> automated/manual traceability
- schema, RLS or other shared changes used
- known limitations or dependencies

Where applicable, include this separate field:

```text
Shared Baseline Update Required:
- None
```

or:

```text
Shared Baseline Update Required:
- <document and approved shared fact needing end-of-sprint reconciliation>
```

Do not push.

---

# Blocked Work Rule

If work is blocked after Human Gate 2 because a required shared decision is not
approved, do not pretend the story is complete, implement hacks, or create the
final implementation commit. A documentation-only checkpoint commit may be
created only when the developer explicitly requests it. Report the blocker and
stop.

# Cross-Story Boundary

If another developer's story is affected:

1. identify the affected story and the exact dependency;
2. record what the current story needs from it;
3. hand the impact to that story's owner; and
4. stop at that boundary for the other story.

Do not update the other story's canonical requirements or tests, start its human
gates, design its database changes, or implement its runtime merely because the
current story depends on it. Never recursively start a second story from inside
this workflow.

If the dependency blocks the current story, report the blocked Acceptance
Criterion and stop or continue only the independently safe portion. Shared
dependencies may be designed or implemented here only when the team explicitly
assigns and approves them as shared work.

# Direct Repository Editing

When repository-editing tools are available, inspect before editing, make the
smallest coherent change, run the actual checks and report actual results. Do
not merely describe hypothetical changes.

If editing tools are unavailable, provide exact paths and required changes
without inventing unseen file contents.

# End State

A story is complete only when:

- the canonical User Story and Acceptance Criteria are approved;
- the canonical functional test specification is approved;
- required shared architecture decisions are approved;
- implementation matches approved requirements;
- automated tests are updated appropriately;
- obsolete behaviour and tests are removed where required;
- traceability is complete;
- required project health checks pass;
- the final diff is reviewed;
- one coherent commit is created; and
- human Pull Request review can proceed.

==================================================
END OF PRIMARY STORY WORKFLOW
==================================================
