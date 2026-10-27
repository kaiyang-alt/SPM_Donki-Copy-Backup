# Test Cases — Review Event Request

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | View key event request details and identify missing, incomplete, or unclear requirements from the supplied information. |
| TC-002 | Happy Path | Send a clarification message to the Event Organiser, update the request status to “Clarification Required”, and verify that the organiser receives the message. |
| TC-003 | Happy Path | Organiser supplies clarification/amendments, and coordinator reviews the updated request and moves it to `planning`. |
| TC-004 | Negative | AC1, AC2 — prevent a coordinator from viewing or reviewing unassigned requests and requests assigned by the Lead to another coordinator. |

### TC-001 — Review Details and Identify Requirement Gaps

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that the coordinator can review the supplied event details and identify missing, incomplete, or unclear requirements. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- Event request EVT-201 exists and the Event Coordinator Lead assigned it to the authenticated coordinator by setting its assigned coordinator.<br>- EVT-201 has status `requested` and contains the test data below. |
| **Test Steps** | 1. Open event request EVT-201.<br>2. Review its event name, date/time, venue information, expected attendance, event requirements, and requested equipment/resources.<br>3. Identify requirement gaps from the displayed information. |
| **Test Data** | `Event Name`: `Regional Business Conference 2026`<br>`Date/Time`: `20 November 2026, 09:00–17:00`<br>`Venue Requirements`: `Indoor venue for 150 attendees; preferred location not provided`<br>`Expected Attendance`: `150`<br>`Event Requirements`: `Catering required; dietary requirements not provided`<br>`Requested Equipment/Resources`: `Microphones required; quantity not provided` |
| **Expected Result** | - The supplied event name, date/time, venue requirements, expected attendance, event requirements, and requested equipment/resources are visible.<br>- The displayed information preserves the unspecified preferred location, dietary requirements, and microphone quantity without supplying invented values.<br>- The coordinator can identify these gaps by reviewing the request; automatic gap detection is not required by this test. |

### TC-002 — Request Clarification and Deliver the Message

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that the coordinator can request clarification, update the request status, and deliver the clarification message to the organiser. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- The Event Coordinator Lead assigned EVT-201 to the authenticated coordinator, and EVT-201 has status `requested`.<br>- EVT-201 belongs to Event Organiser Priya Tan.<br>- The preferred venue location, dietary requirements, and microphone quantity are unspecified. |
| **Test Steps** | 1. Open EVT-201 as the coordinator.<br>2. Select the option to request clarification or amendments.<br>3. Enter the clarification message.<br>4. Send the message and update the event request status to “Clarification Required” through the available workflow.<br>5. View the resulting request status.<br>6. Access the application as Priya Tan.<br>7. View the clarification message received for EVT-201. |
| **Test Data** | `Event Request`: `EVT-201`<br>`Event Organiser`: `Priya Tan`<br>`Clarification Message`: `Please specify your preferred venue location, the catering dietary requirements, and the number of microphones required.` |
| **Expected Result** | - The clarification message is sent for EVT-201.<br>- The event request displays the story-specified status “Clarification Required”.<br>- Priya Tan receives the message associated with EVT-201.<br>- The received message contains the submitted clarification text. |

### TC-003 — Provide Clarification and Review the Updated Request

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that the organiser can provide the requested information or amendments and that the coordinator can review them and move the event to planning. |
| **Pre-conditions** | - EVT-201 belongs to Event Organiser Priya Tan and was assigned to the reviewing Event Coordinator by the Event Coordinator Lead.<br>- Priya Tan has received a clarification message requesting the preferred venue location, dietary requirements, and microphone quantity.<br>- Priya Tan is authenticated. |
| **Test Steps** | 1. Open EVT-201 and its clarification message as Priya Tan.<br>2. Provide the requested clarification or amendments using the available workflow.<br>3. Submit the information.<br>4. Access the application as the assigned coordinator.<br>5. Open EVT-201.<br>6. Review the submitted clarification or amendments.<br>7. Select Planning and save the review decision. |
| **Test Data** | `Event Request`: `EVT-201`<br>`Preferred Venue Location`: `Central Singapore`<br>`Dietary Requirements`: `20 vegetarian meals; remaining meals halal`<br>`Microphone Quantity`: `3` |
| **Expected Result** | - Priya Tan can submit the requested information or amendments for EVT-201.<br>- The event remains `changes_requested` after the organiser responds.<br>- The coordinator can view the submitted preferred venue location, dietary requirements, and microphone quantity associated with EVT-201.<br>- The displayed values match the organiser’s submission.<br>- After the coordinator saves the satisfactory review decision, the event has status `planning`. |

### TC-004 — Reject Review Access Without the Coordinator's Assignment

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Negative |
| **Test Scenario** | Verify that a coordinator can neither view nor submit a review decision for an unassigned request or a request assigned by the Event Coordinator Lead to another coordinator. |
| **Pre-conditions** | - Event Coordinator Maya Tan is authenticated.<br>- Event request EVT-202 has status `requested` and is unassigned.<br>- The Event Coordinator Lead assigned event request EVT-203 to Event Coordinator Daniel Lim.<br>- Neither EVT-202 nor EVT-203 is assigned to Maya Tan. |
| **Test Steps** | 1. Open the assigned-review list as Maya Tan.<br>2. Attempt to open EVT-202 for review.<br>3. Attempt to submit a review decision for EVT-202.<br>4. Attempt to open EVT-203 for review.<br>5. Attempt to submit a review decision for EVT-203. |
| **Test Data** | `Authenticated Coordinator`: `Maya Tan`<br>`Unassigned Event`: `EVT-202`<br>`Other Coordinator's Event`: `EVT-203`<br>`Assigned Coordinator for EVT-203`: `Daniel Lim`<br>`Attempted Decision`: `planning` |
| **Expected Result** | - Neither EVT-202 nor EVT-203 appears in Maya Tan's assigned-review list.<br>- Maya Tan cannot view either request through the coordinator-review workflow.<br>- Neither review decision is accepted.<br>- The status and assignment of both event requests remain unchanged. |

## Confirmed Clarifications

- “Clarification Required” displays the existing `changes_requested` event status.
- A satisfactory coordinator review moves the event to `planning`; further clarification uses `changes_requested` with a clarification message.
- Venue information means venue requirements. Preferred location and catering information can be supplied in the venue requirements, description, or clarification response; requested microphone quantities can be supplied in technical requirements or the response. No separate fields are required.

## Implementation Dependencies

- The Event Coordinator Lead assignment workflow must set the existing
  `event.coordinator_id`, and the shared RLS/permission design must restrict
  assignment writes so coordinators cannot assign requests to themselves.
- The Lead-role migration referenced by the developer must be present and
  verified during implementation readiness; it is not available in the current
  repository checkout.
