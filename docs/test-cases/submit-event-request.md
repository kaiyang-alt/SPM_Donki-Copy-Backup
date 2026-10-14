# Test Cases — Submit Event Request

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | Save an incomplete request as a draft, reopen it, and modify it before submission |
| TC-002 | Happy Path | Enter the event requirements, submit with all mandatory information, and see confirmation and status `requested` |
| TC-003 | Negative | Prevent submission and identify the missing field when any mandatory information is absent |

### TC-001 — Save, Reopen, and Modify an Incomplete Draft

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify an Event Organiser can save an incomplete event request as a draft, review it later, and modify it before submission. |
| **Pre-conditions** | - An Event Organiser can access the event-request form. |
| **Test Steps** | 1. Start a new event request and enter an event name and description, leaving other event details incomplete.<br>2. Save the request as a draft.<br>3. Reopen the saved draft.<br>4. Review the saved event details.<br>5. Change the event description and save the draft again. |
| **Test Data** | `Event name`: `Regional Business Conference 2026`<br>`Initial description`: `A conference for regional business leaders.`<br>`Modified description`: `A one-day conference for regional business leaders and industry partners.` |
| **Expected Result** | - The incomplete request is saved with status `draft`.<br>- The saved draft can be reopened and its entered details are displayed.<br>- The Event Organiser can modify the draft and the updated description is retained. |

### TC-002 — Submit an Event Request with Complete Information

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Happy Path |
| **Test Scenario** | Verify an Event Organiser can enter the event requirements and submit the request when the event name, preferred date and time, and expected number of attendees are provided. |
| **Pre-conditions** | - An Event Organiser can access the event-request form. |
| **Test Steps** | 1. Start a new event request.<br>2. Enter the event details in Test Data.<br>3. Submit the event request.<br>4. View the submission confirmation and request status. |
| **Test Data** | `Event name`: `Regional Business Conference 2026`<br>`Description`: `A one-day conference for regional business leaders.`<br>`Purpose`: `Share industry developments and encourage professional networking.`<br>`Category`: `Conference`<br>`Preferred date and time`: `20 November 2026, 09:00-17:00`<br>`Expected attendees`: `150`<br>`Venue and room layout requirements`: `Indoor venue; theatre layout`<br>`Accessibility and facility requirements`: `Step-free access; accessible seating`<br>`Equipment and technical support requirements`: `Projector, microphones, and presentation support`<br>`Registration requirements`: `Attendee registration required`<br>`Special arrangements`: `Allow time for a networking break` |
| **Expected Result** | - The event request is submitted successfully.<br>- A confirmation of successful submission is shown.<br>- The request has status `requested`. |

### TC-003 — Block Submission When Mandatory Information Is Missing

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Negative |
| **Test Scenario** | Verify that submission is prevented and the missing mandatory field is identified when the event name, preferred date and time, or expected number of attendees is missing. |
| **Pre-conditions** | - An Event Organiser can access the event-request form. |
| **Test Steps** | 1. Start a new event request and enter the event details, leaving expected attendees blank.<br>2. Submit the request and note the identified missing field.<br>3. Enter expected attendees, clear preferred date and time, and submit again.<br>4. Enter preferred date and time, clear the event name, and submit again. |
| **Test Data** | `Event name`: `Regional Business Conference 2026` (omit for the third submission attempt)<br>`Preferred date and time`: `20 November 2026, 09:00-17:00` (omit for the second submission attempt)<br>`Expected attendees`: `150` (omit for the first submission attempt)<br>`Other event details`: Use the values in TC-002. |
| **Expected Result** | - Each submission attempt is blocked while its specified mandatory field is missing.<br>- The missing field is identified for each attempt.<br>- No submission succeeds while any mandatory field is missing. |
