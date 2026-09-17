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

ConnectSphere supports five main roles:

1. Event Organiser
2. Event Coordinator
3. Venue Staff
4. Technical Support Staff
5. Attendee

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
│
├── app/
│   ├── app.py
│   ├── supabase_client.py
│   ├── routes/
│   ├── services/
│   ├── templates/
│   └── static/
│
├── docs/
│   ├── architecture/
│   │   ├── common_structure.md
│   │   └── project_context.md
│   ├── uml/
│   └── user-stories/
│
├── tests/
├── .github/
├── .env.example
├── .gitignore
├── AGENTS.md
├── README.md
└── requirements.txt
```

## Shared Project Context

Detailed information about the current ConnectSphere architecture, database, status values, business rules, Supabase setup, frontend baseline and development decisions is documented in:

```text
docs/architecture/project_context.md
```

Developers and AI coding agents should review this file before implementing a user story.

The concise architecture and service-ownership reference is located at:

```text
docs/architecture/common_structure.md
```

## Shared Development Instructions

Development and AI-agent rules are documented in:

```text
AGENTS.md
```

These instructions cover areas such as:

- frontend consistency
- route and service structure
- database restrictions
- Git workflow
- security
- user-story scope

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

## AI Coding Context

When using an AI coding assistant, provide:

```text
1. README.md
2. AGENTS.md
3. docs/architecture/project_context.md
4. docs/user-stories/<relevant-story>.md
5. Relevant UML, if applicable
```

Different team members may use different AI tools, but all AI agents should receive the same shared project context.

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