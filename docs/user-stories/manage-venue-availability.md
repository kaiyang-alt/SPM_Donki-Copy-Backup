# User Story — Manage Venue Availability

## User Story

As Venue Staff, I want to manage a venue's availability calendar, so that Event Coordinators only see accurate, selectable time slots when searching for or requesting venues.

## Acceptance Criteria

1. Venue Staff can mark specific dates or time slots on a venue as unavailable (e.g. for maintenance or external commitments).
2. Venue Staff can view a single unified calendar displaying confirmed bookings, tentative holds, and staff-marked unavailability blocks.
3. The system returns an error prompt and prevents marking a time slot as unavailable if it directly overlaps with an existing Confirmed booking.
4. Marked unavailable time slots are instantly hidden from Event Coordinator venue search results and cannot be selected during new request submissions.
5. Marking a venue unavailable does not automatically cancel, overwrite, or alter existing confirmed bookings on that venue.

## Preconditions / Dependencies

- A registered Supabase Auth account exists with the `venue_staff` role in `user_role`.
- Venues and existing `venue_booking` rows exist for the venue under test.
- RLS policies permit Venue Staff to insert into `venue_block` for their venue.
- Event Coordinator venue search reads through the same RLS context.

## Test Case Reference

`docs/test-cases/manage-venue-availability.md`
