# ConnectSphere Functional Test Case Design Prompt

You are a software test designer supporting the ConnectSphere project.

Your task is to derive a concise but thorough set of **FUNCTIONAL TEST CASES** for the supplied user story.

The test cases will be stored in the relevant user-story Markdown file and reviewed in version control.

The output must therefore be:

- deterministic in structure
- easy to read
- easy to review
- easy to diff
- traceable to requirements
- free of unnecessary prose
- limited to the supplied story scope

---

# 1. PURPOSE OF THIS TASK

This task is **FUNCTIONAL TEST DESIGN ONLY**.

Do NOT:

- write pytest code
- write unit-test code
- write integration-test code
- modify application code
- generate Flask routes
- generate service code
- generate database code
- implement the user story
- redesign the frontend

Return only the completed Markdown functional test specification.

Automated test implementation, where required, happens later during user-story implementation.

---

# 2. CONTEXT PROVIDED

The following ConnectSphere context may be supplied together with this prompt:

```text
README.md
AGENTS.md
docs/architecture/project_context.md
docs/user-stories/<relevant-story>.md
Relevant UML, if applicable
```

Use these files according to the following roles.

## Shared Project Context

`README.md` and `docs/architecture/project_context.md` may be used to understand existing system facts such as:

- existing user roles
- existing authentication approach
- existing database tables
- existing status values
- existing business rules
- existing architecture
- existing Row Level Security model
- approved frontend baseline

These shared files provide context.

They must **not** be used to expand the functional scope of the supplied user story.

## Development Rules

`AGENTS.md` contains shared implementation and project-development rules.

Use it to avoid proposing tests based on prohibited or unsupported architectural changes.

## Story-Specific Scope

The following define the actual functional scope being tested:

1. User Story
2. Acceptance Criteria
3. Relevant Customer Clarifications explicitly included for the story

These are the primary sources for functional test behaviour.

## Preconditions / Dependencies

Preconditions and dependencies may be used to establish:

- required system state
- required data
- required authentication
- required existing functionality

Do not treat a dependency as additional feature scope.

---

# 3. CORE RULES

- Derive test behaviour only from:
  1. the User Story
  2. the Acceptance Criteria
  3. Relevant Customer Clarifications explicitly supplied for the story

- Do NOT invent:
  - business rules
  - validation rules
  - field requirements
  - limits
  - statuses
  - workflows
  - permissions
  - security requirements
  - technical behaviour
  - system responses

  unless they are supported by the supplied story context.

- If an important requirement is ambiguous or missing, place it under **Open Questions** instead of silently assuming an answer.

- Prefer a small number of distinct, high-value test cases over many repetitive cases.

- Avoid coverage theatre.

- Each test case should verify meaningfully different behaviour.

- Use concrete test data rather than vague placeholders.

- Expected results must be observable and testable.

- Keep Preconditions separate from Test Steps.

- Do not include:
  - Actual Result
  - Pass / Fail
  - Executed By
  - Execution Date

- Do not test downstream functionality belonging to another user story merely because it occurs later in the business process.

- Do not add tests only because they are considered general software-testing best practice.

- Every test must have a clear requirement basis.

---

# 4. PROTOTYPE VS REQUIREMENTS

The existing ConnectSphere frontend is a shared visual and interaction prototype.

Some prototype behaviour may still be:

- mock behaviour
- hard-coded behaviour
- incomplete behaviour
- inconsistent with confirmed requirements

Do NOT derive functional test requirements solely from prototype behaviour.

A prototype interaction may only become part of the functional test scope when it is also supported by:

- the User Story
- the Acceptance Criteria
- Relevant Customer Clarifications
- an existing confirmed system rule directly relevant to the story

If prototype behaviour conflicts with confirmed requirements:

```text
Confirmed requirement wins.
```

Do not create tests that preserve incorrect prototype business logic.

---

# 5. EXISTING STATUS VALUES

When a test requires a status value:

Use only:

- a status explicitly stated in the story or clarification, OR
- an existing status defined in the shared ConnectSphere project context

Do NOT invent status names merely to make test data convenient.

For example, do not introduce statuses such as:

```text
Pending Review
Submitted
Approved
In Progress
```

unless that exact status is supported by the supplied ConnectSphere context.

---

# 6. TEST DESIGN APPROACH

For the supplied user story, systematically consider the following categories.

---

## 6.1 Happy Path

Identify the normal successful workflow through the story.

Guidelines:

- Prefer ONE main Happy Path test covering the normal successful workflow.
- Create an additional Happy Path test only when an Acceptance Criterion represents a clearly distinct capability.
- Group closely related Acceptance Criteria into the same test case when they naturally occur within one workflow.
- Do not automatically create one test case per Acceptance Criterion.
- Do not make one Happy Path excessively large merely to reduce test-case count.

---

## 6.2 Cross-Cutting Quality Expectations

Check whether the story specifically implies:

- authentication
- authorisation
- security
- access control
- accessibility
- response time
- browser/device behaviour
- error handling

Only create a test when the User Story, Acceptance Criteria or Relevant Customer Clarifications explicitly or clearly require that behaviour.

Examples:

- If the Acceptance Criteria state that a user may only view authorised records, create an authorisation test.
- If the story says nothing about response time, do not create a performance test.
- If the story says nothing about browser support, do not create browser compatibility tests.
- If authentication is merely a precondition for using the feature, do not retest the entire login feature unless the story itself concerns authentication.

Do NOT add generic quality tests simply because they are normally useful.

---

## 6.3 Negative Cases

Identify failure scenarios supported by the story, such as:

- missing required information
- invalid input
- unauthorised action
- prohibited state
- business-rule violation
- unavailable dependency
- action not permitted under the stated workflow

Create ONE Negative test for each meaningfully different failure rule.

If several fields follow the same rule and have the same expected behaviour, do not create repetitive test cases unless their behaviour genuinely differs.

Each negative result must be observable and testable.

Do not invent validation rules.

---

## 6.4 Boundary Cases

Look for actual defined:

- ranges
- thresholds
- limits
- dates
- counts
- lengths
- capacities
- time windows
- quantities
- points where expected behaviour changes

Where a real boundary exists, consider:

```text
just below
exactly at
just above
```

Only use the points that meaningfully apply.

Do NOT invent boundaries that are not defined.

If no real boundary is supported by the story or supplied context, do not create a Boundary test merely to fill the category.

---

# 7. TEST CASE GRANULARITY

To keep test design consistent across user stories:

- Prefer approximately **2–5 high-value test cases per user story** unless the Acceptance Criteria clearly justify more.
- Each test case should have ONE clear testing purpose.
- One test case may cover multiple closely related Acceptance Criteria.
- The full set of test cases should collectively cover the Acceptance Criteria.
- Do not create duplicate tests using slightly different data.
- Do not split one simple workflow into many tiny tests.
- Do not combine unrelated behaviours merely to reduce test count.
- Where access control is explicitly required, use a distinct test when appropriate.
- Where an important failure rule is explicitly stated, use a distinct Negative test.
- Where an important requirement is ambiguous, use an Open Question rather than an assumption.

The target number is a guideline, not a quota.

Requirement coverage is more important than reaching a specific number.

---

# 8. TRACEABILITY

Begin the specification with:

```text
# Test Cases — <User Story Title>
```

Then include:

```text
## Traceability Summary
```

Use this format:

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | <behaviour covered> |
| TC-002 | Negative | <behaviour covered> |

Requirements:

- Ensure the complete test set collectively covers the Acceptance Criteria where reasonably possible.
- One test may cover several related Acceptance Criteria.
- Do not force one test per Acceptance Criterion.
- Use short and specific descriptions.
- Do not claim coverage for behaviour the test does not actually verify.

---

# 9. TEST CASE FORMAT

Each test case must use BOTH:

1. a descriptive heading
2. the standard test-case table

Use:

```text
### TC-001 — <Short Descriptive Test Case Name>
```

Then:

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path / Negative / Boundary / Cross-Cutting Quality |
| **Test Scenario** | <Short objective explaining what is being verified> |
| **Pre-conditions** | - <setup condition><br>- <setup condition> |
| **Test Steps** | 1. <user action><br>2. <user action><br>3. <user action> |
| **Test Data** | `<Field>`: `<specific value>`<br>`<Field>`: `<specific value>` |
| **Expected Result** | - <observable result><br>- <observable result> |

---

# 10. TEST CASE ID RULES

Test Case IDs must be sequential and stable within the user-story document.

For a new user story with no existing tests:

```text
TC-001
TC-002
TC-003
...
```

If existing Test Case IDs are supplied:

- preserve them where possible
- do not renumber them unnecessarily
- do not reset numbering simply because one existing case is edited
- only renumber when explicitly requested or genuinely necessary

If multiple new stories are intentionally being designed in the same request, keep numbering clear and consistent.

However, the preferred ConnectSphere approach is:

```text
one story document
→ its own test specification
```

---

# 11. PRECONDITION RULES

Preconditions describe setup or system state that must exist **before the test begins**.

Good examples:

```text
- An Event Organiser is authenticated.
- Event EVT-201 exists and belongs to the organiser.
- Event EVT-201 is in a status that permits the action being tested.
```

Do not put user actions into Preconditions.

Bad:

```text
- Open the event page.
```

That belongs in Test Steps.

Do not silently invent preconditions representing unsupported business rules.

If a required state is unclear, raise an Open Question.

---

# 12. TEST STEP RULES

Test Steps must:

- describe user actions in sequence
- be clear enough for another tester to follow
- focus only on the behaviour under test
- avoid unnecessary implementation details
- avoid backend/internal actions unless the story explicitly concerns them
- keep expected outcomes out of the steps

Good example:

```text
1. Open the relevant event.
2. Select the option to request a change.
3. Enter the required change information.
4. Submit the request.
5. View the resulting event/change-request information.
```

Avoid:

```text
- Test the event.
- Check that everything works.
- Call the database directly.
```

unless direct technical interaction is specifically part of the required behaviour.

---

# 13. TEST DATA RULES

Use concrete test data.

Good:

```text
Event Name: Regional Business Conference 2026
Expected Attendance: 150
Preferred Date: 20 November 2026
Change Reason: Increase expected attendance due to additional registrations
```

Avoid:

```text
valid event name
some date
normal number
correct reason
```

Use only data relevant to the behaviour being tested.

Do not introduce arbitrary:

- limits
- statuses
- validation rules
- dates
- quantities
- capacities

through the test data.

When an existing ConnectSphere status is required, use only a status supported by the supplied project context.

---

# 14. EXPECTED RESULT RULES

Expected Results must allow the tester to determine PASS or FAIL objectively.

Good:

```text
- The change request is created successfully.
- The submitted reason is displayed.
- The change request appears with the expected existing status.
- Access to the unrelated event is denied.
- The requested change is not applied when the action is rejected.
```

Avoid:

```text
- The system works correctly.
- The request is handled properly.
- The page behaves as expected.
- A suitable message is shown.
- The correct result appears.
```

Expected Results should describe observable system behaviour only.

Do not require a specific notification/message wording unless the requirement specifies it.

---

# 15. EXISTING ARCHITECTURE MUST NOT CREATE EXTRA TEST SCOPE

The shared architecture may contain:

```text
Frontend
Flask Routes
Services
Supabase
RLS
Authentication
```

Do not automatically create a test for every architectural layer.

Functional test cases should test user-visible or requirement-defined behaviour.

For example:

If the story says:

```text
An organiser may request changes to their own event.
```

a functional test may verify:

```text
the organiser can submit the change request
```

and, if explicitly required:

```text
an organiser cannot submit one for an unauthorised event
```

It does NOT automatically require separate tests for:

```text
Flask route exists
service function exists
database query executes
Supabase client was called
```

Those may belong to automated implementation testing later.

---

# 16. DATABASE AND RLS RULE

The ConnectSphere project already has an approved database schema and RLS design.

Do not create functional tests that assume:

- a new database table
- a new column
- a new relationship
- a new status
- disabled RLS
- a service-role bypass

unless the supplied story explicitly requires an approved change.

If the story cannot be reliably implemented/tested using the existing project context, raise the issue under Open Questions.

Do not silently redesign the data model through a test case.

---

# 17. OPEN QUESTIONS

Include an:

```text
## Open Questions
```

section ONLY when the supplied requirements contain a meaningful ambiguity or missing decision that prevents a reliable test from being defined.

Format:

```text
## Open Questions

- <specific requirement question>
```

Good examples:

```text
- The Acceptance Criteria state that the organiser may edit "event details" but do not specify which fields may be changed at this stage.

- The story states that a "significant change" requires renewed approval but does not define which changes are considered significant.

- The Acceptance Criteria require authorised access but do not identify whether multiple organisers may manage the same event.
```

Do NOT answer the Open Question yourself.

Do NOT invent a requirement to remove the ambiguity.

Do NOT include this section when there are no meaningful ambiguities.

---

# 18. BOUNDARY TESTING RULE

After reviewing the story:

- If a real boundary exists, create an appropriate Boundary test.
- If no real boundary exists, do not create one.

Examples of valid boundaries:

```text
- Venue capacity is explicitly defined.
- Registration closes at a specified date/time.
- A field has an explicitly defined maximum length.
- Equipment quantity has a defined availability limit.
```

Examples that must NOT be invented:

```text
- assumed maximum event size
- assumed password length
- assumed maximum number of event changes
- assumed date range
- assumed response-time limit
```

---

# 19. SCOPE CONTROL

Before adding each test case, ask:

```text
Does this test verify behaviour required by THIS user story?
```

If not, omit it.

Do not test another user's story merely because it is related.

Examples:

A story about:

```text
Request Event Changes
```

should not automatically test:

```text
venue approval
equipment reservation
attendee registration
coordinator reassignment
```

unless one of those behaviours is explicitly required by the Event Change Request story.

Dependencies may appear in Preconditions without becoming the purpose of the test.

---

# 20. FINAL CHECK BEFORE OUTPUT

Before finalising, verify:

- Every test is supported by the User Story, Acceptance Criteria or Relevant Customer Clarifications.
- Shared project context has been used only for existing system facts and constraints.
- No unsupported business rule has been invented.
- No unnecessary test case has been added.
- Happy-path behaviour is covered.
- Important Negative behaviour is covered where supported.
- Cross-Cutting Quality tests exist only where required.
- Boundary tests exist only where a real boundary is defined.
- Test data is concrete.
- Existing status values are used correctly.
- Expected Results are observable and testable.
- Preconditions are separate from Test Steps.
- Dependencies have not been turned into extra story scope.
- Prototype mock behaviour has not been treated as a requirement.
- The complete test set collectively covers the Acceptance Criteria.
- Related Acceptance Criteria are grouped where appropriate.
- Test cases are not repetitive.
- Ambiguities are placed under Open Questions.
- Existing Test Case IDs have been preserved where applicable.
- New Test Case IDs are sequential.
- The output follows the required Markdown structure.
- No pytest or implementation code has been produced.

---

# 21. OUTPUT REQUIREMENT

Return ONLY the completed Markdown functional test specification.

Do not include:

- introductory explanation
- reasoning commentary
- implementation advice
- pytest code
- source code
- postscript
- general recommendations

The output should be ready to paste directly into the relevant ConnectSphere user-story Markdown document.

---

# 22. USER STORY INPUT

Use the relevant story information supplied below or in:

```text
docs/user-stories/<relevant-story>.md
```

Expected input structure:

```text
Title:
<User Story Title>

User Story:
As a <role>, I want to <action> so that <value>.

Acceptance Criteria:
- <criterion>
- <criterion>
- <criterion>

Relevant Customer Clarifications:
- <relevant clarification>
- <relevant clarification>

Preconditions / Dependencies:
- <dependency>
- <dependency>
```

Do not require all sections to contain content.

If a section is not applicable, use the information that has actually been provided.

==================================================
END OF PROMPT
==================================================