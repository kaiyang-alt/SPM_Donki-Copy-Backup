# Secure Access to Event Organiser Account

## User Story

As an Event Organiser, I want to securely log in to my account so that I can access and manage only the event information I am authorised to use.

## Acceptance Criteria

The Event Organiser can:

- Log in using registered account credentials.
- Access the system when valid credentials are provided.
- Be denied access when invalid credentials are provided.
- Access Event Organiser functionality after successful authentication.
- View and modify only event information that the Event Organiser is authorised to manage.
- Be prevented from accessing event information that the Event Organiser is not authorised to manage.
- Log out of the account and end the authenticated session.

## Relevant Customer Clarifications

- All users are authenticated users.
- A user may hold more than one role.
- Staff onboarding is outside the scope of the first release, so test accounts may be pre-created.
- Existing Supabase Authentication should be used.
- Existing Row Level Security policies should be respected for authorised data access.

## Preconditions / Dependencies

- The Event Organiser has an existing registered Supabase Auth account.
- The Event Organiser has an associated `profile` record.
- The Event Organiser has the `event_organiser` role in `user_role`.
- At least one event exists that the Event Organiser is authorised to access.
- At least one unrelated event exists that the Event Organiser is not authorised to manage.
- The shared Supabase client and authentication configuration are available.

## Test Case Reference

`docs/test-cases/event-organiser-login.md`

## Relevant UML Reference

`docs/uml/event-organiser-login.puml`

## Implementation Notes

- Use the existing Supabase Authentication setup.
- Do not introduce a new authentication mechanism.
- The current role switcher in the prototype is for demonstration only and is not the final authentication flow.
- The authentication story should implement the real login and logout experience.
- Authorised event access should rely on the existing application access model and Row Level Security.
- Organisers may edit their own events in `draft`, `requested`, or `changes_requested` status.
- Do not introduce a new `organisation` entity solely for this story.
