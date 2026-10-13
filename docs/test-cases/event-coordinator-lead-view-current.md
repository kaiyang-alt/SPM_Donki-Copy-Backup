# Test Cases — View Current Event Coordinator Assignments

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | AC1, AC2 and AC4 — view an active event with its currently assigned Event Coordinator and approved basic information |
| TC-002 | Happy Path | AC2–AC4 — identify an active event request that remains unassigned and view its approved basic information |

### TC-001 — View an Event's Current Coordinator Assignment

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an Event Coordinator Lead can view an event together with its currently assigned Event Coordinator and basic event information. |
| **Pre-conditions** | - An Event Coordinator Lead is authenticated and authorised to view assignment information.<br>- Event `EVT-501` is in the active `planning` status.<br>- Event `EVT-501` is assigned to Maya Tan. |
| **Test Steps** | 1. Open the current Event Coordinator assignments.<br>2. Locate event `EVT-501`.<br>3. View the assignment information displayed for the event. |
| **Test Data** | `Event ID`: `EVT-501`<br>`Event Name`: `Community Leadership Summit`<br>`Event Status`: `planning`<br>`Confirmed Start`: `20 November 2026, 10:00 AM`<br>`Confirmed End`: `20 November 2026, 4:00 PM`<br>`Assigned Coordinator`: `Maya Tan` |
| **Expected Result** | - Event `EVT-501` is displayed under assigned active events.<br>- Maya Tan is displayed as its currently assigned Event Coordinator.<br>- The event ID, name, `planning` status, and confirmed start and end dates are displayed. |

### TC-002 — Identify an Unassigned Event Request

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an Event Coordinator Lead can identify an event request with no assigned Event Coordinator. |
| **Pre-conditions** | - An Event Coordinator Lead is authenticated and authorised to view assignment information.<br>- Event request `EVT-502` is in the active `requested` status.<br>- Event request `EVT-502` has no assigned Event Coordinator. |
| **Test Steps** | 1. Open the current Event Coordinator assignments.<br>2. Locate event request `EVT-502`.<br>3. View its assignment information. |
| **Test Data** | `Event ID`: `EVT-502`<br>`Event Name`: `Regional Innovation Forum`<br>`Event Status`: `requested`<br>`Preferred Start`: `25 November 2026, 9:00 AM`<br>`Preferred End`: `25 November 2026, 5:00 PM`<br>`Assigned Coordinator`: none |
| **Expected Result** | - Event request `EVT-502` is displayed under unassigned active requests.<br>- The request is visibly identified as unassigned.<br>- The event ID, name, `requested` status, and preferred start and end dates are displayed.<br>- No Event Coordinator is displayed as the request's current owner. |
