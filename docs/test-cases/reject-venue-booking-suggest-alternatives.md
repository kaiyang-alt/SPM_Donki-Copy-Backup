# Test Cases — Reject Venue Booking Request and Suggest Alternative Venues

**Review state:** APPROVED — Human Gate 2 confirmed on 2026-10-20; implementation-readiness and any required Human Gate 3 approval remain pending.

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | AC1, AC2, AC3, AC5 — Reject a pending booking with explanatory notes and two suggested alternatives; Coordinator sees saved details |
| TC-002 | Happy Path | AC1, AC2, AC3 — Reject a pending booking without optional notes or alternatives |
| TC-003 | Negative | AC1, AC4 — Rejection is unavailable for requests already in a non-pending status |
| TC-004 | Negative | AC4 — A rejected request cannot be approved, rejected again, or overwritten through another booking-status path |
| TC-005 | Happy Path | AC3, AC5 — Coordinator can revisit the rejection and suggested alternatives without restarting the event request or automatically booking an alternative |

### TC-001 — Reject a Pending Booking with Notes and Multiple Alternatives

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that Venue Staff can reject an unsuitable requested booking, record a reason, suggest two other venues, and make the decision details visible to the assigned Coordinator. |
| **Pre-conditions** | - Venue Staff is authenticated and authorised to decide booking `BKG-101`.<br>- `BKG-101` is linked to event `EVT-101`, venue `VEN-001`, and has persisted status `requested`.<br>- `EVT-101` has an assigned Event Coordinator.<br>- Alternative venue references `VEN-002` and `VEN-003` are present in the venue catalogue. |
| **Test Steps** | 1. As Venue Staff, open booking `BKG-101`.<br>2. Select Reject.<br>3. Enter a rejection note explaining why the requested venue is unsuitable.<br>4. Suggest venues `VEN-002` and `VEN-003`.<br>5. Confirm the rejection.<br>6. As the assigned Coordinator, open the booking in the event workspace. |
| **Test Data** | `Booking ID`: `BKG-101`<br>`Current status`: `requested`<br>`Rejection reason`: `Room is undergoing maintenance on the requested date.`<br>`Suggested alternatives`: `VEN-002`, `VEN-003` |
| **Expected Result** | - `BKG-101` is persisted with status `rejected` and displayed as `Rejected`.<br>- The Coordinator sees the rejection note and both suggested venue references attached to `BKG-101`.<br>- The original rejected booking remains identifiable; neither alternative is automatically booked or confirmed. |

### TC-002 — Reject Without Optional Notes or Alternatives

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that rejection does not require explanatory notes or suggested alternative venues. |
| **Pre-conditions** | - Venue Staff is authenticated and authorised to decide booking `BKG-102`.<br>- `BKG-102` is persisted with status `tentative`. |
| **Test Steps** | 1. Open booking `BKG-102`.<br>2. Select Reject.<br>3. Leave the optional reason and alternative-venue fields blank.<br>4. Confirm the rejection.<br>5. Reopen the rejected booking. |
| **Test Data** | `Booking ID`: `BKG-102`<br>`Current status`: `tentative`<br>`Rejection reason`: empty<br>`Suggested alternatives`: none |
| **Expected Result** | - The rejection succeeds and the persisted status is `rejected`.<br>- No rejection note or alternative venue is required to complete the operation.<br>- Reopening the booking shows its rejected status without inventing suggested venues. |

### TC-003 — Prevent Rejection of a Non-Pending Booking

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Negative |
| **Test Scenario** | Verify that only requests in `requested` or `tentative` status can be rejected. |
| **Pre-conditions** | - Venue Staff is authenticated.<br>- Separate bookings `BKG-103`, `BKG-104` and `BKG-105` are persisted with statuses `confirmed`, `rejected`, and `cancelled` respectively. |
| **Test Steps** | 1. Open each booking in turn.<br>2. Attempt to submit Reject for each booking.<br>3. Reopen the bookings and inspect their saved decisions and statuses. |
| **Test Data** | `BKG-103`: `confirmed`<br>`BKG-104`: `rejected`<br>`BKG-105`: `cancelled` |
| **Expected Result** | - No rejection is recorded for any of the three bookings.<br>- All three bookings retain their original persisted statuses and decision details. |

### TC-004 — Preserve Permanent Rejection Across Status-Change Paths

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Negative |
| **Test Scenario** | Verify that a rejected booking cannot be approved or have its decision overwritten using any supported Venue Staff booking-status action. |
| **Pre-conditions** | - Booking `BKG-106` is already persisted as `rejected`.<br>- Its existing rejection note is `Insufficient space for the proposed layout.` and its suggested venue is `VEN-004`.<br>- Venue Staff is authenticated and authorised to access this booking. |
| **Test Steps** | 1. Reopen `BKG-106`.<br>2. Attempt to approve the rejected booking.<br>3. Attempt to reject the booking a second time with a different reason.<br>4. Where a separate Venue Staff status-update interface exists, attempt to change `BKG-106` to an active booking status through it.<br>5. Reopen `BKG-106` and review its saved values. |
| **Test Data** | `Booking ID`: `BKG-106`<br>`Persisted status`: `rejected`<br>`Original reason`: `Insufficient space for the proposed layout.`<br>`Original alternative`: `VEN-004` |
| **Expected Result** | - Every attempt to re-decide or reactivate `BKG-106` is denied.<br>- `BKG-106` remains persisted as `rejected`.<br>- The original reason, suggested alternative, decision maker and decision time remain unchanged. |

### TC-005 — Coordinator Can Review Rejection Without Restarting Event Planning

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-005 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that the Coordinator can retrieve the saved rejection details after refreshing and continue using the existing event-planning context. |
| **Pre-conditions** | - Event `EVT-107` is assigned to the signed-in Event Coordinator.<br>- Linked booking `BKG-107` is persisted as `rejected` with reason `Venue is unsuitable for the requested setup.` and alternative `VEN-005`.<br>- The event remains available in the Coordinator's planning workspace. |
| **Test Steps** | 1. Open the Coordinator's existing event workspace for `EVT-107`.<br>2. Locate its rejected venue request `BKG-107`.<br>3. Review its note and suggested venue.<br>4. Refresh the page or reopen the event workspace.<br>5. Locate the same booking again and continue to the existing venue-booking workflow. |
| **Test Data** | `Event ID`: `EVT-107`<br>`Booking ID`: `BKG-107`<br>`Persisted status`: `rejected`<br>`Suggested venue`: `VEN-005` |
| **Expected Result** | - The Coordinator sees `Rejected`, the persisted reason and the suggested alternative before and after the page is refreshed.<br>- The original event request and rejected booking remain accessible and identifiable.<br>- The Coordinator can continue in the existing event-planning context without creating another event request.<br>- No replacement booking is automatically created as a result of viewing a suggested venue. |

## Implementation Dependencies

- The current Coordinator booking list does not display the persisted `decision_reason` field. Rendering the reason and its currently encoded suggested venue IDs is required to meet AC5.
- The canonical booking service guards rejected bookings against being decided again, but a separate legacy Venue Staff status-write path uses incompatible status/column assumptions and lacks the same final-state invariant. Reconcile this path through the approved shared-change process before claiming TC-004 passes.
- The existing service stores alternative venue IDs in `venue_booking.decision_reason`; the current schema has no dedicated alternative-venue relationship. Do not introduce one from this test specification.
- A suggestion must not be presented as a confirmed available slot. Whether to validate referenced venue existence/availability during rejection is an open implementation-contract question.
- These are functional specifications, not executed test results. Live Supabase/RLS and browser behavior remain to be verified during implementation.

## Human Gate 2

**Human Gate 2 approved on 2026-10-20.** Do not implement routes, services, frontend changes, pytest tests, schema/RLS changes or merge this feature until the remaining workflow gates are cleared.
