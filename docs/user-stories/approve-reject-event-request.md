# Approve or Reject a Submitted Event Request

## User Story

As an Event Coordinator, I want to formally approve or reject a submitted
event request so that the organiser knows whether their event can proceed to
venue and resource booking.

## Acceptance Criteria

- **AC1:** Provide distinct `Approve` and `Reject` action controls on the Event
  Review interface.
- **AC2:** Require a mandatory text feedback field if the request is marked as
  `Rejected`.
- **AC3:** Update the event status to `Approved` or `Rejected` in the Event
  Service database.
- **AC4:** Enable downstream venue and equipment reservation actions only when
  the status is `Approved`.
- **AC5:** Dispatch an automated notification containing the status outcome and
  feedback notes to the Event Organiser.
- **AC6:** Log status-change timestamps and coordinator details in the event
  audit history.

## Requirement Source

- The User Story and Acceptance Criteria were supplied by the developer from
  the assigned story's AC checklist on 21 October 2026.
- `Approved` and `Rejected` are retained here exactly as stated in the supplied
  Acceptance Criteria.

## Confirmed Customer Clarifications

- `Approved` is the user-facing decision label and maps to the new persisted
  event status `approved`.
- `Rejected` maps to the existing persisted event status `rejected`.
- Automatic coordinator assignment must leave a newly submitted event in
  `requested` until the assigned Coordinator makes this formal decision.
- The assigned Coordinator may approve or reject an event in `requested` or
  `changes_requested` after reviewing any organiser clarification.
- Rejection feedback is mandatory. Approval feedback is optional; when no
  approval feedback is entered, the organiser notification uses a default
  approval message.
- An approved event remains in `approved` while venue and equipment
  arrangements are made. When all confirmation requirements are satisfied,
  the event transitions directly from `approved` to `confirmed`.
- The event audit identifies the deciding Coordinator through
  `event_action_log.actor_id`; no Coordinator name or email snapshot is added.
- These clarifications and shared workflow decisions were confirmed by the
  developer and team on 22 October 2026.

## Preconditions / Dependencies

- The Event Coordinator is authenticated through the existing Supabase
  Authentication setup and has the `event_coordinator` role.
- The submitted event request exists and is assigned to the Event Coordinator.
- The existing Event Review interface and service expose the submitted request
  and its review information.
- The Coordinator's authenticated RLS context permits the required event
  update and audit-history insertion.
- The notification workflow permits an automated notification to be inserted
  for the Event Organiser.
- Venue and equipment reservation workflows must use the approved shared event
  status decision when determining eligibility.

## Cross-Story Impacts

- `event-assignment` currently states that automatic assignment changes an
  event from `requested` to `planning`. That transition may bypass the formal
  approval or rejection required by this story. The assignment story owner and
  team must reconcile this shared workflow; this story does not modify the
  assignment story.
- `event-coordinator-review-event-request` currently treats a satisfactory
  review as a transition to `planning`. Its clarification workflow shares the
  Event Review interface with this story, but its canonical requirements are
  not changed here.
- `submit-venue-booking` currently permits booking only for events in
  `planning`. Its owner must change that eligibility check to `approved`.
- The equipment-reservation owner must be informed of the same `approved`
  eligibility decision. That feature remains owned by its teammate and is not
  implemented by this story.
- `track-readiness-actions` currently confirms events from `planning`. Its
  owner must change the eligible source status to `approved` so a ready event
  transitions from `approved` to `confirmed`.

## Shared Architecture Decisions

- The team approved `approved` as a new persisted event status. The live
  `events_status_check` constraint was updated and verified on 27 October 2026
  to permit `approved` while preserving every existing event status. The
  shared status catalogue and dependent workflows still require reconciliation.
- Keeping an automatically assigned event in `requested` changes the shared
  assignment workflow currently documented by the `event-assignment` story and
  requires coordination with that story owner.
- The team-approved RLS policies for review audit-history access and inserts,
  Coordinator-to-Organiser decision notifications, sender access to returned
  decision notifications, and clarification messages were applied in Supabase
  and recorded in
  `docs/architecture/database_schema.md`.
- The existing `event_action_log` columns represent the actor, old and new
  statuses, details, and creation timestamp.

## Test Case Reference

`docs/test-cases/approve-reject-event-request.md`

## Relevant UML Reference

- No new UML is required. The existing Event Review interaction is reused.

## Implementation Notes

- Reuse the existing Event Review interface, route, and service rather than
  creating a duplicate review workflow.
- Persist `approved` for an approval decision and `rejected` for a rejection
  decision, following the team-approved shared status decision.
- Do not change another story's canonical requirements from this story branch.
- No new table, column, authentication method, or dependency is introduced.
