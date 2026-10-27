# Assign an Unassigned Event Request

## User Story

As an Event Coordinator Lead, I want to assign an unassigned event request to an Event Coordinator so that the request has a clear owner for planning.

## Acceptance Criteria

- AC1: The Event Coordinator Lead can select an unassigned event request.
- AC2: The Event Coordinator Lead can view active Event Coordinators available for assignment.
- AC3: The Event Coordinator Lead manually selects one Event Coordinator for the request; no automatic selection algorithm is used.
- AC4: An event has no more than one assigned Event Coordinator at any point in time.
- AC5: The selected Event Coordinator is displayed as the current Coordinator after successful assignment.
- AC6: The event request is no longer shown as unassigned after successful assignment.
- AC7: The assigned Event Coordinator can access and manage the event through the Coordinator workflow.
- AC8: Another Event Coordinator does not gain management access merely by holding the Event Coordinator role.
- AC9: Successful assignment notifies the assigned Event Coordinator and Event Organiser.
- AC10: Unauthorised roles cannot assign an Event Coordinator.

## Relevant Customer Clarifications

- The Event Coordinator Lead is a new application role.
- The database role value is `event_coordinator_lead`, which is distinct from `event_coordinator`.
- A successful assignment notifies the newly assigned Event Coordinator and the Event Organiser.
- The event remains in the existing `requested` status after assignment.
- Coordinator selection is manual; no automatic best-Coordinator algorithm is used.
- Only users with an active profile and the `event_coordinator` role are available for selection.

## Preconditions / Dependencies

- The Event Coordinator Lead is authenticated and authorised to perform assignments.
- The selected event request has no assigned coordinator.
- At least one Event Coordinator is available for selection.
- The shared authentication flow must support the `event_coordinator_lead` role.
- RLS must permit a Lead to view requested events, view Event Coordinator identities, assign an unassigned requested event, and create the approved notifications.
- The existing automatic coordinator-assignment trigger must be disabled so submitted requests can remain unassigned for Lead assignment.

## Test Case Reference

Planned functional test specification:

`docs/test-cases/event-coordinator-lead-assign-unassigned-event.md`

## Relevant UML Reference

No story-specific UML is currently documented.

## Implementation Notes

- Reuse `event.coordinator_id` to record the assigned Event Coordinator unless the team approves a schema change.
- Use existing event status values; do not introduce a new assignment status.
- Follow the shared `route -> service/business logic -> Supabase` flow.
- Assignment updates `event.coordinator_id` without changing the event's `requested` status.
- Assignment notifications use the existing `notification` table and the `coordinator_assigned` notification type.
- The story-specific database migration disables the old automatic-assignment trigger and adds narrowly scoped Lead RLS policies.
- The approved transactional assignment function validates the Lead, request and active Coordinator, then saves the assignment and both notifications atomically.
- A database trigger prevents `event.coordinator_id` changes by non-Lead callers even when another permissive event-update policy applies.
