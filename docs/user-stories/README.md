# User Stories

This folder stores the implementation context for ConnectSphere user stories.

Each user story should have its own Markdown file.

## File Naming

Recommended naming format:

```text
<story-name>.md
```

Example:

```text
event-change-request.md
```

## Required Story Content

Each user-story document should include, where applicable:

- User Story
- Acceptance Criteria
- Test Cases
- Relevant Customer Clarifications
- Preconditions / Dependencies
- Relevant UML Reference
- Implementation Notes

## Suggested Story Template

```md
# <User Story Name>

## User Story

As a <role>, I want to <goal> so that <reason>.

## Acceptance Criteria

- AC1:
- AC2:
- AC3:

## Test Cases

- TC1:
- TC2:
- TC3:

## Relevant Customer Clarifications

- Add only clarifications relevant to this story.

## Preconditions / Dependencies

- List any required functionality, data, authentication, setup or dependency that must exist before this story can work.

## Relevant UML Reference

- Add the path to the relevant UML file if applicable.

Example:

`docs/uml/event-change-request-sequence.md`

## Implementation Notes

- Add important implementation decisions or constraints here.
- Keep notes within the scope of this user story.
```

## Usage Rules

Developers and AI coding agents should review the relevant user-story document before implementation.

Only include information required to implement and test that story.

Do not add unrelated requirements or redesign shared architecture within a user-story document.

If the story requires a change to the shared:

- database schema
- authentication model
- status values
- Row Level Security design
- frontend structure
- shared architecture

raise it with the team before implementation.

## AI Context

When using an AI coding assistant for a user story, provide:

```text
README.md
AGENTS.md
docs/architecture/project_context.md
docs/user-stories/<relevant-story>.md
Relevant UML, if applicable
```

The user-story document should define the scope of the feature being implemented.

The AI should not invent missing requirements or make shared architectural changes outside the story scope.