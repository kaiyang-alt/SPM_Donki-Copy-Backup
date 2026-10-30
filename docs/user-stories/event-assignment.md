# Assign an Event Request

## User Story

As an Event Coordinator, I want submitted event requests to be automatically assigned to one Event Coordinator so that every event has a clear owner for its planning and execution.

## Acceptance Criteria

- AC1: When an event request is submitted (status `requested`) without a coordinator, the system automatically assigns an Event Coordinator.
- AC2: An event must have no more than one assigned Event Coordinator.
- AC3: On assignment, the event's `coordinator_id` is set and its status transitions from `requested` to `planning`.
- AC4: The assigned coordinator automatically receives a notification confirming ownership of the event.
- AC5: The event organiser automatically receives a notification that a coordinator has been assigned to their event.
- AC6: An event that already has a coordinator is not reassigned by automatic assignment.
- AC7: An Event Coordinator can view the events assigned to them in the `Assigned Events` section of the coordinator workspace.
- AC8: An Event Organiser can see on their event whether an Event Coordinator has been assigned, including the coordinator’s name.

## Relevant Customer Clarifications

- Each event must be automatically assigned to an Event Coordinator and must have no more than one assigned coordinator.
- Reassignment requires offline agreement between coordinators; the original coordinator initiates it and the new coordinator must accept. The reassignment workflow and UI are out of scope for this story.
- `Submitted` maps to the existing status `requested`; `In Review` maps to `planning`.
- Notifications are created automatically by the system, not by a user.

## Open Questions / Unresolved Requirements

- The customer has not specified how the system selects an Event Coordinator. The coordinator-selection algorithm remains unresolved, and no particular selection rule may be assumed until it is clarified.

## Preconditions / Dependencies

- The event request creation/submission story produces events with status `requested` and no coordinator.
- At least one user has the `event_coordinator` role.
- Notification display belongs to the notification story; until it exists, notifications can be verified in the `notification` table.

## Test Case Reference

`docs/test-cases/event-assignment.md`

## Relevant UML Reference

- Not required.

## Implementation Notes

- The current repository provides read-only views of assignment state but does not contain a confirmed automatic-assignment implementation.
- There is no confirmed database assignment SQL file or named automatic-assignment trigger implementation in the current repository.
- The automatic-assignment mechanism and coordinator-selection basis remain unresolved.
