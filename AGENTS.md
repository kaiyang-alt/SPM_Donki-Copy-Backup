# ConnectSphere Development Instructions

## Required Context Before Implementation

Before implementing any user story, review:

1. `README.md` for the repository and development overview.
2. `docs/requirements/README.md` for requirement precedence.
3. `docs/architecture/project_context.md` for the current reconciled project
   baseline.
4. `docs/architecture/database_schema.md` for the current approved/documented
   database structure.
5. The relevant file under `docs/user-stories/`.
6. The corresponding functional test specification under `docs/test-cases/`,
   where applicable.
7. Relevant UML under `docs/uml/`, if applicable.

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

- Use the current approved/documented database structure in
  `docs/architecture/database_schema.md`.
- Do not independently invent or modify tables, columns, relationships,
  constraints, statuses or Row Level Security policies.
- Shared database or RLS changes require team approval.
- When an approved schema change is implemented,
  `docs/architecture/database_schema.md` must also be updated as part of the
  approved implementation workflow.

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

## Repository Integrity and Structure Protection

### Default Rule

Do not delete, rename, move, replace or reorganise an existing tracked file or
directory unless both:

1. The assigned task genuinely requires the structural change.
2. The developer or team explicitly approves it.

### Before Creating a New File

- Check whether an equivalent canonical file already exists.
- Check whether the functionality belongs in an existing file.
- If a shared or documented file appears unexpectedly missing, inspect Git
  history where appropriate before creating a replacement.
- Prefer restoring the canonical file instead of creating duplicate `-v2`,
  `-new`, `-final` or `-latest` files.

### Shared / Structural Files

Treat at minimum the following as shared infrastructure:

- `README.md`
- `AGENTS.md`
- `.gitignore`
- `.env.example`
- `.github/`
- `app/app.py`
- `app/supabase_client.py`
- `docs/architecture/`
- `docs/requirements/`
- `docs/implementation/`
- `scripts/`
- `pytest.ini`
- `requirements.txt`

These files and directories may be modified when legitimately required, but
changes must remain minimal and scoped.

### Story Files

Agents may update canonical files belonging to the assigned story, including:

- `docs/user-stories/<story-name>.md`
- `docs/test-cases/<story-name>.md`
- relevant route, service, frontend and test files

Do not modify another developer's story merely because it is related. Flag
cross-story impacts instead.

### Deletion Rule

If an existing tracked file appears obsolete and deletion is proposed, stop and
report:

- the file or path
- why it appears obsolete
- its references and dependencies
- whether a canonical replacement exists
- the likely impact of deletion

Explicit approval is required before deletion.

### Structural Change Rule

Explicit approval is required before:

- deleting, renaming or moving files or folders
- merging or splitting canonical files
- introducing a new top-level directory
- reorganising routes, services or tests
- changing the shared application structure

Do not perform structural refactoring merely for cleanliness.

### Preserve Working Structure

Prefer the smallest coherent change. Avoid unrelated formatting or rewrite
churn.
