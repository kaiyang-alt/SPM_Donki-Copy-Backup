# Submit a Venue Booking Request

## User Story

As an Event Coordinator, I want to submit a formal venue booking request for an approved event so that Venue Staff can review and reserve the required space.

## Acceptance Criteria

- **AC1:** An authenticated Event Coordinator can select an available venue, date, time slot, and setup layout for an event they are authorised to coordinate. For this story, the eligible event status is `planning`.
- **AC2:** Before saving, check for overlapping active bookings/holds and venue blackout periods. Reject conflicts without creating a booking or notification.
- **AC3:** Successful submission places a tentative hold on the selected venue slot. An event must not have more than one active venue/time arrangement.
- **AC4:** Persist the booking linked to its Event ID and Venue ID.
- **AC5:** Notify the Venue Staff assigned to the selected venue through the Notification service.
- **AC6:** Display “Pending Venue Approval” in the Coordinator event workspace and retain that status when the workspace is reloaded.

## Confirmed Project Rules

- The Coordinator submits the request; Venue Staff have final approval authority.
- Only one active tentative or confirmed arrangement may apply to an event.
- Existing venue-booking statuses are `requested`, `tentative`, `confirmed`, `rejected`, and `cancelled`. Do not introduce `approved` as an event or booking status.
- Both venue and equipment arrangements must be complete before confirming the event. Submitting or approving a venue booking must not automatically confirm the event.
- Existing authentication, Supabase configuration, schema, and RLS must be preserved.

Source: [Shared project context](../architecture/project_context.md).

## Implementation Interpretation Requiring Team Verification

The existing functional specification stores a newly submitted request as `requested` and treats it as a blocking hold. The application therefore treats `requested`, `tentative`, and `confirmed` as active when checking conflicts. Confirm that this matches the existing database workflow; do not silently change the database status model.

Intervals use a same-day, half-open convention: `[start, end)`. A booking ending at 12:00 does not conflict with one starting at 12:00. Overnight bookings are not represented by this date/start/end payload.

## Preconditions and Dependencies

- A valid Supabase session with the `event_coordinator` role. The current shared login UI supports Event Organisers; a Coordinator-only login flow remains an integration dependency.
- The event is visible under the caller's existing RLS policies and is in `planning` status. RLS must enforce which events the Coordinator may coordinate.
- The selected venue exists and the database provides the venue-to-staff assignment relationship.
- RLS must expose the conflicts required to make an availability decision; filtering out another user's reservation must not make its slot appear free.
- Database enforcement must prevent simultaneous submissions from creating overlapping holds or multiple active arrangements for one event. Application prechecks alone cannot guarantee this across workers.
- The notification insert must be permitted under the existing RLS design.

## Test Cases

[Functional test specification](../test-cases/submit-venue-booking.md)

Automated route/service tests: `tests/test_venue_booking.py`. The fixture uses the actual Flask application so missing blueprint registration is detected. Database calls are simulated; this is not a live schema/RLS or browser end-to-end test.

## Scope

This story covers submission, holds, notification, and the Coordinator's pending status. Approval/rejection, venue editing, maintenance blocks, and staff schedule management are separate workflows. Existing handlers are retained and guarded, but their presence is not evidence that those stories have been accepted.

## Outstanding Integration Verification

- The implementation uses the confirmed live columns: `booking_id`, `requested_start`, `requested_end`, `requested_by`, `venue_block_id`, `start_datetime`, and `end_datetime`. A live Supabase integration test is still required to verify the deployed schema and policies.
- AC5 remains blocked. The unchanged database has no venue-to-staff assignment relationship, and the current notification RLS policies do not permit a Coordinator to insert notifications. Successful booking responses explicitly report `notification_sent: false` with a warning.
- No atomic booking RPC/constraint is documented locally. Do not claim concurrency safety until the existing database protections are verified. Any required database changes need team agreement.
- The Coordinator and Venue Staff interfaces use real role-verified Supabase sessions. The Coordinator flow checks eligible venues, submits requests, and reloads persisted booking status.
- Setup layout is stored in the existing `event.layout_requirements` field because `venue_booking` has no layout column. The booking remains linked to that event through `event_id`.
- User-entered dates and times are interpreted as Singapore time (`UTC+08:00`) before being written to the `timestamptz` booking and block columns.
- A saved booking reports `notification_sent: false` and a warning. Do not retry the booking itself merely because notification delivery is unavailable.
