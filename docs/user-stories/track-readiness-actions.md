# Track Event Readiness and Outstanding Actions

## User Story

As an Event Coordinator, I want to view the readiness and outstanding actions for an assigned event so I can identify what remains before confirming the event.

## Acceptance Criteria

The Event Coordinator can:

- View the status of the venue booking, equipment reservations, programme setup, and event tasks.
- Treat venue arrangements as complete only when the venue booking has status `Confirmed`.
- Treat equipment arrangements as complete only when every required equipment reservation has status `Confirmed`, or the event explicitly records `No equipment required`.
- Treat programme setup as complete only when its status is `Completed`.
- Treat event tasks as complete only when every task has status `Completed`. If no tasks exist, this condition is satisfied.
- View each unfinished task with its responsible person and deadline. An unfinished task whose deadline has passed is marked `Overdue`.
- See readiness displayed as `Incomplete` if any readiness condition is unmet, with each outstanding booking, reservation, programme action, or task identified.
- See readiness displayed as `Ready for Confirmation` only when all readiness conditions are met. The displayed readiness is refreshed after a relevant status change is saved.
- Have current readiness checked when confirming an event. If any condition remains unmet, confirmation is prevented, the event retains its existing status, and outstanding actions are displayed. If all conditions are met, the event status is updated to `confirmed`.

## Preconditions / Dependencies

- The Event Coordinator is authenticated and has the `event_coordinator` role.
- An event is assigned to the Event Coordinator and has an existing event status.
- Venue booking and equipment reservation records are available for the event where required.
- Programme setup and event task information, including task status, responsible person, and deadline, must be available to the readiness view. These data sources are not present in the currently documented database schema and require confirmation.
- The event must be able to explicitly record `No equipment required`. This field or mechanism is not present in the currently documented event schema and requires confirmation.

## Test Case Reference

`docs/test-cases/track-readiness-actions.md`

## Implementation Notes

- Use existing `confirmed` as the event status after successful confirmation; do not introduce a new event status.
- `Incomplete`, `Ready for Confirmation`, and `Overdue` are readiness/task display labels, not new event status values.
- Confirm how programme setup, event tasks, task responsibility/deadlines, and the explicit no-equipment-required choice are stored before implementation. Do not introduce database structures or status values without team agreement.
