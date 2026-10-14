# Test Cases — View Event Status and Arrangements

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | View recorded status and event details for an authorised event |
| TC-002 | Happy Path | View venue booking and technical support arrangement statuses (Pending, Confirmed, Rejected, Unavailable) and outstanding requirements |
| TC-003 | Happy Path | View event details reflecting approved changes or rescheduling |
| TC-004 | Cross-Cutting Quality | Deny access to event details when an Event Organiser attempts to view an unauthorised event |

### TC-001 — View Recorded Event Status and Details

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an authenticated Event Organiser can view the recorded status and full event details for an event they are authorised to manage. |
| **Pre-conditions** | - `organiser.alpha@example.test` is authenticated.<br>- The account has the `event_organiser` role in `user_role`.<br>- Event `Alpha Leadership Forum 2026` exists and belongs to the organiser.<br>- The event record includes recorded date/time, expected attendance, venue, room layout, and programme details. |
| **Test Steps** | 1. Open the ConnectSphere dashboard.<br>2. Select `Alpha Leadership Forum 2026` from the event list.<br>3. View the event detail page. |
| **Test Data** | `Authenticated User`: `organiser.alpha@example.test`<br>`Event ID`: `EVT-2026-001`<br>`Event Title`: `Alpha Leadership Forum 2026` |
| **Expected Result** | - The event's recorded status (e.g., `Confirmed`) is clearly displayed.<br>- All recorded event details are displayed correctly:<br>  - Date and time<br>  - Expected attendance<br>  - Venue<br>  - Room layout<br>  - Programme or session information |

### TC-002 — View Venue and Technical Support Arrangement Statuses and Outstanding Requirements

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an Event Organiser can view the arrangement statuses (Pending, Confirmed, Rejected, Unavailable) for venue booking and technical support, including any outstanding arrangements before confirmation. |
| **Pre-conditions** | - `organiser.alpha@example.test` is authenticated.<br>- The account has the `event_organiser` role in `user_role`.<br>- Event `Alpha Leadership Forum 2026` exists with mixed arrangement statuses:<br>  - Venue booking: `Confirmed`<br>  - Technical support arrangement: `Pending`<br>- Outstanding requirements are linked to the event record. |
| **Test Steps** | 1. Access the event detail page for `Alpha Leadership Forum 2026`.<br>2. Locate the "Arrangements & Logistics" section.<br>3. Review the status indicators for venue booking and technical support.<br>4. Review the list of outstanding requirements. |
| **Test Data** | `Event ID`: `EVT-2026-001`<br>`Venue Booking Status`: `Confirmed`<br>`Technical Support Status`: `Pending`<br>`Outstanding Requirement`: "AV setup confirmation for Keynote Auditorium" |
| **Expected Result** | - The status of venue booking is displayed as `Confirmed`.<br>- The status of technical support is displayed as `Pending` (or `Confirmed`, `Rejected`, `Unavailable` as applicable).<br>- Outstanding venue and technical support requirements preventing final event confirmation are explicitly displayed to the organiser. |

### TC-003 — View Event Details Reflecting Approved Changes or Rescheduling

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an Event Organiser can view updated event details after a change request or rescheduling has been approved. |
| **Pre-conditions** | - `organiser.alpha@example.test` is authenticated.<br>- Event `Alpha Leadership Forum 2026` had an approved change request resulting in an updated date, venue, and room layout. |
| **Test Steps** | 1. Open the ConnectSphere event page for `Alpha Leadership Forum 2026`.<br>2. Review the event details and arrangement information. |
| **Test Data** | `Event ID`: `EVT-2026-001`<br>`Approved Change`: Rescheduled date to `15 Nov 2026`, updated venue to `Hall B`, updated room layout to `Workshop` |
| **Expected Result** | - The event details accurately reflect the newly approved date, venue, room layout, and associated schedule changes.<br>- Previous obsolete details are replaced with the updated, approved information. |

### TC-004 — Deny Access to Unauthorised Event Details

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Cross-Cutting Quality |
| **Test Scenario** | Verify that an Event Organiser is denied access and cannot view event status or details when attempting to access an event they are not authorised to view. |
| **Pre-conditions** | - `organiser.alpha@example.test` is authenticated.<br>- The account has the `event_organiser` role in `user_role`.<br>- Event `Beta Strategy Retreat 2026` (`EVT-2026-999`) belongs to a different Event Organiser.<br>- Row Level Security (RLS) or authorization logic blocks unauthorised access. |
| **Test Steps** | 1. Log in as `organiser.alpha@example.test`.<br>2. Attempt to navigate directly to `/events/EVT-2026-999` or request `GET /api/events/EVT-2026-999`.<br>3. Observe system response and page content. |
| **Test Data** | `Authenticated User`: `organiser.alpha@example.test`<br>`Unauthorised Event ID`: `EVT-2026-999` |
| **Expected Result** | - Access to the event is denied (e.g., HTTP 403 Forbidden or redirected to an Access Denied / 404 page).<br>- No event details, status, or arrangement information for `Beta Strategy Retreat 2026` are disclosed or rendered. |