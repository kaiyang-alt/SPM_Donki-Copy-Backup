# Test Cases — Approve or Reject a Submitted Event Request

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | AC1, AC3, AC4, AC5, AC6 — approve a submitted request, persist `approved`, enable downstream actions, notify the organiser, and record the audit history |
| TC-002 | Happy Path | AC1, AC2, AC3, AC4, AC5, AC6 — reject a submitted request with mandatory feedback, keep downstream actions disabled, notify the organiser, and record the audit history |
| TC-003 | Negative | AC2 — prevent rejection when mandatory feedback is missing and apply no decision side effects |
| TC-004 | Happy Path | Confirmed clarification for AC3, AC4, AC5, AC6 — approve a request after organiser clarification without optional approval feedback and use the default approval notification |

### TC-001 — Approve a Submitted Event Request

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that the assigned Event Coordinator can approve a submitted event request and that the decision updates the event, downstream actions, organiser notification, and audit history. |
| **Pre-conditions** | - Event Coordinator `coordinator.alpha@example.test` is authenticated and assigned to event `EVT-401`.<br>- `EVT-401` belongs to Event Organiser `organiser.alpha@example.test` and has persisted status `requested`.<br>- Venue and equipment reservation actions are unavailable before the decision. |
| **Test Steps** | 1. Open `EVT-401` in the Event Review interface.<br>2. Verify that distinct `Approve` and `Reject` controls are displayed.<br>3. Enter the optional feedback note.<br>4. Select `Approve` and confirm the decision.<br>5. Reopen the event and inspect its downstream reservation actions and audit history.<br>6. Access the organiser's notifications. |
| **Test Data** | `Event ID`: `EVT-401`<br>`Event Name`: `Regional Innovation Forum`<br>`Decision`: `Approve`<br>`Feedback`: `Requirements are complete; venue and equipment planning may proceed.` |
| **Expected Result** | - The Event Review interface displays the decision as `Approved`.<br>- The event's persisted status is `approved`.<br>- Venue and equipment reservation actions are enabled for the event.<br>- The organiser receives an automated notification containing the `Approved` outcome and the submitted feedback.<br>- The event audit history records the change from `requested` to `approved`, the deciding Coordinator's user ID in `actor_id`, and the status-change timestamp. |

### TC-002 — Reject a Submitted Event Request with Feedback

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that the assigned Event Coordinator can reject a submitted event request after providing the required feedback. |
| **Pre-conditions** | - Event Coordinator `coordinator.alpha@example.test` is authenticated and assigned to event `EVT-402`.<br>- `EVT-402` belongs to Event Organiser `organiser.beta@example.test` and has persisted status `requested`. |
| **Test Steps** | 1. Open `EVT-402` in the Event Review interface.<br>2. Select `Reject`.<br>3. Enter the rejection feedback.<br>4. Confirm the decision.<br>5. Reopen the event and inspect its downstream reservation actions and audit history.<br>6. Access the organiser's notifications. |
| **Test Data** | `Event ID`: `EVT-402`<br>`Event Name`: `Community Partnership Summit`<br>`Decision`: `Reject`<br>`Feedback`: `The submitted safety and accessibility requirements are insufficient for the proposed event.` |
| **Expected Result** | - The Event Review interface displays the decision as `Rejected`.<br>- The event's persisted status is `rejected`.<br>- Venue and equipment reservation actions remain unavailable.<br>- The organiser receives an automated notification containing the `Rejected` outcome and the complete submitted feedback.<br>- The event audit history records the change from `requested` to `rejected`, the deciding Coordinator's user ID in `actor_id`, and the status-change timestamp. |

### TC-003 — Prevent Rejection Without Mandatory Feedback

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Negative |
| **Test Scenario** | Verify that an Event Coordinator cannot reject a submitted event request without providing text feedback. |
| **Pre-conditions** | - Event Coordinator `coordinator.alpha@example.test` is authenticated and assigned to event `EVT-403`.<br>- `EVT-403` has persisted status `requested` and has no previous approval or rejection decision. |
| **Test Steps** | 1. Open `EVT-403` in the Event Review interface.<br>2. Select `Reject`.<br>3. Leave the feedback field empty.<br>4. Attempt to confirm the rejection.<br>5. Reopen the event and review the organiser's notifications and event audit history. |
| **Test Data** | `Event ID`: `EVT-403`<br>`Decision`: `Reject`<br>`Feedback`: Empty |
| **Expected Result** | - The rejection is prevented and the interface identifies that feedback is required.<br>- The event remains in persisted status `requested`.<br>- Venue and equipment reservation actions remain unavailable.<br>- No rejection notification is sent to the organiser.<br>- No rejection status-change entry is added to the event audit history. |

### TC-004 — Approve After Clarification Without Optional Feedback

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that the assigned Event Coordinator can approve an event after reviewing organiser clarification and can omit optional approval feedback. |
| **Pre-conditions** | - Event Coordinator `coordinator.alpha@example.test` is authenticated and assigned to event `EVT-404`.<br>- `EVT-404` belongs to Event Organiser `organiser.gamma@example.test` and has persisted status `changes_requested`.<br>- The organiser's clarification response is available in the Event Review interface.<br>- Venue and equipment reservation actions are unavailable before the decision. |
| **Test Steps** | 1. Open `EVT-404` and review the organiser's clarification response.<br>2. Select `Approve` without entering feedback.<br>3. Confirm the decision.<br>4. Reopen the event and inspect its downstream reservation actions and audit history.<br>5. Access the organiser's notifications. |
| **Test Data** | `Event ID`: `EVT-404`<br>`Event Name`: `Sustainable Operations Workshop`<br>`Current persisted status`: `changes_requested`<br>`Decision`: `Approve`<br>`Feedback`: Empty |
| **Expected Result** | - The decision succeeds without requiring approval feedback.<br>- The Event Review interface displays `Approved`, and the event's persisted status is `approved`.<br>- Venue and equipment reservation actions are enabled.<br>- The organiser receives an automated notification containing the `Approved` outcome and the default approval message.<br>- The event audit history records the change from `changes_requested` to `approved`, the deciding Coordinator's user ID in `actor_id`, and the status-change timestamp. |

## Implementation Dependencies

- The automatic-assignment workflow currently moves an assigned event directly
  to `planning`. The approved story requires an assigned submitted event to
  remain `requested` until this decision is made; that cross-story workflow
  change requires coordination with the assignment story owner and team.
- The approved RLS policies supporting authenticated review audit records and
  notifications, including sender access to the returned notification row, are
  applied in Supabase and documented in
  `docs/architecture/database_schema.md`.
- The live `events_status_check` constraint permits the new persisted
  `approved` status as well as every existing event status.
- The venue-booking workflow currently uses persisted status `planning` for
  eligibility and must be changed by its owner to use `approved`.
- The equipment-reservation feature and its `approved` eligibility rule remain
  owned by the equipment story teammate.
- The readiness workflow currently confirms events from `planning` and must be
  changed by its owner to transition ready events from `approved` to
  `confirmed`.
