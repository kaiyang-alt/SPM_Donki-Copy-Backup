# Test Cases — Track Event Readiness and Outstanding Actions

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | Display `Incomplete` and identify outstanding venue, equipment, programme, and task actions; show unfinished task owners, deadlines, and overdue state |
| TC-002 | Happy Path | Refresh readiness after a relevant status change is saved and display `Ready for Confirmation` once all conditions are met; no reservations and no tasks satisfy their conditions only when the event records no equipment required and no tasks exist, respectively |
| TC-003 | Negative | Recheck current readiness on confirmation attempt, block confirmation when a condition is unmet, retain the existing event status, and display outstanding actions |
| TC-004 | Happy Path | Confirm an event when every readiness condition is met and update event status to `confirmed` |
| TC-005 | Negative | Treat the venue condition as incomplete unless the booking is `Confirmed`, and equipment as incomplete unless every required reservation is `Confirmed` |

### TC-001 — Display Incomplete Readiness and Outstanding Actions

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify readiness is shown as `Incomplete` when multiple conditions remain unmet, with each outstanding action and unfinished task details identified. |
| **Pre-conditions** | - An Event Coordinator is authenticated and assigned to event `Northstar Industry Forum`.<br>- The event has a venue booking that is not `Confirmed`.<br>- At least one required equipment reservation is not `Confirmed`.<br>- Programme setup has a status other than `Completed`.<br>- At least two event tasks have statuses other than `Completed`, including one whose deadline has passed. |
| **Test Steps** | 1. Open the assigned event's readiness view.<br>2. Review the displayed readiness conditions and outstanding actions.<br>3. Review each unfinished task and its responsible person and deadline. |
| **Test Data** | `Event`: `Northstar Industry Forum`<br>`Existing event status`: `planning`<br>`Venue booking status`: `requested`<br>`Equipment reservation`: `Projector`, status `requested`<br>`Programme setup status`: Any status other than `Completed`<br>`Unfinished task 1 status`: Any status other than `Completed`; task `Confirm speaker schedule`; responsible person `Jordan Lee`; deadline `28 September 2026`<br>`Unfinished task 2 status`: Any status other than `Completed`; task `Prepare attendee materials`; responsible person `Mina Patel`; deadline `5 October 2026`<br>`Current date for test`: `30 September 2026` |
| **Expected Result** | - Readiness is displayed as `Incomplete`.<br>- The venue booking, equipment reservation, and programme action are identified as outstanding.<br>- Each unfinished task is listed with its responsible person and deadline.<br>- `Confirm speaker schedule` is marked `Overdue`; `Prepare attendee materials` is not marked `Overdue`. | 

### TC-002 — Refresh Readiness After Completion Conditions Are Saved

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Happy Path |
| **Test Scenario** | Verify readiness refreshes after relevant status changes are saved and becomes `Ready for Confirmation` when all readiness conditions are met, including the explicit no-equipment and no-tasks cases. |
| **Pre-conditions** | - An Event Coordinator is authenticated and assigned to event `Northstar Industry Forum`.<br>- The event has no event tasks.<br>- The event explicitly records `No equipment required` and has no required equipment reservations. |
| **Test Steps** | 1. Open the event's readiness view while the venue booking or programme setup is incomplete.<br>2. Save the venue booking with status `Confirmed` and programme setup with status `Completed`.<br>3. Refresh or revisit the displayed readiness after the saved status changes. |
| **Test Data** | `Event`: `Northstar Industry Forum`<br>`Venue booking status after save`: `Confirmed`<br>`Equipment requirement`: `No equipment required`<br>`Equipment reservations`: None<br>`Programme setup status after save`: `Completed`<br>`Event tasks`: None |
| **Expected Result** | - Readiness updates after the relevant status changes are saved.<br>- The venue condition is complete because the venue booking is `Confirmed`.<br>- The equipment condition is complete because the event explicitly records `No equipment required`.<br>- The programme condition is complete because its status is `Completed`.<br>- The task condition is satisfied because no tasks exist.<br>- Readiness is displayed as `Ready for Confirmation`. | 

### TC-003 — Block Confirmation When Current Readiness Is Incomplete

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Negative |
| **Test Scenario** | Verify confirmation uses current readiness conditions and is blocked when an outstanding action remains, even if the displayed readiness had previously indicated readiness. |
| **Pre-conditions** | - An Event Coordinator is authenticated and assigned to event `Northstar Industry Forum`.<br>- The event currently has status `planning`.<br>- The displayed readiness was `Ready for Confirmation` before a relevant status change was saved.<br>- A required equipment reservation is now saved with a status other than `Confirmed`, and the event does not record `No equipment required`. |
| **Test Steps** | 1. Open the event's readiness view.<br>2. Attempt to confirm the event.<br>3. Review the event status and displayed outstanding actions. |
| **Test Data** | `Event`: `Northstar Industry Forum`<br>`Event status before confirmation attempt`: `planning`<br>`Venue booking status`: `Confirmed`<br>`Equipment reservation`: `Projector`, status `requested`<br>`Programme setup status`: `Completed`<br>`Event tasks`: All `Completed` |
| **Expected Result** | - The current readiness conditions are checked when confirmation is attempted.<br>- Confirmation is prevented because the required equipment reservation is not `Confirmed` and no `No equipment required` choice is recorded.<br>- The event retains its existing status `planning`.<br>- The equipment reservation is displayed as an outstanding action. | 

### TC-004 — Confirm an Event When All Readiness Conditions Are Met

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Happy Path |
| **Test Scenario** | Verify an Event Coordinator can confirm an event when all readiness conditions are met. |
| **Pre-conditions** | - An Event Coordinator is authenticated and assigned to event `Northstar Industry Forum`.<br>- The event currently has status `planning`.<br>- The venue booking is `Confirmed`.<br>- Every required equipment reservation is `Confirmed`.<br>- Programme setup is `Completed`.<br>- Every event task is `Completed`. |
| **Test Steps** | 1. Open the assigned event's readiness view.<br>2. Verify the displayed readiness.<br>3. Attempt to confirm the event.<br>4. View the event status. |
| **Test Data** | `Event`: `Northstar Industry Forum`<br>`Event status before confirmation`: `planning`<br>`Venue booking status`: `Confirmed`<br>`Equipment reservation`: `Projector`, status `Confirmed`<br>`Programme setup status`: `Completed`<br>`Event task`: `Confirm speaker schedule`, status `Completed` |
| **Expected Result** | - Readiness is displayed as `Ready for Confirmation`.<br>- The event is confirmed successfully.<br>- The event status is updated to `confirmed`. | 

### TC-005 — Require Confirmed Venue and Equipment Arrangements

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-005 |
| **Category** | Negative |
| **Test Scenario** | Verify that a venue booking is not complete before it is `Confirmed` and that equipment is not complete until every required reservation is `Confirmed`. |
| **Pre-conditions** | - An Event Coordinator is authenticated and assigned to event `Northstar Industry Forum`.<br>- The event has a venue booking, required equipment reservations, programme setup, and event tasks. |
| **Test Steps** | 1. Open the event's readiness view with the statuses in Test Data.<br>2. Review the readiness and the venue and equipment outstanding actions.<br>3. Save the venue booking as `Confirmed` and the `Projector` reservation as `Confirmed`.<br>4. Review the refreshed readiness. |
| **Test Data** | `Event`: `Northstar Industry Forum`<br>`Venue booking status before update`: `tentative`<br>`Equipment reservations before update`: `Projector` status `requested`; `Microphone` status `confirmed`<br>`Programme setup status`: `Completed`<br>`Event task status`: `Completed` |
| **Expected Result** | - Before the updates, readiness is `Incomplete`.<br>- The venue booking is outstanding while its status is not `Confirmed`.<br>- The equipment condition is outstanding while any required reservation is not `Confirmed`.<br>- After both status changes are saved, readiness refreshes and displays `Ready for Confirmation`. |

## Open Questions

- What existing data source or approved schema change will provide programme setup status?
- What existing data source or approved schema change will provide event tasks, their statuses, responsible people, and deadlines?
- How and where does an event explicitly record `No equipment required`?
- What exact stored status values represent the supplied display labels `Confirmed` and `Completed`, and what values represent unfinished programme setup and event tasks? The existing database documents lowercase booking and event statuses, but programme and task status values are not specified.
- Which existing event statuses are eligible for confirmation?
