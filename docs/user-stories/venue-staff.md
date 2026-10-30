# Review Venue Booking Requests

## User Story
As Venue Staff, I want to review incoming venue booking requests with full event details and conflict checks, so that I can decide whether to approve or reject the request and notify the coordinator.

# Acceptance Criteria
Ensure that Venue Staff can:
- View the requested venue, date, time, setup notes, requested capacity (versus listed venue capacity), layout, and accessibility details.
- View any overlapping tentative holds or confirmed bookings flagged by the system for the requested time slot.
- View competing pending requests (persisted as `requested` or `tentative`) ordered chronologically by submission timestamp (first-come, first-served basis).
- Approve or reject a request. Approval persists `venue_booking.status = confirmed`; rejection persists `venue_booking.status = rejected`.
- Concurrently evaluate requests: approving one request automatically prompts a warning to resolve or reject remaining overlapping pending requests.
- Trigger an automated system notification to the submitting Event Coordinator, displaying the updated result (`Approved` or `Rejected`) on their request dashboard. These are display labels; `Approved` is not a persisted database status.

## Persisted Status Values

The live `venue_booking.status` CHECK constraint permits only `requested`,
`tentative`, `confirmed`, `rejected`, and `cancelled`. In this workflow,
"pending" describes requests persisted as `requested` or `tentative`, while
"Approved" is display text for a booking persisted as `confirmed`.

## Test Case Reference

`docs/test-cases/venue_staff.md`
