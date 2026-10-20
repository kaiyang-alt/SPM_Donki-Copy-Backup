# Test Cases for Submit a Venue Booking Request

## Test Cases

These are acceptance targets, not a claim that all flows are implemented. The automated tests use the real Flask app with a simulated database shaped to the confirmed Supabase columns. Live RLS, assigned-staff delivery, and concurrent submission safety still require integration verification.

Story: [Submit a Venue Booking Request](../user-stories/submit-venue-booking.md).

### Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | AC1, AC2, AC3, AC4, AC6 — Submission and persisted workspace coverage; AC5 remains blocked by the unchanged schema/RLS |
| TC-002 | Negative | AC2 — Automated conflict check rejection for overlapping bookings or blackout dates |
| TC-003 | Negative | AC1 — Prevention of venue booking request for unapproved events |
| TC-004 | Negative | AC1 — Validation failure when required submission fields are missing |

---

### TC-001 — Successful Submission of Venue Booking Request with Tentative Hold and Notification

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an Event Coordinator can successfully select an available venue, date, time slot, and layout for an approved event, triggering an automated conflict check, creating a linked booking request record with a tentative hold, notifying Venue Staff, and displaying the `Pending Venue Approval` label. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- Event `EVT-101` exists in `planning` status.<br>- Venue `VEN-001` (Grand Hall) has no existing bookings or blackout blocks on `2026-11-15` for time slot `09:00 - 12:00`.<br>- Venue Staff user `STF-301` is assigned to Venue `VEN-001`. |
| **Test Steps** | 1. Navigate to the Coordinator Event Workspace for event `EVT-101`.<br>2. Select the option to submit a formal venue booking request.<br>3. Select Venue `VEN-001`, Date `2026-11-15`, Time Slot `09:00 - 12:00`, and Setup Layout `Theatre`.<br>4. Submit the booking request.<br>5. Review the booking status on the event workspace and check the assigned Venue Staff's notifications. |
| **Test Data** | `Event ID`: `EVT-101`<br>`Venue ID`: `VEN-001`<br>`Date`: `2026-11-15`<br>`Time Slot`: `09:00 - 12:00`<br>`Setup Layout`: `Theatre` |
| **Expected Result** | - The automated conflict check completes successfully with no detected conflicts.<br>- A `venue_booking` record is created with persisted status `requested` (placing a tentative hold) linked directly to `EVT-101` and `VEN-001`.<br>- A notification is created for Venue Staff `STF-301` via the Notification Service regarding the incoming request.<br>- The Coordinator event workspace displays `Pending Venue Approval`; this is display text, not a persisted status value. |

---

### TC-002 — Rejection of Submission Due to Schedule Conflict or Blackout Date

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Negative |
| **Test Scenario** | Verify that the system executes an automated conflict check and blocks booking request submission when the selected venue slot overlaps with an existing booking or blackout date. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- Event `EVT-102` exists in `planning` status.<br>- Venue `VEN-001` has a blackout record (`venue_block`) or confirmed booking on `2026-11-15` for `14:00 - 18:00`. |
| **Test Steps** | 1. Navigate to the Coordinator Event Workspace for event `EVT-102`.<br>2. Select the option to submit a formal venue booking request.<br>3. Select Venue `VEN-001`, Date `2026-11-15`, Time Slot `14:00 - 18:00`, and Setup Layout `Theatre`.<br>4. Attempt to submit the booking request. |
| **Test Data** | `Event ID`: `EVT-102`<br>`Venue ID`: `VEN-001`<br>`Date`: `2026-11-15`<br>`Time Slot`: `14:00 - 18:00`<br>`Setup Layout`: `Theatre` |
| **Expected Result** | - The automated conflict check flags the time slot collision.<br>- Submission is prevented, and no `venue_booking` record or tentative hold is created for `EVT-102`.<br>- An explicit conflict message is displayed informing the Coordinator that the selected slot is unavailable. |

---

### TC-003 — Prevention of Venue Booking Submission for Unapproved Event

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Negative |
| **Test Scenario** | Verify that the system restricts venue booking request submissions to approved events and prevents requests for unapproved or draft events. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- Event `EVT-103` exists in `draft` status (unapproved).<br>- Venue `VEN-002` is available on `2026-11-20`. |
| **Test Steps** | 1. Navigate to the Coordinator Workspace for event `EVT-103`.<br>2. Attempt to initiate or submit a venue booking request for event `EVT-103`. |
| **Test Data** | `Event ID`: `EVT-103`<br>`Event Status`: `draft`<br>`Venue ID`: `VEN-002` |
| **Expected Result** | - The option to submit a venue booking request is disabled or blocked for `EVT-103`.<br>- The system displays an error or warning indicating that venue bookings can only be requested for approved events in planning status. |

---

### TC-004 — Validation Failure When Required Submission Fields Are Missing

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Negative |
| **Test Scenario** | Verify that attempting to submit a venue booking request with missing required selection fields fails validation and prevents record creation. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- Event `EVT-104` exists in `planning` status. |
| **Test Steps** | 1. Navigate to the Coordinator Event Workspace for event `EVT-104`.<br>2. Select the option to submit a formal venue booking request.<br>3. Select Venue `VEN-001` and Date `2026-11-15`, but leave Time Slot and Setup Layout unselected.<br>4. Attempt to submit the booking request. |
| **Test Data** | `Event ID`: `EVT-104`<br>`Venue ID`: `VEN-001`<br>`Date`: `2026-11-15`<br>`Time Slot`: `[Unselected]`<br>`Setup Layout`: `[Unselected]` |
| **Expected Result** | - Submission is rejected by input validation.<br>- Validation error messages highlight the unselected required fields.<br>- No `venue_booking` record or tentative hold is created. |

## Additional Regression and Integration Cases

| ID | Scenario | Expected result | Verification |
|---|---|---|---|
| TC-005 | Missing/invalid session; caller lacks Coordinator role | 401/403; no booking or notification | Automated |
| TC-006 | Missing event or event hidden by RLS | 404; no writes | Simulated database; live RLS verification required |
| TC-007 | Same event already has a requested/tentative/confirmed arrangement at another venue | 409; no second arrangement | Automated precheck; database concurrency protection required |
| TC-008 | Partial overlap, enclosing interval, enclosed interval, identical interval | 409 for requested, tentative, and confirmed bookings | Automated |
| TC-009 | Adjacent intervals; rejected/cancelled old bookings | Submission permitted if otherwise valid | Automated |
| TC-010 | Non-object/malformed JSON, wrong field types, blank strings, invalid calendar date, invalid/reversed/equal times | 400; no writes | Automated |
| TC-011 | Database failure before booking insertion | Sanitised error; no notification | Automated |
| TC-012 | Notification fails after booking saved | Return saved booking and explicit notification warning; do not create another booking on retry | Automated API test |
| TC-013 | Different users simultaneously request the same slot or different venues for the same event | At most one active arrangement is committed | Required live integration test; not established by mocks |
| TC-014 | Two venues have different assigned staff | Notify only staff assigned to the selected venue | Blocked: no assignment relationship or notification INSERT policy exists |
| TC-015 | Coordinator submits through workspace then reloads | Saved request with persisted status `requested` displays `Pending Venue Approval` after reload | Implemented; browser execution still required |
| TC-016 | Actual Supabase schema and policies | All columns valid; JWT preserved; authorised conflicts visible; unauthorised writes denied | Required live integration test |

### TC-002 execution variants

Run the conflict case independently for a requested hold, tentative hold, confirmed booking, and blackout. Include each overlap shape in TC-008 and the adjacent boundaries in TC-009. A failed submission must leave both the booking and notification counts unchanged.

### TC-001 assertions

Assert the actual insert payload, persisted Event ID/Venue ID, `requested` status, and response display status. Separately verify recipient assignment against real venue relationships and verify the workspace through the browser. A predefined mock booking response alone is insufficient.

### Separate workflow regression checks

The automated file also guards the retained staff endpoints: require authentication and Venue Staff authorisation, use the supported `confirmed` status on approval, and prevent re-deciding rejected/cancelled/confirmed requests. These tests are not substitutes for TC-002, TC-003, or TC-004, and do not constitute full acceptance coverage for staff workflows.
