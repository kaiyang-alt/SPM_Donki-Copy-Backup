# ConnectSphere Shared Project Context

This document contains the shared technical and functional context for ConnectSphere.

Developers and AI coding agents should treat this file as the current project-level source of truth unless newer confirmed customer requirements or team decisions override it.

---

## 1. System Overview

ConnectSphere is a role-based event management system.

The main user roles are:

- Event Organiser
- Event Coordinator
- Event Coordinator Lead
- Venue Staff
- Technical Support Staff
- Attendee

A user may hold more than one role.

Authentication is handled through Supabase Authentication.

---

## 2. Application Architecture

The shared application flow is:

```text
Frontend
    ↓
Flask Route
    ↓
Service / Business Logic
    ↓
Supabase
```

### Frontend

Shared frontend files:

```text
app/templates/index.html
app/static/css/styles.css
app/static/js/app.js
```

The approved ConnectSphere light prototype is the shared frontend baseline.

New user stories should extend the existing interface rather than create a separate design or application.

Some current frontend behaviour is still mock or hard-coded prototype behaviour.

Mock behaviour should only be replaced when the relevant user story is implemented.

---

### Flask Routes

New Flask route modules belong in:

```text
app/routes/
```

Routes should primarily:

- receive requests
- validate basic request input
- call the appropriate service/business logic
- return the response

Business rules should not be unnecessarily embedded directly in routes.

---

### Services

Business logic belongs in:

```text
app/services/
```

Examples include:

- event-change rules
- venue booking rules
- equipment availability rules
- registration-capacity rules
- coordinator reassignment workflow

---

### Supabase

Supabase provides:

- Authentication
- PostgreSQL database
- Row Level Security
- Persistent application data

The shared client is:

```text
app/supabase_client.py
```

New features should reuse:

```python
create_supabase_client()
```

Do not create duplicate Supabase configuration or authentication approaches for individual user stories.

---

## 3. Current Database Tables

The documented live Supabase table structure and Row Level Security policies are available in [Database Schema](database_schema.md).

The current live Supabase application tables are:

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

These singular names are the current naming standard.

Older SQL or historical documentation may contain previous plural table names.

New application code must use the current names above.

Do not create, rename or modify tables, columns, relationships or status values without team agreement.

---

## 4. Service Ownership

### User / Authentication

Tables:

```text
profile
user_role
```

Responsibilities include:

- user profile information
- application roles
- Supabase Authentication integration

---

### Event

Tables:

```text
event
event_action_log
event_change_request
event_coordinator_reassignment
```

Responsibilities include:

- event information
- event status
- organiser event requests
- event-change requests
- event action history
- coordinator assignment/reassignment

---

### Venue

Tables:

```text
venue
venue_booking
venue_block
```

Responsibilities include:

- venue catalogue
- venue availability
- venue booking requests
- venue operational blocks

---

### Equipment

Tables:

```text
equipment
equipment_reservation
equipment_unavailability
```

Responsibilities include:

- equipment catalogue
- equipment availability
- equipment reservations
- equipment unavailability

---

### Registration

Table:

```text
registration
```

Responsibilities include:

- attendee registration
- registration limits
- VIP registration
- waitlist handling

---

### Notification

Table:

```text
notification
```

Responsibilities include:

- user notifications
- read/unread state

---

## 5. Event Status Values

The current event statuses are:

```text
draft
requested
changes_requested
planning
confirmed
completed
cancelled
withdrawn
rejected
```

Do not introduce additional event statuses without team agreement.

---

## 6. Other Important Status Values

### Venue Booking

```text
requested
tentative
confirmed
rejected
cancelled
```

### Event Change Request

```text
pending
agreed
rejected
applied
cancelled
```

### Coordinator Reassignment

```text
pending
accepted
rejected
cancelled
```

### Registration

```text
registered
waitlisted
invited
withdrawn
cancelled
```

New code should use existing database-supported values instead of inventing new ones.

---

## 7. Important Confirmed Business Rules

### Coordinator Assignment

- Each submitted event must have exactly one Event Coordinator.
- A newly submitted request remains in `requested` with no coordinator until an Event Coordinator Lead assigns it.
- `event_coordinator_lead` is distinct from `event_coordinator`.
- An Event Coordinator Lead assigns an unassigned request by setting `event.coordinator_id`; assignment does not change the `requested` status.
- The newly assigned coordinator and Event Organiser are notified when assignment occurs.
- Coordinator-initiated reassignment requires agreement between the outgoing and incoming coordinators.
- An Event Coordinator Lead may directly replace an event's coordinator without either coordinator's approval.
- Lead-controlled reassignment notifies the outgoing coordinator, incoming coordinator and Event Organiser.
- The outgoing coordinator initiates reassignment.
- The proposed new coordinator accepts or rejects it.

---

### Event Changes

- Organisers may amend their event before Coordinator approval.
- Organisers may withdraw an event during planning.
- Significant event changes may require notification or renewed approval.
- A significant change should not automatically cause an event-status change unless required by the implemented workflow.
- Normal operational changes may simply update the event and notify relevant users.

---

### Venue Booking

- The Event Organiser provides venue requirements.
- The Event Coordinator searches for venues and submits the venue-booking request.
- Venue Staff has final authority to approve or reject venue bookings.
- Venue Staff may suggest an alternative venue without restarting the full event-request process.
- Only one active tentative or confirmed venue/time arrangement should apply to the event at one time.
- External venues are not part of the core first-release scope.

---

### Equipment

- Equipment arrangements are handled through the Equipment service.
- Coordinator and Technical Support determine required equipment.
- If no equipment is required, the equipment requirement may be considered complete.
- Equipment availability must consider unavailable and already committed quantities.

---

### Event Confirmation

Both:

```text
venue arrangement
AND
technical/equipment arrangement
```

must be completed before the event can be considered fully confirmed.

---

### Registration

- Registration is governed by the registration capacity.
- Expected attendance is used for planning and is not necessarily the same as registration capacity.
- VIP attendance may exceed the normal registration limit.
- VIP attendance must still remain within physical venue capacity.
- Waitlisted attendees are invited when appropriate rather than automatically promoted.
- Attendees are authenticated users.

---

### Multi-Session Events

Multiple sessions should currently be represented as separate events.

---

## 8. Row Level Security

Row Level Security is enabled for the application database.

The existing RLS design must be respected.

Examples of the access model include:

- organisers access their own event information
- coordinators access events required for coordination
- venue staff access venue and booking information
- technical support accesses relevant equipment information
- attendees access appropriate event and registration information

Do not:

- disable RLS
- bypass RLS
- replace the access model
- introduce service-role-key usage

without explicit team agreement.

---

## 9. Authentication

Authentication uses Supabase Authentication.

The current backend contains:

```text
POST /auth/login
```

The existing login implementation currently remains in:

```text
app/app.py
```

This is existing baseline functionality.

New feature development should follow the shared:

```text
route → service → Supabase
```

structure.

The authentication implementation may be refactored when the relevant authentication user story is implemented.

Do not introduce another authentication method.

---

## 10. Shared Frontend

The approved frontend baseline is located in:

```text
app/templates/index.html
app/static/css/styles.css
app/static/js/app.js
```

The prototype establishes the shared:

- navigation
- layout
- cards
- forms
- modal patterns
- role-based screens
- visual language
- interaction style

The frontend should not be redesigned for individual user stories.

Story-specific changes should be kept as isolated as practical.

Coordinate with the team before making large structural changes to shared frontend files.

---

## 11. Frontend Visual System

Current visual baseline:

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

New screens should remain consistent with this baseline.

---

## 12. Prototype vs Functional Requirements

The frontend prototype is a visual and interaction baseline.

It is not automatically the source of truth for business rules.

Where prototype behaviour conflicts with confirmed requirements:

```text
Confirmed requirement wins.
```

Example:

The prototype may currently allow an organiser to select a venue during event creation.

The confirmed requirement is:

```text
Organiser provides venue requirements
→ Coordinator searches for a suitable venue
→ Coordinator submits booking request
→ Venue Staff approves or rejects
```

When the relevant story is implemented, preserve the approved visual style but replace incorrect prototype logic with the confirmed workflow.

---

## 13. Testing

Automated testing uses:

```text
pytest
```

Tests are located under:

```text
tests/
```

Run:

```bash
python -m pytest
```

before opening a Pull Request.

Story-specific tests should be added where appropriate.

Tests should verify actual acceptance criteria rather than obsolete prototype behaviour.

---

## 14. Continuous Integration

GitHub Actions is configured in:

```text
.github/workflows/ci.yml
```

CI runs pytest for:

- pushes to `main`
- Pull Requests targeting `main`

CI should pass before merge.

---

## 15. User Story Documentation

Story-specific implementation context belongs in:

```text
docs/user-stories/
```

A user-story document should contain the information required to implement that story, such as:

```text
User Story
Acceptance Criteria
Test Cases
Relevant Customer Clarifications
Preconditions / Dependencies
Relevant UML Reference
```

Do not put unrelated requirements into a story document.

---

## 16. UML

UML belongs in:

```text
docs/uml/
```

Use just-enough UML.

Useful diagrams include:

- sequence diagrams when interaction order or alternative flows matter
- class diagrams when code-level structure requires clarification

PlantUML or Mermaid source should be preferred so diagrams remain editable and version-controlled.

A diagram is not required simply for the sake of having one.

---

## 17. Development Flow

Each user story should generally follow:

```text
User Story + Acceptance Criteria
        ↓
Test Cases
        ↓
Relevant Customer Clarifications
        ↓
Preconditions / Dependencies
        ↓
Just-Enough UML where useful
        ↓
Implementation
        ↓
Testing
        ↓
Evidence
        ↓
Pull Request
        ↓
Human Review
        ↓
Merge
```

Implement only the required story scope.

Avoid unrelated refactoring or features unless required for the story.

---

## 18. Parallel Development

Multiple team members may implement different user stories in parallel.

To reduce conflicts:

- pull the latest `main` before starting
- use a separate short-lived branch
- keep changes scoped to the assigned story
- avoid unnecessary edits to shared files
- coordinate large shared frontend changes
- place new routes in `app/routes/`
- place business logic in `app/services/`
- reuse the current database
- reuse the current Supabase client
- follow the approved frontend baseline

Different team members may use different AI coding assistants.

All AI agents should receive the same shared project context.

---

## 19. AI Context Package

Before asking an AI coding agent to implement a story, provide:

```text
README.md
AGENTS.md
docs/architecture/project_context.md
docs/user-stories/<relevant-story>.md
Relevant UML, if applicable
```

The AI should not:

- invent new tables
- rename current tables
- invent new status values
- introduce a new authentication mechanism
- disable RLS
- redesign the frontend
- implement unrelated requirements

If the requested story genuinely requires one of these changes, the issue should be raised with the team before implementation.

---

## 20. Current Shared Baseline

The current repository baseline includes:

- Flask application
- Supabase connection
- Supabase Authentication login endpoint
- approved ConnectSphere light frontend prototype
- shared CSS
- shared JavaScript
- route folder
- service folder
- database schema and RLS already configured in Supabase
- automated pytest setup
- GitHub Actions CI
- architecture documentation
- UML documentation folder
- user-story documentation folder
- shared AI/development instructions

The system should now be extended incrementally through user stories rather than rebuilt.

---

## 21. Security

Never commit:

```text
.env
Supabase keys
Passwords
Access tokens
Test-account credentials
Other secrets
```

Environment-specific secrets belong only in local `.env` files or approved private team channels.

---

## 22. Source of Truth

If documents or prototype behaviour disagree, use this priority:

```text
1. Confirmed customer requirements and clarifications
2. Approved database schema and RLS design
3. Relevant user story and acceptance criteria
4. This shared project context
5. Shared architecture documentation
6. AGENTS.md development rules
7. Approved frontend prototype
```

Do not silently guess when an important requirement is unclear.

Raise the ambiguity with the team before changing shared architecture or data design.
