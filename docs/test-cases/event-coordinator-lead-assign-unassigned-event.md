# Test Cases — Assign an Unassigned Event Request

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | AC1–AC6 and AC9 — manually select an active Coordinator, assign once, display ownership, remove the request from the queue, retain `requested`, and notify relevant users |
| TC-002 | Authorization | AC7–AC8 — assigned Coordinator gains management access while another Coordinator does not |
| TC-003 | Validation | AC2–AC4 — inactive or ineligible users cannot be selected and an assigned request cannot receive a second Coordinator |
| TC-004 | Authorization | AC10 — non-Lead users cannot assign through the application or directly change `coordinator_id` |

### TC-001 — Assign an Event Coordinator to an Unassigned Request

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an Event Coordinator Lead can assign an Event Coordinator to an unassigned event request. |
| **Pre-conditions** | - An Event Coordinator Lead is authenticated and authorised to perform assignments.<br>- Event request `EVT-301` has status `requested` and no assigned Event Coordinator.<br>- Maya Tan is available for selection as an Event Coordinator. |
| **Test Steps** | 1. Open the unassigned-event queue.<br>2. Select `EVT-301`.<br>3. Select Maya Tan as the Event Coordinator.<br>4. Confirm the assignment.<br>5. View the resulting event assignment.<br>6. Return to the unassigned-event queue.<br>7. Review the notifications triggered by the assignment. |
| **Test Data** | `Event ID`: `EVT-301`<br>`Event Name`: `Regional Innovation Forum 2026`<br>`Event Status`: `requested`<br>`Current Coordinator`: none<br>`Selected Coordinator`: `Maya Tan` |
| **Expected Result** | - `EVT-301` is assigned to Maya Tan.<br>- Maya Tan is displayed as the assigned Event Coordinator.<br>- `EVT-301` remains in status `requested`.<br>- `EVT-301` is no longer displayed in the unassigned-event queue.<br>- An assignment notification is created for Maya Tan.<br>- An assignment notification is created for the Event Organiser. |

### TC-002 — Apply Coordinator Management Access

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Authorization |
| **Test Scenario** | Verify that assignment grants management access only to the selected Coordinator. |
| **Pre-conditions** | - `EVT-301` has been assigned to Maya Tan.<br>- Daniel Koh also holds the Event Coordinator role but is not assigned to `EVT-301`. |
| **Test Steps** | 1. Access the Coordinator workflow as Maya Tan and open `EVT-301`.<br>2. Attempt the same management action as Daniel Koh. |
| **Expected Result** | - Maya Tan can access and manage `EVT-301`.<br>- Daniel Koh cannot manage `EVT-301` through Maya Tan's assignment. |

### TC-003 — Reject Ineligible or Duplicate Assignment

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Validation |
| **Test Scenario** | Verify that only an active Event Coordinator can be selected and that an event cannot receive a second assignment. |
| **Pre-conditions** | - One profile is inactive or lacks the Event Coordinator role.<br>- `EVT-301` is initially unassigned.<br>- Two Leads may attempt to assign it. |
| **Test Steps** | 1. Review the Coordinator selection list.<br>2. Attempt to assign the ineligible user.<br>3. Assign Maya Tan successfully.<br>4. Attempt another initial assignment for `EVT-301`. |
| **Expected Result** | - The ineligible user is not offered as available and cannot be assigned through the API.<br>- Maya Tan is assigned once.<br>- The second assignment is rejected and Maya Tan remains the sole Coordinator. |

### TC-004 — Prevent Unauthorised Assignment

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Authorization |
| **Test Scenario** | Verify that only an Event Coordinator Lead can change an event's Coordinator assignment. |
| **Pre-conditions** | - `EVT-301` is unassigned.<br>- A normal Event Coordinator or Event Organiser is authenticated without the Lead role. |
| **Test Steps** | 1. Attempt assignment through the Lead endpoint.<br>2. Attempt to update `event.coordinator_id` directly through Supabase. |
| **Expected Result** | - The Lead endpoint rejects the user.<br>- The database assignment guard rejects the direct update.<br>- `EVT-301` remains unassigned and no assignment notifications are created. |
