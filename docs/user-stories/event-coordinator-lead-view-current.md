# View Current Event Coordinator Assignments

## User Story

As an Event Coordinator Lead, I want to view current Event Coordinator assignments so that I can oversee active events under my supervision.

## Acceptance Criteria

- AC1: The Event Coordinator Lead can view active events with their currently assigned Event Coordinator.
- AC2: The Event Coordinator Lead can identify submitted events that remain unassigned.
- AC3: The Event Coordinator Lead can view basic event information associated with each assignment.
- AC4: Assigned events are clearly distinguished from unassigned event requests.
- AC5: The Event Coordinator Lead can open an assigned event and view its current Coordinator assignment.
- AC6: Assignment information refreshes after assignment or reassignment is completed.
- AC7: Only an authenticated Event Coordinator Lead can access the assignment overview and assigned-event details.

## Relevant Customer Clarifications

- The Event Coordinator Lead is a new application role.
- Active events use the existing `requested`, `changes_requested`, `planning`, and `confirmed` statuses.
- Basic event information includes the event ID, name, status, preferred or confirmed dates, and current Event Coordinator.
- The current schema has no Lead-to-event relationship, so every active event is under the supervision of an authenticated Event Coordinator Lead.
- Until a narrower supervision relationship is confirmed and added to the schema, the overview must not invent one and therefore shows all active events.

## Preconditions / Dependencies

- The Event Coordinator Lead is authenticated and authorised to view assignment information.
- Assigned events use `event.coordinator_id` to identify their current Event Coordinator.
- Unassigned event requests have no value in `event.coordinator_id`.
- The shared role model and authentication support for the Event Coordinator Lead must be available.
- RLS must permit an Event Coordinator Lead to view active events and Event Coordinator identities.

## Test Case Reference

Planned functional test specification:

`docs/test-cases/event-coordinator-lead-view-current.md`

## Relevant UML Reference

No story-specific UML is currently documented.

## Implementation Notes

- Use existing event and profile information; do not introduce duplicate assignment storage.
- Use the confirmed active-event statuses, supervision scope, and basic information fields documented above.
- Assigned-event details are available only for active events that currently have a Coordinator.
- Follow the shared `route -> service/business logic -> Supabase` flow.
