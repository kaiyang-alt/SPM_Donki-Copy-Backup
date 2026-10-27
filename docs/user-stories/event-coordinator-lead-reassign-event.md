# Reassign an Event

## User Story

As an Event Coordinator Lead, I want to reassign an event to another Event Coordinator so that ownership can be changed when necessary.

## Acceptance Criteria

- AC1: The Event Coordinator Lead can view the Event Coordinator currently assigned to an event.
- AC2: The Event Coordinator Lead can select another active Event Coordinator for reassignment.
- AC3: A successful reassignment replaces the existing assignment with the selected Event Coordinator.
- AC4: The event has no more than one assigned Event Coordinator after reassignment.
- AC5: The newly assigned Coordinator can manage the event after reassignment.
- AC6: The previous Coordinator can no longer manage the event through the previous assignment.
- AC7: The newly assigned Coordinator is displayed as the current owner after reassignment is saved.
- AC8: Successful reassignment notifies the outgoing Coordinator, incoming Coordinator, and Event Organiser.
- AC9: Unauthorised users cannot reassign the event.

## Relevant Customer Clarifications

- The Event Coordinator Lead is a new application role.
- Lead-controlled reassignment immediately replaces the current assignment and does not require approval from either coordinator.
- The outgoing Event Coordinator, incoming Event Coordinator, and Event Organiser are notified after reassignment.
- Only a user with an active profile and the `event_coordinator` role can be selected as the replacement.

## Preconditions / Dependencies

- The Event Coordinator Lead is authenticated and authorised to perform reassignment.
- The event currently has an assigned Event Coordinator.
- Another Event Coordinator is available for selection.
- The shared role model and authentication support for the Event Coordinator Lead must be available.
- RLS must permit the Lead to view assigned events and Event Coordinator identities, replace an existing assignment, and create the approved notifications.

## Test Case Reference

Planned functional test specification:

`docs/test-cases/event-coordinator-lead-reassign-event.md`

## Relevant UML Reference

No story-specific UML is currently documented.

## Implementation Notes

- Reuse `event.coordinator_id` for current ownership unless the team approves a schema change.
- Lead-controlled reassignment is a direct administrative replacement and supersedes the previous Coordinator-to-Coordinator acceptance model for this workflow.
- The approved transactional reassignment function validates the Lead, expected current owner, and active replacement, then saves ownership and all three notifications atomically.
- The approved assignment guard prevents non-Lead callers from changing `event.coordinator_id`.
- Follow the shared `route -> service/business logic -> Supabase` flow.
