# Test Cases — Assign an Event Request

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | AC1, AC2, AC4, AC5, AC6 — submitted event is auto-assigned to no more than one coordinator, moves to `planning`, and both the assigned coordinator and organiser are notified |
| TC-002 | Unresolved | AC3 — coordinator-selection basis is not specified and cannot yet be tested |
| TC-003 | Negative | AC1 — a user without the `event_coordinator` role is not assigned as the coordinator |
| TC-004 | Negative | AC7 — event that already has a coordinator is not reassigned |
| TC-005 | Happy Path | AC8 — coordinator sees only their own assigned events |
| TC-006 | Happy Path | AC9 — organiser sees whether a coordinator has been assigned |

### TC-001 — Auto-Assign a Submitted Event and Notify Both Parties

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify a submitted event is automatically assigned to no more than one Event Coordinator without assuming which eligible coordinator is selected, moves to `planning`, and both the assigned coordinator and organiser receive notifications. |
| **Pre-conditions** | - `organiser.one@example.test` is authenticated with the `event_organiser` role.<br>- `coordinator.alpha@example.test` and `coordinator.beta@example.test` have the `event_coordinator` role. |
| **Test Steps** | 1. As the organiser, create and submit the event request.<br>2. Open the submitted event's details.<br>3. Record the assigned coordinator.<br>4. View both eligible coordinators' notifications.<br>5. View `organiser.one@example.test`'s notifications. |
| **Test Data** | `Event Name`: `Northstar Industry Forum`<br>`Expected Attendance`: `150`<br>`Preferred Start`: `20 November 2026 09:00`<br>`Preferred End`: `20 November 2026 17:00` |
| **Expected Result** | - The event has exactly one assigned coordinator, who is either `coordinator.alpha@example.test` or `coordinator.beta@example.test`; the test does not require one of them to be preferred.<br>- The event status is `planning`.<br>- Only the assigned coordinator has one new notification confirming ownership of `Northstar Industry Forum`.<br>- `organiser.one@example.test` has one new notification stating a coordinator has been assigned to `Northstar Industry Forum`. |

### TC-002 — Coordinator Selection Basis Is Unresolved

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Unresolved |
| **Test Scenario** | A coordinator-selection test cannot be defined until an authoritative requirement confirms the selection basis. |
| **Pre-conditions** | - The automatic coordinator-selection basis has been confirmed by an authoritative requirement. |
| **Test Steps** | Not defined pending resolution of the Open Question below. |
| **Test Data** | Not defined. |
| **Expected Result** | Not defined. This test must not assume least workload, availability, skill matching, round-robin, or another selection method. |

### TC-003 — User Without Event Coordinator Role Is Not Assigned

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Negative |
| **Test Scenario** | Verify that automatic assignment assigns a user with the `event_coordinator` role rather than a user without that role. |
| **Pre-conditions** | - `organiser.one@example.test` is authenticated with the `event_organiser` role.<br>- `coordinator.beta@example.test` has the `event_coordinator` role.<br>- `organiser.two@example.test` does not have the `event_coordinator` role.<br>- No other Event Coordinators exist. |
| **Test Steps** | 1. As the organiser, create and submit the event request.<br>2. Open the submitted event's details.<br>3. Inspect the assigned coordinator. |
| **Test Data** | `Event Name`: `Lakeside Sustainability Workshop`<br>`Expected Attendance`: `40` |
| **Expected Result** | - The event has one assigned coordinator.<br>- The assigned user has the `event_coordinator` role.<br>- `organiser.two@example.test` is not assigned as the coordinator. |

### TC-004 — Event with an Existing Coordinator Is Not Reassigned

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Negative |
| **Test Scenario** | Verify automatic assignment does not change the coordinator of an event that already has one. |
| **Pre-conditions** | - `organiser.one@example.test` is authenticated with the `event_organiser` role.<br>- Event `Northstar Industry Forum` belongs to the organiser, is assigned to `coordinator.alpha@example.test`, and has status `changes_requested`.<br>- Another user has the `event_coordinator` role. |
| **Test Steps** | 1. As the organiser, open `Northstar Industry Forum`.<br>2. Resubmit the event request.<br>3. Open the event's details.<br>4. View both coordinators' notifications. |
| **Test Data** | `Event Name`: `Northstar Industry Forum`<br>`Current Coordinator`: `coordinator.alpha@example.test`<br>`Status before resubmission`: `changes_requested` |
| **Expected Result** | - The event's coordinator remains `coordinator.alpha@example.test`.<br>- The event status is `requested`.<br>- Neither coordinator receives a new assignment notification for this event. |

### TC-005 — Coordinator Views Their Assigned Events

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-005 |
| **Category** | Happy Path |
| **Test Scenario** | Verify the Assigned Events section lists only events assigned to the logged-in coordinator. |
| **Pre-conditions** | - `coordinator.alpha@example.test` is authenticated with the `event_coordinator` role.<br>- `Northstar Industry Forum` is assigned to `coordinator.alpha@example.test` with status `planning`.<br>- `Harbor Research Symposium` is assigned to `coordinator.beta@example.test`. |
| **Test Steps** | 1. Open the Event Coordinator workspace.<br>2. Select `Assigned Events`. |
| **Test Data** | `Own event`: `Northstar Industry Forum`<br>`Other coordinator's event`: `Harbor Research Symposium` |
| **Expected Result** | - `Northstar Industry Forum` is listed with status `Planning`.<br>- `Harbor Research Symposium` is not listed. |

### TC-006 — Organiser Sees Coordinator Assignment on Their Event

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-006 |
| **Category** | Happy Path |
| **Test Scenario** | Verify the organiser can see whether a coordinator has been assigned to their event. |
| **Pre-conditions** | - `organiser.one@example.test` is authenticated with the `event_organiser` role.<br>- `Northstar Industry Forum` belongs to the organiser and is assigned to `coordinator.alpha@example.test`.<br>- `Lakeside Sustainability Workshop` belongs to the organiser, has status `requested` and no coordinator. |
| **Test Steps** | 1. Open `Northstar Industry Forum`.<br>2. Open `Lakeside Sustainability Workshop`. |
| **Test Data** | `Assigned event`: `Northstar Industry Forum`<br>`Unassigned event`: `Lakeside Sustainability Workshop` |
| **Expected Result** | - Northstar Industry Forum shows coordinator.alpha@example.test's profile name as the assigned Event Coordinator. |

## Open Questions

- What coordinator-selection basis should the system use? The customer has not specified least workload, availability, skill matching, round-robin, or another algorithm.
- If no Event Coordinator can be assigned when an event is submitted, should assignment be retried automatically later, surfaced to someone, or handled another way?
- Should a user who holds both `event_organiser` and `event_coordinator` roles be excluded from being auto-assigned their own event?
