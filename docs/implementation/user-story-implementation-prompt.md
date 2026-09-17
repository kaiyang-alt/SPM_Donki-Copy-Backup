# ConnectSphere User Story Implementation Prompt

You are a software developer working on the ConnectSphere project.

Your task is to implement **ONE assigned user story** using the existing ConnectSphere repository, approved requirements, shared architecture and approved functional test cases.

The implementation must remain within the scope of the supplied user story.

Do not redesign or rebuild unrelated parts of the system.

---

# 1. PURPOSE OF THIS TASK

This task is for **USER STORY IMPLEMENTATION**.

You may:

- inspect the existing repository
- modify existing application files where required
- create story-specific route modules
- create story-specific service modules
- extend the existing frontend
- integrate with the existing Supabase database
- add or update automated pytest tests where appropriate
- fix story-related defects discovered during implementation

You must NOT:

- implement unrelated user stories
- perform unrelated refactoring
- redesign the whole application
- replace the existing architecture
- invent new requirements
- create new database structures without approval
- bypass existing security controls
- change shared project decisions simply because another approach seems cleaner

Implement the smallest coherent set of changes required to satisfy the assigned story.

---

# 2. REQUIRED CONTEXT

Before implementation, review the following files:

```text
README.md
AGENTS.md
docs/architecture/project_context.md
docs/user-stories/<relevant-story>.md
docs/test-cases/<relevant-story>.md
Relevant UML under docs/uml/, if applicable
```

Use these files according to the following responsibilities.

## README.md

Use for:

- repository structure
- local setup
- development workflow
- testing workflow
- shared project navigation

## AGENTS.md

Use as the implementation rules.

Follow its restrictions regarding:

- frontend consistency
- backend structure
- database changes
- Git workflow
- security
- story scope

## Shared Project Context

Use:

```text
docs/architecture/project_context.md
```

for existing ConnectSphere facts such as:

- architecture
- user roles
- current database tables
- current status values
- confirmed business rules
- authentication approach
- Row Level Security model
- frontend baseline
- current project decisions

## User Story Document

Use:

```text
docs/user-stories/<relevant-story>.md
```

for the exact scope of the assigned feature.

It may contain:

- User Story
- Acceptance Criteria
- Relevant Customer Clarifications
- Preconditions / Dependencies
- Test Case Reference
- UML Reference
- Implementation Notes

## Functional Test Cases

Use:

```text
docs/test-cases/<relevant-story>.md
```

as the approved functional behaviour that the implementation should satisfy.

Functional test cases support implementation and verification.

They do not override confirmed requirements.

## UML

Use relevant UML only where provided.

UML should clarify implementation.

Do not invent additional architecture simply because a diagram does not exist.

---

# 3. SOURCE-OF-TRUTH PRIORITY

If supplied information conflicts, use this priority:

```text
1. Confirmed customer requirements and clarifications
2. Approved database schema and RLS design
3. User Story and Acceptance Criteria
4. Approved functional test cases
5. docs/architecture/project_context.md
6. Existing shared architecture documentation
7. AGENTS.md implementation rules
8. Approved frontend prototype
```

Do not silently resolve an important contradiction yourself.

If a conflict materially affects implementation, flag it before proceeding.

---

# 4. BEFORE WRITING CODE

Before modifying the repository:

1. Read the assigned User Story.
2. Read every Acceptance Criterion.
3. Review Relevant Customer Clarifications.
4. Review Preconditions / Dependencies.
5. Review the approved functional test cases.
6. Review relevant UML if one exists.
7. Inspect the existing files related to the story.
8. Identify the smallest set of files that need to change.
9. Confirm that the story can be implemented using the existing database and architecture.

Do not begin implementation based only on the story title.

---

# 5. CONFLICT AND AMBIGUITY RULE

Do not start coding if there is a meaningful unresolved conflict between:

```text
User Story
Acceptance Criteria
Customer Clarifications
Functional Test Cases
Database design
Existing shared project rules
```

that changes the expected behaviour.

Do not guess.

Clearly identify:

```text
Conflict:
<what disagrees>

Why it matters:
<how it affects implementation>

Clarification needed:
<specific question>
```

Minor implementation choices that do not alter requirements may be decided normally.

---

# 6. IMPLEMENTATION SCOPE

Implement only behaviour required by the assigned user story.

Do not add functionality merely because:

- it seems useful
- it may be needed in a future sprint
- it is common in similar systems
- the AI believes it is best practice
- a downstream workflow exists
- the prototype contains another feature nearby

Dependencies may be used as existing preconditions.

They do not automatically become implementation scope.

---

# 7. SHARED APPLICATION FLOW

ConnectSphere follows:

```text
Frontend
    ↓
Flask Route
    ↓
Service / Business Logic
    ↓
Supabase
```

New functionality should follow this structure where applicable.

---

# 8. FLASK ROUTE RULES

New Flask route modules belong in:

```text
app/routes/
```

Routes should generally:

- receive the request
- retrieve request data
- perform basic input checks
- call the relevant service
- return an appropriate response

Routes should not contain large amounts of business logic.

Do not create a new Flask application instance for a user story.

Reuse the existing application.

If route registration is required, integrate it with the current Flask application structure using the smallest appropriate change.

---

# 9. SERVICE-LAYER RULES

Business logic belongs in:

```text
app/services/
```

Service logic may include:

- business-rule validation
- workflow decisions
- permission-related business checks where applicable
- interaction with Supabase
- processing application data
- determining permitted state transitions

Keep story-specific logic focused.

Do not create unnecessary abstraction layers.

Do not introduce repositories, managers, factories, adapters or other layers unless the existing project genuinely requires them.

---

# 10. SUPABASE RULES

Reuse:

```python
create_supabase_client()
```

from:

```text
app/supabase_client.py
```

Do not create duplicate Supabase configuration.

Do not hard-code:

```text
Supabase URL
Supabase publishable key
passwords
access tokens
test-user credentials
```

Do not use a service-role key unless explicitly approved by the team.

---

# 11. DATABASE RULES

Use the existing live Supabase schema.

Current application tables are:

```text
profile
user_role
event
event_action_log
event_change_request
event_coordinator_reassignment
venue
venue_booking
venue_block
equipment
equipment_reservation
equipment_unavailability
registration
notification
```

Use these exact current table names.

Older plural table names may appear in historical SQL or documentation.

Do not use the old names in new application code.

Do NOT independently:

- create a new table
- rename a table
- add a column
- remove a column
- alter relationships
- change constraints
- add a new status value
- remove a status value

If the assigned story genuinely appears to require a schema change, stop and flag it for team review.

---

# 12. STATUS VALUE RULE

Use only existing approved status values.

Do not invent convenient statuses.

For example, do not introduce values such as:

```text
Pending Review
Submitted
Approved
Processing
In Progress
```

unless they are actually supported by the shared project context.

Use:

```text
docs/architecture/project_context.md
```

to confirm existing status values.

---

# 13. ROW LEVEL SECURITY

Existing Supabase Row Level Security must be respected.

Do not:

- disable RLS
- bypass RLS
- use privileged credentials to avoid RLS
- weaken access restrictions
- replace the current access model

simply to make the user story easier to implement.

If RLS prevents behaviour that the confirmed story genuinely requires, identify the mismatch and raise it with the team.

---

# 14. AUTHENTICATION

Authentication uses Supabase Authentication.

Do not introduce:

- Flask-Login
- custom password storage
- a second authentication database
- another identity provider
- a separate login mechanism

unless explicitly approved.

Reuse the existing authentication approach.

The existing login implementation may remain in:

```text
app/app.py
```

until the authentication story intentionally refactors it.

Do not refactor working authentication code merely for architectural neatness while implementing an unrelated story.

---

# 15. FRONTEND BASELINE

The approved shared frontend is:

```text
app/templates/index.html
app/static/css/styles.css
app/static/js/app.js
```

Use the existing ConnectSphere:

- layout
- navigation
- styling
- role-based screens
- cards
- forms
- modal patterns
- interaction style

Do not create a separate frontend application.

Do not replace the existing design system.

Do not rewrite shared frontend files wholesale for one user story.

---

# 16. FRONTEND CONFLICT CONTROL

The following are shared files:

```text
app/templates/index.html
app/static/css/styles.css
app/static/js/app.js
```

Multiple developers may modify them in parallel.

Therefore:

- make the smallest practical frontend change
- avoid unrelated formatting changes
- avoid reorganising large sections unnecessarily
- avoid renaming shared functions without need
- avoid moving code purely for style preference
- coordinate with the team before large structural changes

Where practical, keep story-specific additions isolated.

---

# 17. PROTOTYPE RULE

The current frontend is a light prototype.

Some behaviour is:

- mocked
- hard-coded
- incomplete
- only present for demonstration

Do not treat prototype behaviour as a confirmed business requirement.

When implementing a story:

```text
Confirmed requirement
> prototype mock behaviour
```

Replace mock behaviour only where required by the current story.

Do not attempt to convert the entire prototype into production functionality at once.

---

# 18. VISUAL CONSISTENCY

Maintain the approved ConnectSphere Clay & Linen design.

Current shared visual baseline includes:

```text
Clay        #783A32
Linen       #EEE0CC
Warm Ivory  #FAF5EE
Soft Cream  #FFFDF9
Pale Clay   #F2E4D6
Espresso    #453329
```

Typography:

```text
Headings: Georgia
Body / navigation / buttons / labels: Arial
```

New user-story interfaces should fit the existing frontend instead of introducing another visual system.

---

# 19. FUNCTIONAL TEST CASES

Use the approved functional test cases under:

```text
docs/test-cases/<relevant-story>.md
```

to guide implementation verification.

The implementation should collectively satisfy the approved test behaviours.

Do not blindly implement a test case if it conflicts with a higher-priority confirmed requirement.

If such a conflict exists, flag it.

---

# 20. AUTOMATED TESTING

Add or update automated pytest tests where appropriate for the story.

Automated tests belong under:

```text
tests/
```

Functional test specifications under:

```text
docs/test-cases/
```

are NOT the same as pytest files.

Do not mechanically create one pytest test for every functional test case.

Create automated tests where they provide meaningful verification of the implemented behaviour.

Do not delete existing passing tests merely to make a new implementation pass.

If an existing test is obsolete because approved behaviour has changed, update it to reflect the current requirement.

---

# 21. TESTING REQUIREMENT

Before considering implementation complete, run:

```bash
python -m pytest
```

Existing tests must continue to pass unless an approved requirement change legitimately requires a test update.

Where practical, also verify the relevant user workflow manually through the Flask application.

---

# 22. ERROR HANDLING

Implement error handling only where supported or reasonably necessary for the assigned behaviour.

Do not invent extensive validation frameworks.

Error behaviour should be:

- clear
- observable
- consistent with the story
- scoped to the feature

Avoid exposing internal exceptions or secrets to users.

---

# 23. SECURITY

Never commit:

```text
.env
Supabase keys
Passwords
Access tokens
Test-account credentials
Private secrets
```

Do not print sensitive credentials into:

```text
logs
test output
responses
documentation
Git commits
```

Use environment variables for configuration.

---

# 24. MINIMAL-CHANGE RULE

Prefer the smallest coherent implementation.

Do not perform unrelated:

- refactoring
- formatting
- renaming
- folder restructuring
- dependency upgrades
- architecture changes
- frontend redesign
- database changes

while implementing the assigned story.

A Pull Request should be easy for another team member to understand and review.

---

# 25. DEPENDENCY RULE

Before installing a new Python package, determine whether the story can reasonably be implemented using the current dependencies.

Do not add packages unnecessarily.

If a new dependency is genuinely required:

- explain why
- update `requirements.txt`
- keep the change within story scope

Do not replace existing libraries simply because another library is preferred.

---

# 26. USER STORY DOCUMENTATION

If implementation reveals an important approved implementation decision relevant to the story, it may be recorded under:

```text
## Implementation Notes
```

in the relevant user-story document.

Do not turn the story document into a development diary.

Only record information that another developer or reviewer genuinely needs.

---

# 27. UML

Use existing relevant UML when provided.

Do not change UML merely to match code after making an unsupported design decision.

If implementation legitimately changes an approved story-level design, update the relevant UML so documentation and implementation remain consistent.

Do not create unnecessary diagrams.

---

# 28. FILE MODIFICATION DISCIPLINE

Before editing:

- inspect the current file
- understand existing behaviour
- preserve unrelated working functionality

Do not replace entire files when a small targeted edit is sufficient.

If providing code in chat rather than directly editing the repository:

- clearly state the exact file path
- provide complete replacement files when that is safer for the user
- do not omit required imports or surrounding code

---

# 29. IMPLEMENTATION SEQUENCE

Use this sequence:

```text
1. Understand story scope
2. Review test cases
3. Review dependencies
4. Review relevant UML
5. Inspect existing implementation
6. Identify required files
7. Implement route changes
8. Implement service/business logic
9. Integrate Supabase
10. Integrate required frontend behaviour
11. Add/update automated tests where appropriate
12. Run pytest
13. Verify Acceptance Criteria
14. Review changed files
15. Summarise implementation
```

Skip steps that genuinely do not apply.

---

# 30. ACCEPTANCE CRITERIA CHECK

Before declaring the story complete, explicitly verify every Acceptance Criterion.

Use:

```text
AC1 — Satisfied / Not Satisfied
Evidence: <implemented behaviour or test>

AC2 — Satisfied / Not Satisfied
Evidence: <implemented behaviour or test>
```

Do not claim an Acceptance Criterion is satisfied unless the implementation actually supports it.

If an AC remains incomplete, state that clearly.

---

# 31. FUNCTIONAL TEST CASE CHECK

Also verify the approved functional test cases.

Use:

```text
TC-001 — Supported / Not Supported
TC-002 — Supported / Not Supported
...
```

Do not fabricate test execution results.

If the test was not actually executed, distinguish:

```text
Implementation supports expected behaviour
```

from:

```text
Test executed and passed
```

---

# 32. FINAL CODE REVIEW CHECK

Before completion, confirm:

- implementation remains within the user-story scope
- requirements were not invented
- confirmed clarifications were followed
- existing database tables were reused
- current table names were used
- no unapproved status value was added
- RLS was not bypassed
- existing authentication was reused
- route/service structure was followed where applicable
- frontend design remains consistent
- unrelated mock functionality was not unnecessarily replaced
- unrelated files were not refactored
- secrets were not introduced
- relevant automated tests were added or updated where appropriate
- existing tests still pass
- each Acceptance Criterion has been checked

---

# 33. FINAL RESPONSE FORMAT

After implementation, provide a concise implementation summary using:

```text
## Story Implemented

<User Story Title>

## Files Changed

- <file path> — <what changed>
- <file path> — <what changed>

## Implementation Summary

<brief description of how the story was implemented>

## Acceptance Criteria Check

- AC1 — Satisfied / Not Satisfied
- AC2 — Satisfied / Not Satisfied
- AC3 — Satisfied / Not Satisfied

## Functional Test Case Check

- TC-001 — Supported / Not Supported
- TC-002 — Supported / Not Supported

## Automated Testing

Command run:

python -m pytest

Result:

<actual result>

## Open Issues

- <only include if something remains unresolved>
```

Do not claim tests passed unless they were actually executed.

Do not hide incomplete Acceptance Criteria.

---

# 34. IF DIRECT REPOSITORY EDITING IS AVAILABLE

If you have tools that allow you to inspect and edit the repository directly:

1. inspect the existing relevant files first
2. make the required edits
3. avoid unrelated changes
4. run the available tests
5. report the actual files changed and actual test results

Do not merely describe code that could be written when you are able to implement it directly.

---

# 35. IF DIRECT REPOSITORY EDITING IS NOT AVAILABLE

If you cannot edit the repository directly:

- provide exact file paths
- explain which files need modification
- provide complete code where practical
- preserve the current project structure
- do not assume unprovided file contents

If an existing file is required but has not been supplied, request or inspect it before replacing it.

---

# 36. STORY INPUT

Implement the user story contained in:

```text
docs/user-stories/<relevant-story>.md
```

using the approved test specification:

```text
docs/test-cases/<relevant-story>.md
```

and relevant UML if applicable.

==================================================
END OF IMPLEMENTATION PROMPT
==================================================