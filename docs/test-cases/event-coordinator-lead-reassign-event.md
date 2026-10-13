# Test Cases — Reassign an Event

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | AC1–AC6 — view the current coordinator, select another coordinator, replace ownership without coordinator approval, update management access, and notify the relevant users |

### TC-001 — Replace the Assigned Event Coordinator

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an Event Coordinator Lead can replace an event's current Event Coordinator without requiring approval from either coordinator. |
| **Pre-conditions** | - An Event Coordinator Lead is authenticated and authorised to perform reassignment.<br>- Event `EVT-401` is assigned to Maya Tan.<br>- Daniel Koh is available for selection as another Event Coordinator. |
| **Test Steps** | 1. Open the current Event Coordinator assignments.<br>2. Open event `EVT-401`.<br>3. View the currently assigned Event Coordinator.<br>4. Select Daniel Koh as the replacement Event Coordinator.<br>5. Confirm the reassignment.<br>6. View the resulting event assignment.<br>7. Access `EVT-401` as Daniel Koh and attempt to manage it.<br>8. Access `EVT-401` as Maya Tan and attempt to manage it through the previous assignment.<br>9. Review the notifications received by Maya Tan, Daniel Koh, and the Event Organiser. |
| **Test Data** | `Event ID`: `EVT-401`<br>`Event Name`: `Digital Futures Forum`<br>`Event Organiser`: `Ai Wei`<br>`Previous Coordinator`: `Maya Tan`<br>`Replacement Coordinator`: `Daniel Koh` |
| **Expected Result** | - Maya Tan is displayed as the current Event Coordinator before reassignment.<br>- Daniel Koh is available for selection as another Event Coordinator.<br>- The reassignment completes without approval from Maya Tan or Daniel Koh.<br>- Daniel Koh replaces Maya Tan and is displayed as the current Event Coordinator.<br>- Daniel Koh can manage `EVT-401` through the new assignment.<br>- Maya Tan can no longer manage `EVT-401` through the previous assignment.<br>- Maya Tan receives a notification that she is no longer assigned to `EVT-401`.<br>- Daniel Koh receives a notification that he is now assigned to `EVT-401`.<br>- Ai Wei receives a notification that the Event Coordinator for `EVT-401` has changed. |
