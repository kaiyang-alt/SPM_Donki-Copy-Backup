# Test Cases — View Newly Submitted Unassigned Event Requests

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | AC1–AC3 and AC5 — view newly submitted unassigned requests with basic event information, exclude assigned requests, and remove a request after assignment |
| TC-002 | Cross-Cutting Quality | AC6–AC7 — restrict the queue and request details to authenticated Event Coordinator Leads |
| TC-003 | Happy Path | AC4 — open an unassigned request and review its available event information before assignment |

### TC-001 — View Newly Submitted Unassigned Requests

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an Event Coordinator Lead can view submitted event requests requiring coordinator assignment and distinguish them from assigned requests. |
| **Pre-conditions** | - An Event Coordinator Lead is authenticated.<br>- Event request `EVT-301` has status `requested` and no assigned Event Coordinator.<br>- Event request `EVT-302` has status `requested` and is assigned to Maya Tan. |
| **Test Steps** | 1. Open the Event Coordinator Lead workspace.<br>2. Open the newly submitted unassigned-event queue.<br>3. Review the requests displayed in the queue.<br>4. Assign `EVT-301` to an Event Coordinator.<br>5. Review the refreshed queue. |
| **Test Data** | `Unassigned Event ID`: `EVT-301`<br>`Unassigned Event Name`: `Regional Innovation Forum 2026`<br>`Unassigned Event Status`: `requested`<br>`Preferred Start`: `25 November 2026, 9:00 AM`<br>`Preferred End`: `25 November 2026, 5:00 PM`<br>`Expected Attendance`: `180`<br>`Unassigned Coordinator`: none<br>`Assigned Event ID`: `EVT-302`<br>`Assigned Event Name`: `Community Leadership Workshop`<br>`Assigned Event Status`: `requested`<br>`Assigned Coordinator`: `Maya Tan` |
| **Expected Result** | - `EVT-301` is displayed in the unassigned-event queue.<br>- Its event ID, name, `requested` status, preferred start and end dates, and expected attendance are displayed.<br>- `EVT-301` is visibly marked as unassigned.<br>- `EVT-302` is not displayed in the unassigned-event queue.<br>- After successful assignment and refresh, `EVT-301` is no longer displayed in the unassigned-event queue. |

### TC-002 — Restrict Access to the Unassigned Queue

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Cross-Cutting Quality |
| **Test Scenario** | Verify that a user without the Event Coordinator Lead role cannot access the unassigned-event queue. |
| **Pre-conditions** | - Event request `EVT-301` has status `requested` and no assigned Event Coordinator.<br>- Maya Tan is authenticated with the `event_coordinator` role and does not have the `event_coordinator_lead` role. |
| **Test Steps** | 1. Access ConnectSphere as Maya Tan.<br>2. Attempt to open the newly submitted unassigned-event queue.<br>3. Attempt to open the details of `EVT-301` through the Lead endpoint. |
| **Test Data** | `User`: `Maya Tan`<br>`Role`: `event_coordinator`<br>`Unassigned Event`: `EVT-301` |
| **Expected Result** | - Maya Tan cannot access the unassigned-event queue.<br>- Maya Tan cannot open `EVT-301` through the Lead request-detail endpoint.<br>- Information about `EVT-301` is not displayed through the queue or detail endpoint. |

### TC-003 — Open an Unassigned Request Before Assignment

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an Event Coordinator Lead can open an unassigned request and review its available event information before choosing a Coordinator. |
| **Pre-conditions** | - An Event Coordinator Lead is authenticated.<br>- Event request `EVT-301` has status `requested` and no assigned Event Coordinator. |
| **Test Steps** | 1. Open the unassigned-event queue.<br>2. Select **Open request** for `EVT-301`.<br>3. Review the request details. |
| **Test Data** | `Event ID`: `EVT-301`<br>`Name`: `Regional Innovation Forum 2026`<br>`Purpose`: `Regional collaboration`<br>`Description`: `A forum for regional innovators.`<br>`Venue Requirements`: `Accessible lecture theatre`<br>`Technical Requirements`: `Projector and microphones` |
| **Expected Result** | - The details for `EVT-301` are displayed.<br>- The available submitted event information is shown.<br>- The request remains visibly unassigned.<br>- Opening the request does not assign a Coordinator or change its `requested` status. |

