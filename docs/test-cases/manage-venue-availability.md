# Test Cases — Manage Venue Availability

## Traceability Summary

| Test Case | Category | Acceptance Criterion |
|---|---|---|
| TC-001 | Happy Path | AC-1: Mark a date or slot unavailable |
| TC-002 | Happy Path | AC-2: Unified calendar shows bookings + holds + blocks |
| TC-003 | Negative | AC-3: Overlap with a Confirmed booking is rejected |
| TC-004 | Happy Path | AC-3: Non-overlapping block against a Confirmed booking succeeds |
| TC-005 | Cross-Cutting Quality | AC-4: Blocked slot hidden from Event Coordinator search |
| TC-006 | Cross-Cutting Quality | AC-4: Blocked slot rejected during request submission |
| TC-007 | Cross-Cutting Quality | AC-5: Existing Confirmed bookings remain unchanged after blocking |
| TC-008 | Negative | Access denied for non–Venue Staff |
| TC-009 | Negative | Invalid slot (end before start, missing fields) is rejected |

---

### TC-001 — Mark a Venue Slot Unavailable

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that Venue Staff can mark a specific date/time slot on a venue as unavailable. |
| **Pre-conditions** | - `venue.staff@example.test` is authenticated with the `venue_staff` role.<br>- Venue `VENUE-1` exists and is managed by this staff member.<br>- No confirmed booking overlaps the target slot. |
| **Test Steps** | 1. Open the venue availability view for `VENUE-1`.<br>2. Select the date `2026-12-01` and time `09:00–12:00`.<br>3. Submit the unavailability block with reason `Scheduled maintenance`.<br>4. Reload the calendar. |
| **Test Data** | `Venue`: `VENUE-1`<br>`Date`: `2026-12-01`<br>`Start`: `09:00`<br>`End`: `12:00`<br>`Reason`: `Scheduled maintenance` |
| **Expected Result** | - The block is created successfully.<br>- The slot displays as unavailable on the calendar.<br>- The block persists after reload. |

---

### TC-002 — Unified Availability Calendar

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that the availability calendar displays confirmed bookings, tentative holds, and staff blocks together. |
| **Pre-conditions** | - `venue.staff@example.test` is authenticated.<br>- `VENUE-1` has at least one `confirmed` booking, one `tentative` booking, and one `venue_block` on the same date. |
| **Test Steps** | 1. Open the venue availability view for `VENUE-1`.<br>2. Inspect the calendar entries for the target date.<br>3. Compare against the raw rows in `venue_booking` and `venue_block`. |
| **Test Data** | `Confirmed`: `2026-12-05` `10:00–13:00`<br>`Tentative`: `2026-12-05` `14:00–16:00`<br>`Block`: `2026-12-05` `17:00–18:00` |
| **Expected Result** | - All three entries appear on the same calendar.<br>- Each entry is visually distinguishable (e.g. by status label).<br>- No entry is duplicated or missing. |

---

### TC-003 — Reject Block Overlapping a Confirmed Booking

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Negative |
| **Test Scenario** | Verify that a block whose time window directly overlaps a Confirmed booking is rejected with an error prompt. |
| **Pre-conditions** | - `venue.staff@example.test` is authenticated.<br>- `VENUE-1` has a `confirmed` booking on `2026-12-10` from `10:00` to `14:00`. |
| **Test Steps** | 1. Attempt to block `2026-12-10` `12:00–15:00` on `VENUE-1`.<br>2. Inspect the response.<br>3. Reload the calendar and confirm no new block was created. |
| **Test Data** | `Confirmed booking`: `2026-12-10` `10:00–14:00`<br>`Attempted block`: `2026-12-10` `12:00–15:00` |
| **Expected Result** | - The request is rejected with a clear error.<br>- No `venue_block` row is created.<br>- The existing confirmed booking remains unchanged. |

---

### TC-004 — Allow Non-Overlapping Block Against a Confirmed Booking

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that a block immediately before or after a confirmed booking, with no overlap, is accepted. |
| **Pre-conditions** | - `venue.staff@example.test` is authenticated.<br>- `VENUE-1` has a `confirmed` booking on `2026-12-10` from `10:00` to `14:00`. |
| **Test Steps** | 1. Block `2026-12-10` `14:00–16:00` on `VENUE-1`.<br>2. Reload the calendar. |
| **Test Data** | `Confirmed booking`: `2026-12-10` `10:00–14:00`<br>`Attempted block`: `2026-12-10` `14:00–16:00` |
| **Expected Result** | - The block is created.<br>- Both entries appear on the calendar without overlap. |

---

### TC-005 — Blocked Slot Hidden from Event Coordinator Search

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-005 |
| **Category** | Cross-Cutting Quality |
| **Test Scenario** | Verify that a blocked time slot is not returned when an Event Coordinator searches for venues. |
| **Pre-conditions** | - `organiser.alpha@example.test` is authenticated with the `event_organiser` role.<br>- `VENUE-1` has a block on `2026-12-15` `09:00–12:00`. |
| **Test Steps** | 1. Search for venues available on `2026-12-15` `09:00–12:00`.<br>2. Inspect the availability slots shown for `VENUE-1`.<br>3. Compare against the block in `venue_block`. |
| **Test Data** | `Search date`: `2026-12-15`<br>`Search window`: `09:00–12:00` |
| **Expected Result** | - `VENUE-1` does not expose `09:00–12:00` as a selectable slot.<br>- The slot is either excluded from results or explicitly marked unavailable.<br>- No stale cached slot appears after the block is created. |

---

### TC-006 — Blocked Slot Rejected at Request Submission

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-006 |
| **Category** | Cross-Cutting Quality |
| **Test Scenario** | Verify that an Event Coordinator cannot submit a new venue request for a blocked slot, even if it bypasses search. |
| **Pre-conditions** | - `organiser.alpha@example.test` is authenticated.<br>- `VENUE-1` has a block on `2026-12-20` `13:00–17:00`. |
| **Test Steps** | 1. Attempt to submit a venue request for `VENUE-1` on `2026-12-20` `13:00–17:00` via the normal UI.<br>2. Attempt the same submission directly via the API (bypassing UI validation).<br>3. Inspect both responses. |
| **Test Data** | `Venue`: `VENUE-1`<br>`Date`: `2026-12-20`<br>`Window`: `13:00–17:00` |
| **Expected Result** | - The UI prevents selecting the blocked slot.<br>- The API rejects the submission with an error.<br>- No `venue_booking` row is created. |

---

### TC-007 — Blocking Does Not Alter Existing Confirmed Bookings

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-007 |
| **Category** | Cross-Cutting Quality |
| **Test Scenario** | Verify that creating a block never cancels, overwrites, or mutates existing confirmed bookings on the same venue. |
| **Pre-conditions** | - `VENUE-1` has a confirmed booking on `2026-12-25` `10:00–14:00`.<br>- Note the booking's `id`, `status`, `start_time`, `end_time` before the test. |
| **Test Steps** | 1. Create a block on `2026-12-25` `15:00–17:00` (non-overlapping).<br>2. Query the confirmed booking before and after.<br>3. Repeat with an attempt to block `2026-12-25` `10:00–14:00` (overlapping) — verify it is rejected and the booking still unchanged. |
| **Test Data** | `Confirmed booking ID`: `REQ-100`<br>`Original status`: `confirmed`<br>`Original window`: `10:00–14:00` |
| **Expected Result** | - The confirmed booking's `status`, `start_time`, and `end_time` are identical before and after.<br>- The overlapping block attempt is rejected without side effects.<br>- No cascade or trigger alters the booking. |

---

### TC-008 — Deny Access to Non–Venue Staff

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-008 |
| **Category** | Negative |
| **Test Scenario** | Verify that users without the `venue_staff` role cannot create, view, or manage availability blocks. |
| **Pre-conditions** | - `organiser.alpha@example.test` is authenticated with the `event_organiser` role only. |
| **Test Steps** | 1. Attempt to create a block on `VENUE-1`.<br>2. Attempt to fetch the venue's availability calendar. |
| **Test Data** | `Authenticated User`: `organiser.alpha@example.test`<br>`Target Venue`: `VENUE-1` |
| **Expected Result** | - Both operations are denied.<br>- No `venue_block` row is created.<br>- No availability data is disclosed. |

---

### TC-009 — Reject Invalid Block Inputs

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-009 |
| **Category** | Negative |
| **Test Scenario** | Verify that malformed block requests are rejected without creating a row. |
| **Pre-conditions** | - `venue.staff@example.test` is authenticated with the `venue_staff` role. |
| **Test Steps** | 1. Submit a block with `end_time` before `start_time`.<br>2. Submit a block with a missing `date`.<br>3. Submit a block with a missing `venue_id`.<br>4. Inspect each response and the table. |
| **Test Data** | `Case A`: `start=15:00`, `end=14:00`<br>`Case B`: no date field<br>`Case C`: no venue_id |
| **Expected Result** | - Each case returns a validation error.<br>- No partial row is inserted.<br>- The response body names the offending field. |