# Assign an Event Request

## User Story

As an Event Coordinator, I want to assign an unassigned event request to myself (or a team member) so that I can take ownership of its planning and execution.

## Acceptance Criteria

The Event Coordinator can:

- View an `Unassigned Requests` queue on the Event Coordinator workspace.
- Assign an unassigned request using an `Assign to Me` button or a dropdown list of active Event Coordinators.
- Have the event's `coordinator_id` field updated upon assignment via the Event Service.
- Transition the event status from `Submitted` to `In Review`.
- Trigger an automated notification to the assigned coordinator confirming ownership.
- Be prevented from claiming an event once a coordinator has already been assigned.

## Preconditions / Dependencies

- The Event Coordinator is authenticated and has the `event_coordinator` role.
- An event request exists with no assigned coordinator.
- The `event` table has a nullable `coordinator_id` field, and active coordinator accounts can be identified from `profile.active` and the `event_coordinator` role in `user_role`.
- The event assignment action must be supported by the existing Event Service and Row Level Security policies. The currently documented coordinator update policy permits updates only when the acting coordinator is already assigned to the event, so support for assigning an unassigned event is unconfirmed.
- Automated notification delivery requires permission to create a record in the existing `notification` table. The currently documented Row Level Security policies do not specify notification insertion permissions.

## Test Case Reference

`docs/test-cases/event-assignment.md`

## Implementation Notes

- The current shared project context states that each submitted event must have exactly one coordinator and coordinator assignment should use a fair automatic assignment approach. Manual self-assignment or selection of a team member differs from this rule and requires team confirmation before implementation.
- The current event statuses are `requested`, `planning`, and other documented values; `Submitted` and `In Review` are not current event status values. Confirm the intended status mapping with the team rather than introducing new statuses without approval.
- Assigning an event to another coordinator requires a decision about who is authorized to make that assignment and must respect the existing RLS design.
