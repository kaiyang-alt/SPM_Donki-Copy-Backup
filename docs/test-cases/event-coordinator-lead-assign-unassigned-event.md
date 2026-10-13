# Test Cases — Assign an Unassigned Event Request

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | AC1–AC5 — select an unassigned request, assign a coordinator, display the assignment, remove the request from the unassigned queue, and trigger notifications |

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
