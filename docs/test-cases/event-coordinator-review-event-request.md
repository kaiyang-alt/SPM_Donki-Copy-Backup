# Test Cases — Review Event Request

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | Assigned Event Coordinator views the complete request and identifies missing, incomplete, or unclear requirements |
| TC-002 | Happy Path | Assigned Event Coordinator requests clarification, applies the “Clarification Required” display status, and delivers the message to the organiser |
| TC-003 | Happy Path | Organiser submits amendments and the assigned Event Coordinator reviews them and updates the request status |
| TC-004 | Cross-Cutting Quality | Newly submitted requests enter the Lead queue and cannot be managed by an unassigned or different Event Coordinator |

### TC-001 — Assigned Coordinator Reviews Complete Request Details

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that the Event Coordinator assigned by the Event Coordinator Lead can view the complete request and identify requirement gaps. |
| **Pre-conditions** | - Maya Tan is authenticated with the `event_coordinator` role.<br>- Event request `EVT-201` has status `requested`.<br>- The Event Coordinator Lead assigned `EVT-201` to Maya Tan.<br>- `EVT-201` contains the test data below. |
| **Test Steps** | 1. Open the assigned event-request list as Maya Tan.<br>2. Open `EVT-201`.<br>3. Review the assigned coordinator and complete event-request information.<br>4. Identify information that is missing, incomplete, or unclear. |
| **Test Data** | `Event ID`: `EVT-201`<br>`Event Name`: `Regional Business Conference 2026`<br>`Assigned Coordinator`: `Maya Tan`<br>`Preferred Date/Time`: `20 November 2026, 9:00 AM–5:00 PM`<br>`Venue Requirements`: `Indoor venue for 150 attendees; preferred location not provided`<br>`Expected Attendance`: `150`<br>`Event Requirements`: `Catering required; dietary requirements not provided`<br>`Technical Requirements`: `Microphones required; quantity not provided` |
| **Expected Result** | - `EVT-201` appears in Maya Tan’s assigned request list.<br>- Maya Tan is displayed as the assigned Event Coordinator.<br>- The event name, preferred date/time, venue requirements, expected attendance, event requirements, and requested equipment or technical requirements are displayed.<br>- The unspecified preferred location, dietary requirements, and microphone quantity remain visibly incomplete without invented values.<br>- Maya Tan can identify these gaps while reviewing the request. |

### TC-002 — Request Clarification and Deliver the Message

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that the assigned Event Coordinator can request clarification, update the displayed request status, and deliver the clarification message to the organiser. |
| **Pre-conditions** | - Maya Tan is authenticated with the `event_coordinator` role.<br>- `EVT-201` is assigned to Maya Tan and has status `requested`.<br>- `EVT-201` belongs to Event Organiser Priya Tan.<br>- The preferred venue location, dietary requirements, and microphone quantity are unspecified. |
| **Test Steps** | 1. Open `EVT-201` as Maya Tan.<br>2. Select the clarification-required review decision.<br>3. Enter the clarification message.<br>4. Save the review decision.<br>5. View the resulting request status.<br>6. Access ConnectSphere as Priya Tan.<br>7. Open `EVT-201` and review the clarification message. |
| **Test Data** | `Event Request`: `EVT-201`<br>`Assigned Coordinator`: `Maya Tan`<br>`Event Organiser`: `Priya Tan`<br>`Clarification Message`: `Please specify your preferred venue location, catering dietary requirements, and the number of microphones required.` |
| **Expected Result** | - The clarification message is recorded for `EVT-201`.<br>- The request displays “Clarification Required”, representing the existing `changes_requested` status.<br>- Priya Tan receives the clarification message associated with `EVT-201`.<br>- The received message contains the text entered by Maya Tan. |

### TC-003 — Review Organiser Amendments

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that the organiser can submit requested amendments and the assigned Event Coordinator can review them and update the request status. |
| **Pre-conditions** | - `EVT-201` belongs to Priya Tan and is assigned to Maya Tan.<br>- `EVT-201` has status `changes_requested` and displays “Clarification Required”.<br>- Priya Tan received a clarification message requesting venue location, dietary requirements, and microphone quantity.<br>- Priya Tan is authenticated. |
| **Test Steps** | 1. Open `EVT-201` and its clarification message as Priya Tan.<br>2. Enter the requested clarification and amendments.<br>3. Submit the response.<br>4. Access ConnectSphere as Maya Tan.<br>5. Open `EVT-201`.<br>6. Review the submitted response and amended information.<br>7. Select Planning and save the review decision. |
| **Test Data** | `Event Request`: `EVT-201`<br>`Preferred Venue Location`: `Central Singapore`<br>`Dietary Requirements`: `20 vegetarian meals; remaining meals halal`<br>`Microphone Quantity`: `3` |
| **Expected Result** | - Priya Tan can submit the requested clarification and amendments.<br>- The request remains `changes_requested` until Maya Tan reviews it.<br>- Maya Tan can view the organiser’s response and amended information.<br>- The displayed amendments match Priya Tan’s submission.<br>- After Maya Tan saves the satisfactory review decision, `EVT-201` has status `planning`. |

### TC-004 — Enforce Lead-Controlled Assignment Before Review

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Cross-Cutting Quality |
| **Test Scenario** | Verify that a newly submitted request must be assigned by the Event Coordinator Lead before an Event Coordinator can manage or review it. |
| **Pre-conditions** | - Event request `EVT-202` was newly submitted with status `requested` and no assigned Event Coordinator.<br>- Event Coordinator Lead Elena Lim is authenticated.<br>- Event Coordinators Maya Tan and Daniel Koh are available.<br>- Neither coordinator is assigned to `EVT-202`. |
| **Test Steps** | 1. Open the Event Coordinator Lead’s unassigned queue.<br>2. Confirm that `EVT-202` is displayed as unassigned.<br>3. Access ConnectSphere as Maya Tan and attempt to take ownership of or review `EVT-202`.<br>4. Return as Elena Lim and assign `EVT-202` to Daniel Koh.<br>5. View the resulting assignment.<br>6. Access ConnectSphere as Maya Tan and attempt to manage or review `EVT-202`.<br>7. Access ConnectSphere as Daniel Koh and open `EVT-202`. |
| **Test Data** | `Event ID`: `EVT-202`<br>`Event Name`: `Community Partnership Forum`<br>`Event Status`: `requested`<br>`Initial Coordinator`: none<br>`Assigned Coordinator`: `Daniel Koh`<br>`Other Coordinator`: `Maya Tan` |
| **Expected Result** | - `EVT-202` appears in Elena Lim’s unassigned queue before assignment.<br>- Maya Tan cannot take ownership of or review the unassigned request directly.<br>- Elena Lim can assign `EVT-202` to Daniel Koh.<br>- Daniel Koh is displayed as the assigned Event Coordinator.<br>- `EVT-202` no longer appears in the unassigned queue.<br>- Maya Tan cannot manage or review the request assigned to Daniel Koh.<br>- Daniel Koh can view and review the complete request. |
