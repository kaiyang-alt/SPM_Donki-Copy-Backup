# ConnectSphere Development Instructions

## Shared Frontend

- Use the existing ConnectSphere frontend as the shared UI baseline.
- Do not redesign the application or introduce a separate design system.
- Reuse the existing layout, navigation, styling and interaction patterns.
- Replace prototype/mock behaviour only when implementing the relevant user story.

## Backend Structure

Follow this flow:

route → service/business logic → Supabase

- Flask routes belong in `app/routes/`.
- Business logic belongs in `app/services/`.
- Use the existing Supabase client and authentication setup.
- Do not create a new authentication method.

## Database

Use the existing Supabase schema.

Current application tables:

- `profile`
- `user_role`
- `event`
- `event_action_log`
- `event_change_request`
- `event_coordinator_reassignment`
- `venue`
- `venue_booking`
- `venue_block`
- `equipment`
- `equipment_reservation`
- `equipment_unavailability`
- `registration`
- `notification`

Do not create, rename or modify tables, columns, relationships or status values without team agreement.

Do not bypass existing Row Level Security policies without team agreement.

## User Story Implementation

Before coding:

1. Read the assigned user story and acceptance criteria.
2. Review its test cases.
3. Check relevant customer clarifications.
4. Identify required preconditions and dependencies.
5. Use just-enough UML where it clarifies the design or interaction.
6. Implement only the scope required by the story.
7. Test against the acceptance criteria before completion.

## Git Workflow

- Sync with the latest `main` before starting.
- Use a short-lived branch for one coherent story/task.
- Do not commit directly to `main`.
- Keep changes limited to the assigned feature where possible.
- Test before opening a Pull Request.
- Human review is required before merge.

## Security

- Never commit `.env`, passwords or secret keys.
- Use environment variables for Supabase configuration.