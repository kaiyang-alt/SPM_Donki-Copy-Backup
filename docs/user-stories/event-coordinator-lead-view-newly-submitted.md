# View Newly Submitted Unassigned Event Requests

## User Story

As an Event Coordinator Lead, I want to view newly submitted unassigned event requests so that I can identify requests that require coordinator assignment.

## Acceptance Criteria

- AC1: The Event Coordinator Lead can view submitted event requests that do not yet have an assigned Event Coordinator.
- AC2: The Event Coordinator Lead can view basic event information needed to support assignment.
- AC3: Unassigned requests are distinguishable from already assigned requests.
- AC4: Only a user authenticated with the appropriate role can access the unassigned queue.

## Relevant Customer Clarifications

- The Event Coordinator Lead is a new application role.
- The database role value is `event_coordinator_lead`.
- Submitted event requests use the existing `requested` event status.
- Basic event information includes the event ID, name, `requested` status, preferred start and end dates, expected attendance, and unassigned state.

## Preconditions / Dependencies

- The Event Coordinator Lead is authenticated through the existing Supabase Authentication flow.
- Newly submitted requests can remain in status `requested` with `event.coordinator_id` unset.
- The shared role model, authentication support, and RLS policies for the Event Coordinator Lead must be available.
- The automatic coordinator-assignment trigger must remain disabled so newly submitted requests can enter this queue.

## Test Case Reference

Planned functional test specification:

`docs/test-cases/event-coordinator-lead-view-newly-submitted.md`

## Relevant UML Reference

No story-specific UML is currently documented.

## Implementation Notes

- Use the existing `requested` status and a null `event.coordinator_id`; do not introduce a new event status for the queue.
- Enforce queue access through the existing authentication and RLS model.
- Reuse the unassigned-request query and queue established by the Lead assignment story.
- Follow the shared `route -> service/business logic -> Supabase` flow.
