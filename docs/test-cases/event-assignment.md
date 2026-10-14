# Test Cases — Assign an Event Request

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | AC1, AC4, AC5, AC6 — submitted event is auto-assigned to one coordinator, moves to `planning`, and both coordinator and organiser are notified |
| TC-002 | Happy Path | AC3 — coordinator with the lowest active workload is selected |
| TC-003 | Negative | AC2 — inactive coordinator is never assigned |
| TC-004 | Negative | AC7 — event that already has a coordinator is not reassigned |
| TC-005 | Happy Path | AC8 — coordinator sees only their own assigned events |
| TC-006 | Happy Path | AC9 — organiser sees whether a coordinator has been assigned |

### TC-001 — Auto-Assign a Submitted Event and Notify Both Parties

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify a submitted event is automatically assigned to one active coordinator, moves to `planning`, and both the coordinator and organiser receive notifications. |
| **Pre-conditions** | - `organiser.one@example.test` is authenticated with the `event_organiser` role.<br>- `coordinator.alpha@example.test` has the `event_coordinator` role, an active profile, and no assigned events.<br>- No other active Event Coordinators exist. |
| **Test Steps** | 1. As the organiser, create and submit the event request.<br>2. Open the submitted event's details.<br>3. View `coordinator.alpha@example.test`'s notifications.<br>4. View `organiser.one@example.test`'s notifications. |
| **Test Data** | `Event Name`: `Northstar Industry Forum`<br>`Expected Attendance`: `150`<br>`Preferred Start`: `20 November 2026 09:00`<br>`Preferred End`: `20 November 2026 17:00` |
| **Expected Result** | - The event's coordinator is `coordinator.alpha@example.test`.<br>- The event status is `planning`.<br>- `coordinator.alpha@example.test` has one new notification confirming ownership of `Northstar Industry Forum`.<br>- `organiser.one@example.test` has one new notification stating a coordinator has been assigned to `Northstar Industry Forum`. |

### TC-002 — Select the Coordinator with the Lowest Active Workload

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Happy Path |
| **Test Scenario** | Verify the eligible coordinator with the fewest active events is selected. |
| **Pre-conditions** | - `organiser.one@example.test` is authenticated with the `event_organiser` role.<br>- `coordinator.alpha@example.test` is active and assigned 3 events in `planning`.<br>- `coordinator.beta@example.test` is active and assigned 1 event in `planning`.<br>- No other active Event Coordinators exist. |
| **Test Steps** | 1. As the organiser, create and submit the event request.<br>2. Open the submitted event's details.<br>3. View both coordinators' notifications. |
| **Test Data** | `Event Name`: `Harbor Research Symposium`<br>`Expected Attendance`: `80` |
| **Expected Result** | - The event's coordinator is `coordinator.beta@example.test`.<br>- The event status is `planning`.<br>- Only `coordinator.beta@example.test` receives an assignment notification for `Harbor Research Symposium`. |

### TC-003 — Inactive Coordinator Is Not Assigned

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Negative |
| **Test Scenario** | Verify a coordinator with an inactive profile is excluded even when they have the lowest workload. |
| **Pre-conditions** | - `organiser.one@example.test` is authenticated with the `event_organiser` role.<br>- `coordinator.gamma@example.test` has the `event_coordinator` role, `profile.active = false`, and no assigned events.<br>- `coordinator.beta@example.test` is active and assigned 2 events in `planning`.<br>- No other active Event Coordinators exist. |
| **Test Steps** | 1. As the organiser, create and submit the event request.<br>2. Open the submitted event's details.<br>3. View `coordinator.gamma@example.test`'s notifications. |
| **Test Data** | `Event Name`: `Lakeside Sustainability Workshop`<br>`Expected Attendance`: `40` |
| **Expected Result** | - The event's coordinator is `coordinator.beta@example.test`.<br>- `coordinator.gamma@example.test` receives no assignment notification for this event. |

### TC-004 — Event with an Existing Coordinator Is Not Reassigned

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Negative |
| **Test Scenario** | Verify automatic assignment does not change the coordinator of an event that already has one. |
| **Pre-conditions** | - `organiser.one@example.test` is authenticated with the `event_organiser` role.<br>- Event `Northstar Industry Forum` belongs to the organiser, is assigned to `coordinator.alpha@example.test`, and has status `changes_requested`.<br>- `coordinator.beta@example.test` is active and has fewer active events than `coordinator.alpha@example.test`. |
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

- If no active Event Coordinator exists when an event is submitted, the event currently remains `requested` and unassigned. Should it be retried automatically later, surfaced to someone, or is this acceptable?
- Should a user who holds both `event_organiser` and `event_coordinator` roles be excluded from being auto-assigned their own event?
- Should `confirmed` events count toward a coordinator's active workload, or only `requested` / `changes_requested` / `planning`?