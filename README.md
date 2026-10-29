# SPM_Donki

# ConnectSphere Event Management System

IS212 Software Project Management  
AY 2026/27 Term 1

## Project Overview

ConnectSphere is a role-based event management system developed as part of the IS212 Software Project Management course.

The system supports:

- Event request creation and approval
- Event coordination
- Venue search and booking
- Equipment management
- Attendee registration
- Event change requests
- Coordinator reassignment
- Notifications

## User Roles

ConnectSphere supports six main roles:

1. Event Organiser
2. Event Coordinator
3. Event Coordinator Lead
4. Venue Staff
5. Technical Support Staff
6. Attendee

A user may hold more than one role.

## Technology Stack

| Area | Technology |
| --- | --- |
| Programming Language | Python |
| Web Framework | Flask |
| Database | Supabase / PostgreSQL |
| Authentication | Supabase Auth |
| Frontend | HTML / CSS / JavaScript |
| Testing | pytest |
| CI | GitHub Actions |
| Version Control | GitHub |
| Project Management | Trello |
| Architecture | Service-oriented Flask application |

## Project Structure

```text
SPM_Donki/
├── app/
│   ├── routes/
│   ├── services/
│   ├── static/
│   ├── templates/
│   ├── app.py
│   └── supabase_client.py
├── docs/
│   ├── architecture/
│   ├── requirements/
│   ├── user-stories/
│   ├── test-cases/
│   ├── implementation/
│   └── uml/
├── scripts/
├── tests/
├── .github/
├── .env.example
├── .gitignore
├── AGENTS.md
├── pytest.ini
├── README.md
└── requirements.txt
```

## Documentation Map

| Document / Area | Purpose |
| --- | --- |
| `AGENTS.md` | Development and AI-agent guardrails |
| `docs/requirements/README.md` | Requirement precedence and customer-change process |
| `docs/architecture/common_structure.md` | Quick architecture and repository reference |
| `docs/architecture/project_context.md` | Current reconciled shared project baseline |
| `docs/architecture/database_schema.md` | Current approved/documented database structure |
| `docs/user-stories/` | Canonical User Story cards |
| `docs/test-cases/` | Functional test specifications |
| `docs/implementation/user-story-implementation-prompt.md` | Primary AI-assisted story workflow and orchestration entry point |

## Local Setup

### 1. Pull the latest main branch

```bash
git switch main
git pull origin main
```

### 2. Create a Python virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

For Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Create a local `.env`

Create a local `.env` file based on:

```text
.env.example
```

Add the shared Supabase project values:

```text
SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=
```

Do not commit `.env`, passwords, access tokens or secret keys.

### 6. Run the application

From the repository root:

```bash
python -m app.app
```

### 7. Open the application

Open the local Flask URL shown in the terminal.

Normally:

```text
http://127.0.0.1:5000
```

## Testing

Run all automated tests with:

```bash
python -m pytest
```

Tests should pass before opening a Pull Request.

GitHub Actions also runs pytest automatically for Pull Requests targeting `main` and pushes to `main`.

## Development Workflow

Before starting a story:

```bash
git switch main
git pull origin main
```

Create a short-lived branch:

```bash
git switch -c feat/<feature-name>
```

Development should follow:

```text
Frontend → Flask Route → Service / Business Logic → Supabase
```

<<<<<<< HEAD
General rules:

- New Flask routes belong in `app/routes/`
- Business logic belongs in `app/services/`
- Reuse the existing Supabase client
- Reuse the approved ConnectSphere frontend baseline
- Keep changes within the assigned story where possible
- Do not commit directly to `main`
- Test before opening a Pull Request
- Human review is required before merge

## User Story Documentation

Story-specific implementation context belongs in:

```text
docs/user-stories/
```

A story document may contain:

- User Story
- Acceptance Criteria
- Test Cases
- Relevant Customer Clarifications
- Preconditions / Dependencies
- Relevant UML reference

## UML

Relevant UML belongs in:

```text
docs/uml/
```

Use just-enough UML where it helps clarify implementation.

Sequence diagrams are useful where interaction order or alternative flows matter.

Class diagrams may be used where code-level structure needs clarification.

## Shared AI Prompts

ConnectSphere uses two shared AI prompts to keep development consistent across the team.

### Functional Test Case Design

Use:

```text
docs/test-cases/functional-test-case-prompt.md
```

This prompt is used before implementation to derive functional test cases from the approved user story, acceptance criteria and relevant customer clarifications.

The completed functional test specification should be stored under:

```text
docs/test-cases/<story-name>.md
```

### User Story Implementation

Use:

```text
docs/implementation/user-story-implementation-prompt.md
```

This prompt is used after the story requirements and functional test cases have been reviewed.

It instructs the AI to implement only the assigned user story while following the existing ConnectSphere architecture, database, RLS, authentication and frontend rules.

## AI Coding Context

Different team members may use different AI coding tools, but all AI agents should receive the same shared project context.

### Test-Design Stage

Provide:

```text
README.md
AGENTS.md
docs/architecture/project_context.md
docs/user-stories/<relevant-story>.md
docs/test-cases/functional-test-case-prompt.md
Relevant UML, if applicable
```

The generated functional test specification should be reviewed by a human and stored in:

```text
docs/test-cases/<relevant-story>.md
```

### Implementation Stage

Provide:

```text
README.md
AGENTS.md
docs/architecture/project_context.md
docs/implementation/user-story-implementation-prompt.md
docs/user-stories/<relevant-story>.md
docs/test-cases/<relevant-story>.md
Relevant UML, if applicable
```

The AI should implement only the assigned story and follow the shared ConnectSphere development rules.

## Security

Never commit:

```text
.env
Supabase keys
Passwords
Access tokens
Test-account credentials
Other secrets
```

Use environment variables or approved private team channels for sensitive information.
=======
Use `AGENTS.md` for the full development, security, scope and repository-integrity
rules. Test changes before opening a Pull Request, and obtain human review before
merge.
>>>>>>> 3da8002c1dc7118685c899081164b59f9ec66f43
