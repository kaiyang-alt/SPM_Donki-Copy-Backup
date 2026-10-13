# Review Event Request

## User Story

As an Event Coordinator, I want to review event requests assigned to me by the Event Coordinator Lead so that I can identify missing or unclear requirements and manage the clarification process.

## Acceptance Criteria

- AC1: A newly submitted event request enters the Event Coordinator Lead's unassigned queue.
- AC2: The Event Coordinator Lead must assign the request before an Event Coordinator can manage or review it.
- AC3: The assigned Event Coordinator can view and review the complete event request details.
- AC4: An Event Coordinator cannot take ownership of an unassigned event request directly.
- AC5: An Event Coordinator cannot manage or review a request assigned to another coordinator.
- AC6: The assigned Event Coordinator is displayed on the event request.
- AC7: The assigned Event Coordinator can identify requirements that are missing, incomplete, or unclear.
- AC8: The assigned Event Coordinator can send a clarification message to the Event Organiser and set the displayed status to "Clarification Required".
- AC9: The assigned Event Coordinator can review amendments submitted by the Event Organiser and update the request status accordingly.

## Relevant Customer Clarifications

- `event_coordinator_lead` and `event_coordinator` are distinct roles.
- A newly submitted request remains `requested` and unassigned until an Event Coordinator Lead assigns it.
- Assignment uses `event.coordinator_id` and does not change the `requested` status.
- "Clarification Required" is the display label for the existing `changes_requested` event status.
- After satisfactory review, the coordinator moves the event to `planning`. If more clarification is needed, the coordinator requests it using `changes_requested`.
- "Venue" in this story means the organiser's venue requirements.
- Clarification messages and organiser responses are recorded in `event_action_log.details`, with workflow actions in `action_type`. No separate clarification or response columns are added.

## Preconditions / Dependencies

- The Event Coordinator Lead assignment workflow is implemented.
- The request has status `requested` and an Event Coordinator Lead assigns exactly one Event Coordinator through `event.coordinator_id`.
- The Event Organiser owns the request through `event.organiser_id`.
- Existing RLS policies permit only the relevant organiser, assigned coordinator, and Event Coordinator Lead to perform their authorised actions.

## Test Case Reference

`docs/test-cases/event-coordinator-review-event-request.md`

## Relevant UML Reference

- Not required.

## Implementation Notes

- The existing Supabase login endpoint supports coordinator role verification as well as organiser login.
- Assigned coordinators review request details, equipment reservations, and clarification history. Organisers open events requiring clarification from My Events and submit responses or amendments to documented event fields.
- Organiser responses leave the event in `changes_requested` until coordinator review.
- Event updates, audit entries, and notifications use separate authenticated Supabase calls under existing RLS. A partial failure is reported explicitly; these writes are not an atomic database transaction.
