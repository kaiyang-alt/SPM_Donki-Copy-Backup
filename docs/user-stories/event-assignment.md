# Assign an Event Request

## User Story

As an Event Coordinator, I want submitted event requests to be automatically and fairly assigned to exactly one Event Coordinator so that every event has a clear owner for its planning and execution.

## Acceptance Criteria

- AC1: When an event request is submitted (status `requested`) without a coordinator, the system automatically assigns exactly one Event Coordinator.
- AC2: Only users with the `event_coordinator` role and `profile.active = true` are eligible for assignment.
- AC3: Assignment is fair: the eligible coordinator with the lowest active workload (assigned events in `requested`, `changes_requested`, `planning` or `confirmed`) is selected; ties go to the coordinator least recently given an event.
- AC4: On assignment, the event's `coordinator_id` is set and its status transitions from `requested` to `planning`.
- AC5: The assigned coordinator automatically receives a notification confirming ownership of the event.
- AC6: The event organiser automatically receives a notification that a coordinator has been assigned to their event.
- AC7: An event that already has a coordinator is not reassigned by automatic assignment.
- AC8: An Event Coordinator can view the events assigned to them in the `Assigned Events` section of the coordinator workspace.
- AC9: An Event Organiser can see on their event whether an Event Coordinator has been assigned, including the coordinator’s name.

## Relevant Customer Clarifications

- Each event must be automatically assigned to one Event Coordinator only.
- The team may decide the auto-assignment logic (e.g. round-robin, workload, availability, event type) as long as it is fair, technically feasible and aligned with requirements.
- Reassignment requires offline agreement between coordinators; the original coordinator initiates it and the new coordinator must accept. The reassignment workflow and UI are out of scope for this story.
- `Submitted` maps to the existing status `requested`; `In Review` maps to `planning`.
- Notifications are created automatically by the system, not by a user.

## Preconditions / Dependencies

- The event request creation/submission story produces events with status `requested` and no coordinator.
- At least one user has the `event_coordinator` role and an active profile.
- Notification display belongs to the notification story; until it exists, notifications can be verified in the `notification` table.

## Test Case Reference

`docs/test-cases/event-assignment.md`

## Relevant UML Reference

- Not required.

## Implementation Notes

- Implemented as a `SECURITY DEFINER` trigger function on `event` (`docs/database/event-assignment.sql`). Organisers can read the assigned coordinator’s profile through the “Organisers can view assigned coordinator profiles” RLS policy.
- Concurrent submissions are serialised with a transaction-level advisory lock to keep workload counts accurate.
- If no active coordinator exists, the event remains `requested` and unassigned and no notifications are sent (see Open Questions in the test-case file).
- Because assignment moves the event straight to `planning`, the organiser's direct-edit window (`draft` / `requested` / `changes_requested` under RLS) ends at submission; later amendments go through the event change request flow.