# Reject Venue Booking Request and Suggest Alternative Venues

## User Story

As Venue Staff, I want to reject an unsuitable booking request and suggest an alternative venue so that the Event Coordinator can adjust the request without restarting the planning process.

## Acceptance Criteria

### AC1 — Reject an Unsuitable Booking Request

- An authenticated Venue Staff member can reject a pending venue booking request when the venue is unsuitable or unavailable.
- Only requests with persisted status `requested` or `tentative` are eligible for rejection.
- A successful rejection updates `venue_booking.status` to `rejected`.

### AC2 — Add Explanatory Rejection Notes

- Venue Staff can optionally provide explanatory notes when rejecting a request.
- Any supplied notes are saved with the rejected booking and remain available when it is reopened.
- Rejection is permitted even when no notes are provided.

### AC3 — Suggest Alternative Venues

- Venue Staff can optionally propose one or more alternative venues when rejecting a booking.
- Suggestions are associated with the rejected booking request.
- The Coordinator can identify the suggested venues without creating a new event request.
- Suggested alternatives do not automatically become confirmed bookings.

### AC4 — Preserve Rejected Status

- Once a booking is rejected, its status cannot be changed to `requested`, `tentative` or `confirmed`.
- Approval attempts or repeated rejection attempts against a rejected booking must fail without overwriting the existing decision.
- A Coordinator may submit a separate booking request for another venue while retaining the original rejected record.

### AC5 — Display Rejection Details to the Event Coordinator

- The assigned Event Coordinator can view the rejected booking and its persisted `rejected` status (displayed as `Rejected`).
- Any rejection notes and proposed alternative venues are displayed alongside the affected booking.
- The details remain visible after refreshing or reopening the Coordinator's booking view.
- The Coordinator can use the existing event-planning workflow to request a different venue without restarting the event request.

## Relevant Customer Clarifications

- The provided acceptance criteria make rejection notes and alternative suggestions optional, not mandatory.
- `Rejected` is a user-facing label; the persisted `venue_booking.status` is `rejected`.
- Suggesting an alternative does not itself book, approve or guarantee that venue's availability.
- This story concerns rejecting an individual venue booking, not cancelling the whole event.

## Preconditions / Dependencies

- A venue booking exists in `venue_booking` and is visible under existing RLS.
- The actor is authenticated with the `venue_staff` role.
- The existing `venue_booking` schema supports `status`, `decision_reason`, `decided_by` and `decided_at`.
- An assigned Event Coordinator can view their event's booking records.
- All applicable write paths must preserve the final state of a rejected booking.
- Shared changes to another story's route/service require the existing approval and PR review process.

## Implementation Notes

- Reuse the existing `POST /api/venue-bookings/<booking_id>/reject` endpoint and `app/services/venue_booking_service.py` rather than introducing a competing decision workflow.
- The existing implementation serialises the optional reason and suggested venue IDs into `venue_booking.decision_reason`. Reuse that approved field unless a separate shared data-contract decision authorises a change.
- The existing Coordinator booking view displays rejection status but does not yet display `decision_reason` or alternative suggestions.
- `app/services/venue_service.py` and `app/routes/venue_staff_routes.py` expose a second, legacy status-write path whose assumptions differ from the canonical booking service. Flag reconciliation as a shared integration dependency; do not silently edit, remove or redirect it.
- Preserve the existing frontend styling and authenticated Flask → service → Supabase pattern.
- Do not implement automatic replacement bookings, change the event's status, redesign multi-venue booking, or create schema/RLS migrations within this story.

## Open Implementation Questions

- Should suggested alternative venue IDs be checked for existence at rejection time, or treated as recommendations whose availability is verified later by the Coordinator? Do not imply a guaranteed free slot without an actual check.
- Which owner will approve the minimal shared fix needed to ensure the legacy status-write path cannot overwrite a rejected booking?

## Test Case Reference

`docs/test-cases/reject-venue-booking-suggest-alternatives.md`

## Requirement Revision

2026-10-20: New separately assigned story approved at Human Gate 1. This focused capability overlaps the broader Venue Staff booking-review workflow in `venue-staff.md` but does not replace that story. Human Gate 2 functional tests approved on 2026-10-20; implementation-readiness audit and any required shared-change approval remain pending.
