# Review Event Request

## User Story

As an Event Coordinator, I want to review event requests assigned to me by the
Event Coordinator Lead so that I can identify missing or unclear requirements.

## Acceptance Criteria

- AC1: An Event Coordinator can access for review only event requests assigned
  to them by the Event Coordinator Lead. The existing `event.coordinator_id`
  identifies the assigned coordinator.
- AC2: An Event Coordinator cannot view or submit a review decision for an
  unassigned event request or an event request assigned to another coordinator.
- AC3: For an authorised event request, the assigned Event Coordinator can view
  the event name, requested date and time, venue requirements, expected
  attendance, event requirements, and requested equipment or resources.
- AC4: The assigned Event Coordinator can identify requirements that are
  missing, incomplete, or unclear from the information supplied. Automatic gap
  detection is not required.
- AC5: The assigned Event Coordinator can request clarification or amendments
  by sending a clarification message to the Event Organiser and changing the
  event status to `changes_requested`, displayed as **Clarification Required**.
- AC6: The Event Organiser receives the clarification message and can provide
  the requested information or amendments.
- AC7: An organiser response leaves the event in `changes_requested` until the
  assigned Event Coordinator reviews the updated request.
- AC8: After reviewing the organiser's clarification or amendments, the
  assigned Event Coordinator can either request further clarification or move
  a satisfactory request to `planning`.

## Relevant Customer Clarifications

- The Event Coordinator Lead assigns event requests to Event Coordinators.
- A coordinator may review only event requests assigned to that coordinator by
  the Event Coordinator Lead.
- The existing `event.coordinator_id` remains the source used by the review
  workflow to identify the assigned coordinator. This story does not add a
  second assignment field or require assignment-provenance data.
- **Clarification Required** is the display label for the existing
  `changes_requested` event status.
- After a satisfactory review, the assigned coordinator moves the event to
  `planning`. If more clarification is needed, the coordinator requests it
  using `changes_requested`.
- **Venue** in this story means the organiser's venue requirements.
- Clarification messages and organiser responses are recorded in
  `event_action_log.details`, with workflow actions in `action_type`. No
  separate clarification or response columns are required by this story.

## Preconditions / Dependencies

- The user is authenticated through the existing Supabase Authentication
  setup and holds the `event_coordinator` role.
- The Event Coordinator Lead assignment workflow must establish which event is
  assigned to which coordinator by setting the existing
  `event.coordinator_id` before coordinator review is permitted.
- The assignment and read/write permissions must prevent a coordinator from
  treating an unassigned event or another coordinator's event as their own.
- Organiser ownership continues to use `event.organiser_id`.
- The Event Coordinator Lead implementation exists on its dedicated feature
  branches and must be integrated before this story is deployed. Its migrations
  and RLS must be verified as part of that shared integration.

## Test Case Reference

`docs/test-cases/event-coordinator-review-event-request.md`

## Relevant UML Reference

- No story-level UML is currently required. Reassess during implementation
  readiness if the approved Lead assignment interaction needs sequence-level
  clarification.

## Implementation Notes

- Preserve the existing route -> service/business logic -> Supabase flow and
  existing authentication setup.
- Assigned coordinators review request details, equipment reservations, and
  clarification history. Organisers open events requiring clarification from
  My Events and submit responses or amendments to documented event fields.
- Organiser responses leave the event in `changes_requested` until coordinator
  review.
- Event updates, audit entries, and notifications use separate authenticated
  Supabase calls under existing RLS. A partial failure is reported explicitly;
  these writes are not an atomic database transaction.
- Preserve the existing coordinator-review implementation that authorises
  access by matching the authenticated coordinator to `event.coordinator_id`.
  The approved Lead workflow and RLS own assignment writes to that field; this
  review story must not duplicate that shared assignment implementation.

## Requirement Revision

- The original review and clarification requirements remain in force.
- The story is modified additively so that coordinator review is restricted to
  event requests assigned to that coordinator by the Event Coordinator Lead.
- Existing review routes, service behavior, clarification handling, status
  transitions, notifications, and frontend behavior remain unchanged unless a
  scoped authorization adjustment is required by the verified Lead-assignment
  migration.
- This changes the shared assignment workflow currently described as automatic
  assignment in `docs/architecture/project_context.md`. Per the shared baseline
  synchronisation rule, that document is not changed on this individual story
  branch and must be reconciled during the approved shared baseline task.

