# Review Venue Booking Requests

## User Story
As Venue Staff, I want to review incoming venue booking requests with full event details and conflict checks, so that I can decide whether to approve or reject the request and notify the coordinator.

# Acceptance Criteria
Ensure that Venue Staff can:
- View the requested venue, date, time, setup notes, requested capacity (versus listed venue capacity), layout, and accessibility details.
- View any overlapping tentative holds or confirmed bookings flagged by the system for the requested time slot.
- View competing pending requests ordered chronologically by submission timestamp (first-come, first-served basis).
- Approve or reject a request, updating its status to Approved or Rejected immediately.
- Concurrently evaluate requests: approving one request automatically prompts a warning to resolve or reject remaining overlapping pending requests.
- Trigger an automated system notification to the submitting Event Coordinator, displaying the updated status (Approved or Rejected) on their request dashboard.