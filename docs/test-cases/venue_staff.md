# Test Cases — Venue Staff Booking Request Management

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | Venue Staff can view incoming booking requests for a venue |
| TC-002 | Happy Path | Competing pending requests are displayed in chronological submission order |
| TC-003 | Happy Path | Venue Staff can approve a pending booking request |
| TC-004 | Happy Path | Venue Staff can reject a pending booking request |
| TC-005 | Negative | Access is denied for users without the `venue_staff` role |
| TC-006 | Cross-Cutting Quality | Approving a request warns about overlapping pending requests at the same venue, date and time |
| TC-007 | Negative | Invalid status values are rejected without changing the request |

---

### TC-001 — View Incoming Booking Requests

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an authenticated Venue Staff member can view incoming booking requests for their venue. |
| **Pre-conditions** | - A registered Supabase Auth account exists for `venue.staff@example.test`.<br>- The account has an associated `profile` record.<br>- The account has the `venue_staff` role in `user_role`.<br>- At least one booking request exists against the staff member's venue. |
| **Test Steps** | 1. Log in as `venue.staff@example.test`.<br>2. Open the Venue Staff booking requests view.<br>3. View the list of incoming booking requests. |
| **Test Data** | `Email`: `venue.staff@example.test`<br>`Password`: Registered test-account password stored outside the repository<br>`Venue ID`: The venue assigned to the Venue Staff member |
| **Expected Result** | - The booking requests view loads successfully.<br>- Requests belonging to the Venue Staff member's venue are displayed.<br>- Each request shows its submitted details and current status. |

---

### TC-002 — View Competing Requests in Chronological Order

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that multiple pending booking requests for the same venue are presented in the order they were submitted. |
| **Pre-conditions** | - `venue.staff@example.test` is authenticated with the `venue_staff` role.<br>- Two or more pending booking requests exist for the same venue.<br>- The requests have different `submitted_at` timestamps. |
| **Test Steps** | 1. Open the Venue Staff booking requests view.<br>2. Inspect the ordering of the displayed pending requests.<br>3. Compare the displayed order against each request's submission timestamp. |
| **Test Data** | `Request A`: submitted at `2026-10-07T08:00:00Z`, status `pending`<br>`Request B`: submitted at `2026-10-07T09:30:00Z`, status `pending` |
| **Expected Result** | - The earliest submitted request appears first.<br>- Later submissions appear in ascending `submitted_at` order.<br>- Ordering is consistent across repeated loads of the view. |

---

### TC-003 — Approve a Pending Booking Request

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that a Venue Staff member can approve a pending booking request with no conflicting pending requests. |
| **Pre-conditions** | - `venue.staff@example.test` is authenticated with the `venue_staff` role.<br>- A booking request exists for the venue with status `pending`.<br>- No other pending request exists for the same venue, date and overlapping time window. |
| **Test Steps** | 1. Open the booking request.<br>2. Select the approve action.<br>3. Confirm the approval.<br>4. Reopen the request and inspect its status. |
| **Test Data** | `Request ID`: `REQ-1`<br>`Current Status`: `pending`<br>`Requested Status`: `approved` |
| **Expected Result** | - The request status is updated to `approved`.<br>- The updated status persists when the request is reopened.<br>- No overlap warning is returned. |

---

### TC-004 — Reject a Pending Booking Request

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that a Venue Staff member can reject a pending booking request. |
| **Pre-conditions** | - `venue.staff@example.test` is authenticated with the `venue_staff` role.<br>- A booking request exists for the venue with status `pending`. |
| **Test Steps** | 1. Open the booking request.<br>2. Select the reject action.<br>3. Confirm the rejection.<br>4. Reopen the request and inspect its status. |
| **Test Data** | `Request ID`: `REQ-2`<br>`Current Status`: `pending`<br>`Requested Status`: `rejected` |
| **Expected Result** | - The request status is updated to `rejected`.<br>- The updated status persists when the request is reopened.<br>- No overlap warning is returned. |

---

### TC-005 — Deny Access to Non-Venue-Staff Users

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-005 |
| **Category** | Negative |
| **Test Scenario** | Verify that an authenticated user without the `venue_staff` role cannot view or update booking requests. |
| **Pre-conditions** | - A registered Supabase Auth account exists for `organiser.alpha@example.test`.<br>- The account has the `event_organiser` role in `user_role` and does not have the `venue_staff` role.<br>- At least one booking request exists for the venue. |
| **Test Steps** | 1. Log in as `organiser.alpha@example.test`.<br>2. Attempt to open the Venue Staff booking requests view.<br>3. Attempt to submit an approval or rejection against an existing request. |
| **Test Data** | `Authenticated User`: `organiser.alpha@example.test`<br>`Target Request ID`: `REQ-1`<br>`Attempted Status`: `approved` |
| **Expected Result** | - Access to the booking requests view is denied.<br>- No booking request details are disclosed.<br>- The approval or rejection attempt is rejected.<br>- The target request remains unchanged. |

---

### TC-006 — Warn About Overlapping Pending Requests on Approval

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-006 |
| **Category** | Cross-Cutting Quality |
| **Test Scenario** | Verify that approving a request surfaces a warning when another pending request for the same venue overlaps the approved time window. |
| **Pre-conditions** | - `venue.staff@example.test` is authenticated with the `venue_staff` role.<br>- Two pending booking requests exist for the same venue and requested date.<br>- Their start and end times overlap.<br>- The request being approved is `pending`. |
| **Test Steps** | 1. Open `REQ-1`.<br>2. Approve `REQ-1`.<br>3. Inspect the response for an overlap warning.<br>4. Reopen `REQ-2` and confirm its status is unchanged. |
| **Test Data** | `REQ-1`: `2026-11-20`, `09:00`–`12:00`, status `pending`<br>`REQ-2`: `2026-11-20`, `11:00`–`14:00`, status `pending`<br>`Requested Status on REQ-1`: `approved` |
| **Expected Result** | - `REQ-1` is updated to `approved`.<br>- The response includes an overlap warning identifying `REQ-2` as the conflicting pending request.<br>- `REQ-2` remains in `pending` status. |

---

### TC-007 — Reject Invalid Status Values

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-007 |
| **Category** | Negative |
| **Test Scenario** | Verify that a status update with an unrecognised value is rejected without modifying the request. |
| **Pre-conditions** | - `venue.staff@example.test` is authenticated with the `venue_staff` role.<br>- A booking request exists for the venue with status `pending`. |
| **Test Steps** | 1. Open `REQ-1`.<br>2. Attempt to update its status to a value other than `approved` or `rejected`.<br>3. Inspect the response.<br>4. Reopen the request and confirm its status is unchanged. |
| **Test Data** | `Request ID`: `REQ-1`<br>`Current Status`: `pending`<br>`Attempted Status`: `maybe` |
| **Expected Result** | - The update is rejected with a validation error.<br>- The request status remains `pending`.<br>- No partial update is applied. |