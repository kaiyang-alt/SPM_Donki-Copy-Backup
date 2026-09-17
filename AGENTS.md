# ConnectSphere Development Instructions

## Required Context Before Implementation

Before implementing any user story, review:

1. `README.md`
2. `docs/architecture/project_context.md`
3. The relevant file under `docs/user-stories/`
4. Relevant UML under `docs/uml/`, if applicable

Use `AGENTS.md` as the development rules for implementation.

Do not rely on the frontend prototype alone for business rules. Where prototype behaviour conflicts with confirmed requirements, follow the confirmed requirements and shared project context.

## Shared Frontend

- Use the existing ConnectSphere frontend as the shared UI baseline.
- Do not redesign the application or introduce a separate design system.
- Reuse the existing layout, navigation, styling and interaction patterns.
- Replace prototype/mock behaviour only when implementing the relevant user story.
- Treat `app/templates/index.html`, `app/static/css/styles.css` and `app/static/js/app.js` as shared baseline files.
- Do not replace or restructure these files wholesale for an individual story.
- Keep story-specific changes as isolated as practical and coordinate before making large changes to shared frontend files.

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