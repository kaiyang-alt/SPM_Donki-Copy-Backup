# Test Cases - Request Event Changes

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | Organiser selects an authorised event, enters change details, reviews the request, submits it, receives confirmation, and views the submitted request with `pending` status. |
| TC-002 | Negative | Organiser cannot create a change request for an event they are not authorised to manage. |
| TC-003 | Negative | Organiser cannot submit a change request before providing change details. |

### TC-001 - Submit Change Request for an Authorised Event

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an Event Organiser can create, review, submit, and view a change request for an event they are authorised to manage. |
| **Pre-conditions** | - An Event Organiser is authenticated.<br>- Event `EVT-201` exists and is managed by the authenticated Event Organiser. |
| **Test Steps** | 1. Open the event change request function.<br>2. Select event `EVT-201`.<br>3. Enter requested changes for the event date, time, expected attendance, programme timings, venue requirements, equipment requirements, and technical support requirements.<br>4. Enter details explaining the requested change.<br>5. Proceed to review the change request.<br>6. Submit the reviewed change request.<br>7. View the submitted change request. |
| **Test Data** | `Event ID`: `EVT-201`<br>`Event Name`: `Regional Business Conference 2026`<br>`Requested Date`: `20 November 2026`<br>`Requested Time`: `10:00 AM to 4:00 PM`<br>`Expected Attendance`: `180`<br>`Programme / Session Timings`: `Opening keynote 10:00 AM, workshop session 1:00 PM, closing remarks 3:30 PM`<br>`Venue Requirements`: `Lecture theatre with fixed seating and stage area`<br>`Equipment Requirements`: `2 wireless microphones, projector, presentation laptop`<br>`Technical Support Requirements`: `On-site technical support during setup and opening keynote`<br>`Change Details`: `The organiser needs to increase attendance and extend the programme due to additional invited speakers.` |
| **Expected Result** | - The selected event is accepted for the change request.<br>- The entered change details are shown for review before submission.<br>- The change request is submitted successfully.<br>- A submission confirmation is shown.<br>- The submitted change request can be viewed.<br>- The submitted change request shows the status `pending`. |

### TC-002 - Prevent Change Request for Unauthorised Event

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Negative |
| **Test Scenario** | Verify that an Event Organiser cannot create a change request for an event they are not authorised to manage. |
| **Pre-conditions** | - An Event Organiser is authenticated.<br>- Event `EVT-301` exists but is not managed by the authenticated Event Organiser. |
| **Test Steps** | 1. Open the event change request function.<br>2. Attempt to select or access event `EVT-301` for a change request.<br>3. Attempt to continue with creating the change request. |
| **Test Data** | `Event ID`: `EVT-301`<br>`Event Name`: `External Partner Networking Night` |
| **Expected Result** | - The organiser is not able to create a change request for event `EVT-301`.<br>- No change request is submitted for event `EVT-301`. |

### TC-003 - Prevent Submission Without Change Details

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Negative |
| **Test Scenario** | Verify that an Event Organiser cannot submit a change request without providing change details. |
| **Pre-conditions** | - An Event Organiser is authenticated.<br>- Event `EVT-202` exists and is managed by the authenticated Event Organiser. |
| **Test Steps** | 1. Open the event change request function.<br>2. Select event `EVT-202`.<br>3. Leave the change details empty.<br>4. Attempt to submit the change request. |
| **Test Data** | `Event ID`: `EVT-202`<br>`Event Name`: `Student Leadership Forum 2026`<br>`Change Details`: empty |
| **Expected Result** | - The change request is not submitted.<br>- The organiser remains able to provide the missing change details.<br>- No submitted change request is created with empty change details. |
