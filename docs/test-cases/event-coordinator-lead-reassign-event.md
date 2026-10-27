# Test Cases — Reassign an Event

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | AC1–AC8 — view the current Coordinator, select another active Coordinator, replace ownership immediately, update access and display, and notify relevant users |
| TC-002 | Authorization | AC5–AC6 — transfer management access from the outgoing Coordinator to the incoming Coordinator |
| TC-003 | Validation | AC2–AC4 — reject inactive, identical, unassigned, or stale reassignment attempts |
| TC-004 | Authorization | AC9 — prevent non-Leads from reassigning through the application or direct database updates |

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

### TC-002 — Transfer Coordinator Management Access

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Authorization |
| **Test Scenario** | Verify that management access follows the current `coordinator_id` immediately after reassignment. |
| **Pre-conditions** | - `EVT-401` is assigned to Maya Tan.<br>- Daniel Koh is an active Event Coordinator. |
| **Test Steps** | 1. Reassign `EVT-401` from Maya Tan to Daniel Koh.<br>2. Access the Coordinator workflow as Daniel Koh.<br>3. Attempt the same management action as Maya Tan. |
| **Expected Result** | - Daniel Koh can access and manage `EVT-401`.<br>- Maya Tan can no longer manage it through the previous assignment.<br>- Only Daniel Koh is stored as the current Coordinator. |

### TC-003 — Reject Invalid or Stale Reassignment

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Validation |
| **Test Scenario** | Verify reassignment preserves one valid current owner and rejects stale updates. |
| **Pre-conditions** | - `EVT-401` is assigned to Maya Tan.<br>- One replacement profile is inactive.<br>- Two Leads may load the same current assignment. |
| **Test Steps** | 1. Attempt to select or submit the inactive replacement.<br>2. Attempt to select Maya Tan as her own replacement.<br>3. Reassign successfully to Daniel Koh.<br>4. Submit a stale reassignment that still expects Maya Tan as current owner.<br>5. Attempt reassignment through this workflow for an unassigned event. |
| **Expected Result** | - The inactive replacement is unavailable and rejected by the service.<br>- The current Coordinator cannot replace themselves.<br>- The valid reassignment succeeds once.<br>- Stale and unassigned attempts are rejected.<br>- Daniel Koh remains the sole current Coordinator. |

### TC-004 — Prevent Unauthorised Reassignment

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Authorization |
| **Test Scenario** | Verify that only an Event Coordinator Lead can replace event ownership. |
| **Pre-conditions** | - `EVT-401` is assigned to Maya Tan.<br>- A normal Coordinator or Event Organiser is authenticated without the Lead role. |
| **Test Steps** | 1. Attempt reassignment through the Lead endpoint.<br>2. Attempt to change `event.coordinator_id` directly through Supabase. |
| **Expected Result** | - The Lead endpoint rejects the user.<br>- The database assignment guard rejects the direct update.<br>- Maya Tan remains assigned and no reassignment notifications are created. |
