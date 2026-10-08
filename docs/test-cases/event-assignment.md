# Test Cases — Assign an Event Request

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | Display unassigned event requests in the Event Coordinator workspace queue |
| TC-002 | Happy Path | Assign an unassigned request to an active Event Coordinator, update the coordinator and event status, and notify the assigned coordinator |
| TC-003 | Negative | Prevent another coordinator from claiming an event after it has been assigned |

### TC-001 — View the Unassigned Requests Queue

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify the Event Coordinator workspace displays requests that have not yet been assigned to a coordinator. |
| **Pre-conditions** | - `coordinator.alpha@example.test` is authenticated and has the `event_coordinator` role.<br>- Event request `Northstar Industry Forum` exists with no assigned coordinator.<br>- Event request `Harbor Research Symposium` exists and is already assigned to a coordinator. |
| **Test Steps** | 1. Open the Event Coordinator workspace.<br>2. View the `Unassigned Requests` queue. |
| **Test Data** | `Unassigned event`: `Northstar Industry Forum`; status `Submitted`; coordinator: none<br>`Assigned event`: `Harbor Research Symposium`; coordinator: `coordinator.beta@example.test` |
| **Expected Result** | - The `Unassigned Requests` queue is displayed.<br>- `Northstar Industry Forum` appears in the queue.<br>- `Harbor Research Symposium` does not appear in the unassigned queue. |

### TC-002 — Assign an Unassigned Request to an Active Coordinator

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Happy Path |
| **Test Scenario** | Verify an Event Coordinator can assign an unassigned request to an active Event Coordinator and the assignment, status transition, and ownership notification are reflected. |
| **Pre-conditions** | - `coordinator.alpha@example.test` is authenticated and has the `event_coordinator` role.<br>- `coordinator.beta@example.test` is an active Event Coordinator.<br>- Event request `Northstar Industry Forum` exists with no assigned coordinator and status `Submitted`. |
| **Test Steps** | 1. Open the `Unassigned Requests` queue.<br>2. Select `Northstar Industry Forum`.<br>3. Assign it to `coordinator.beta@example.test` using the available assignment control.<br>4. View the assigned event and the assigned coordinator's notifications. |
| **Test Data** | `Event`: `Northstar Industry Forum`<br>`Assigning coordinator`: `coordinator.alpha@example.test`<br>`Assigned coordinator`: `coordinator.beta@example.test` (active; role `event_coordinator`)<br>`Event status before assignment`: `Submitted` |
| **Expected Result** | - The event is assigned to `coordinator.beta@example.test`.<br>- The event status changes from `Submitted` to `In Review`.<br>- `coordinator.beta@example.test` receives an automated notification confirming ownership. |

### TC-003 — Prevent a Second Coordinator from Claiming an Assigned Request

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Negative |
| **Test Scenario** | Verify another Event Coordinator cannot claim an event after a coordinator has already been assigned. |
| **Pre-conditions** | - `coordinator.alpha@example.test` and `coordinator.beta@example.test` are authenticated Event Coordinators.<br>- Event request `Northstar Industry Forum` is assigned to `coordinator.alpha@example.test`. |
| **Test Steps** | 1. Open the Event Coordinator workspace as `coordinator.beta@example.test`.<br>2. Attempt to claim `Northstar Industry Forum` from the unassigned queue or event view.<br>3. View the event assignment and status. |
| **Test Data** | `Event`: `Northstar Industry Forum`<br>`Current assigned coordinator`: `coordinator.alpha@example.test`<br>`Coordinator attempting claim`: `coordinator.beta@example.test` |
| **Expected Result** | - The second coordinator cannot claim or assign the event.<br>- The event remains assigned to `coordinator.alpha@example.test`.<br>- The event's status is unchanged by the rejected claim. |

## Open Questions

- Manual self-assignment or coordinator selection conflicts with the shared project rule that submitted events receive one coordinator through a fair automatic assignment approach. Should this story replace that rule or use automatic assignment instead?
- The story uses `Submitted` and `In Review`, but these are not current event statuses. What existing statuses should represent these states, or has a status change been approved?
- Who is authorized to assign a request to another coordinator, rather than to themselves?
- The documented Row Level Security policy permits coordinators to update events already assigned to them, not to assign unassigned events. What approved access path should support this assignment?
- The current notification policy documentation does not specify who may create notification records. What approved mechanism should trigger the ownership notification?
