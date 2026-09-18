# Test Cases — Secure Access to Event Organiser Account

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | Registered credentials, valid login, and access to Event Organiser functionality |
| TC-002 | Negative | Access is denied when invalid credentials are provided |
| TC-003 | Happy Path | View and modify authorised event information while the event is in `draft`, `requested`, or `changes_requested` status |
| TC-004 | Cross-Cutting Quality | Prevent viewing or modifying event information owned by another Event Organiser |
| TC-005 | Happy Path | Log out and end the authenticated session |

### TC-001 — Log In with Valid Event Organiser Credentials

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an Event Organiser can log in with registered credentials and access Event Organiser functionality. |
| **Pre-conditions** | - A registered Supabase Auth account exists for `organiser.alpha@example.test`.<br>- The account has an associated `profile` record.<br>- The account has the `event_organiser` role in `user_role`.<br>- The user is not currently authenticated. |
| **Test Steps** | 1. Open the ConnectSphere login page.<br>2. Enter the registered Event Organiser email address and password.<br>3. Submit the login form.<br>4. Attempt to access Event Organiser functionality. |
| **Test Data** | `Email`: `organiser.alpha@example.test`<br>`Password`: Registered test-account password stored outside the repository |
| **Expected Result** | - Authentication succeeds.<br>- The Event Organiser is granted access to the system.<br>- Event Organiser functionality is accessible. |

### TC-002 — Reject Invalid Login Credentials

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Negative |
| **Test Scenario** | Verify that access is denied when an Event Organiser provides invalid credentials. |
| **Pre-conditions** | - A registered Supabase Auth account exists for `organiser.alpha@example.test`.<br>- The user is not currently authenticated. |
| **Test Steps** | 1. Open the ConnectSphere login page.<br>2. Enter the registered email address with an incorrect password.<br>3. Submit the login form.<br>4. Attempt to access Event Organiser functionality. |
| **Test Data** | `Email`: `organiser.alpha@example.test`<br>`Password`: `DefinitelyWrong!2026` |
| **Expected Result** | - Authentication fails.<br>- Access to the system is denied.<br>- Event Organiser functionality remains inaccessible. |

### TC-003 — View and Modify Authorised Event Information

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an authenticated Event Organiser can view and modify permitted information for an event they own while it is in an organiser-editable status. |
| **Pre-conditions** | - `organiser.alpha@example.test` is authenticated.<br>- The account has the `event_organiser` role in `user_role`.<br>- Event `Alpha Leadership Forum 2026` exists and belongs to the organiser.<br>- The event has an organiser-editable status: `draft`, `requested`, or `changes_requested`. |
| **Test Steps** | 1. Open the Event Organiser functionality.<br>2. Open `Alpha Leadership Forum 2026`.<br>3. View the event information.<br>4. Change the event name to `Alpha Leadership Forum 2026 — Updated`.<br>5. Save the change.<br>6. Reopen the event. |
| **Test Data** | `Event`: `Alpha Leadership Forum 2026`<br>`Event Status`: `requested`<br>`Updated Event Name`: `Alpha Leadership Forum 2026 — Updated` |
| **Expected Result** | - The authorised event is displayed.<br>- The organiser can save the permitted name change.<br>- The updated event name remains visible when the event is reopened. |

### TC-004 — Block Access to Unauthorised Event Information

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Cross-Cutting Quality |
| **Test Scenario** | Verify that an authenticated Event Organiser cannot view or modify an event belonging to a different Event Organiser. |
| **Pre-conditions** | - `organiser.alpha@example.test` is authenticated.<br>- The account has the `event_organiser` role in `user_role`.<br>- Event `Restricted Planning Forum 2026` exists and belongs to a different Event Organiser.<br>- Existing RLS does not permit `organiser.alpha@example.test` to view or update the event. |
| **Test Steps** | 1. Open the Event Organiser event list.<br>2. Check whether `Restricted Planning Forum 2026` is displayed.<br>3. Attempt to access `Restricted Planning Forum 2026` directly.<br>4. Attempt to submit an event-name change to `Restricted Planning Forum 2026`. |
| **Test Data** | `Authenticated User`: `organiser.alpha@example.test`<br>`Unauthorised Event`: `Restricted Planning Forum 2026`<br>`Attempted Event Name`: `Unauthorised Update` |
| **Expected Result** | - The unauthorised event is not displayed in the organiser's event list.<br>- The event information is not disclosed through direct access.<br>- The attempted modification is rejected.<br>- The unauthorised event remains unchanged. |

### TC-005 — Log Out and End the Authenticated Session

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-005 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an Event Organiser can log out and end their authenticated session. |
| **Pre-conditions** | - `organiser.alpha@example.test` is authenticated.<br>- The account has the `event_organiser` role in `user_role`.<br>- Event Organiser functionality is accessible during the authenticated session. |
| **Test Steps** | 1. Select the logout option.<br>2. Attempt to access Event Organiser functionality after logout. |
| **Test Data** | `Authenticated User`: `organiser.alpha@example.test` |
| **Expected Result** | - The Event Organiser is logged out.<br>- The authenticated session ends.<br>- Event Organiser functionality and authorised event information are no longer accessible without logging in again. |
