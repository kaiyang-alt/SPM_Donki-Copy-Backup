# Test Cases — Reserve Equipment

These are functional acceptance targets for [Reserve Equipment](../user-stories/reserve-equipment.md), not execution results or a claim that the feature is implemented. TC-001–TC-004 retain their existing IDs; TC-005 and TC-006 cover the confirmed pooled-stock and adjacent-period rules.

## Test Setup and Confirmed Rules

- Technical Support Staff is the reviewing team. Each case starts with existing Coordinator-created requests; Coordinator request creation and login are dependencies, not actions under test.
- Eligible events have status `planning` or `confirmed`. Requests awaiting review have `equipment_reservation.status = planning`; successful acceptance updates the same request to `reserved`.
- Pending requests may coexist and do not automatically consume stock. An unsuccessful acceptance attempt must not create a new reservation or change the request to `reserved`. No rejection/cancellation status is assumed.
- Equipment type and total stock come from `equipment`; required quantity and period come from the linked `equipment_reservation` request. Actual fixture rows use existing UUID identifiers; names below identify those rows for the tester.
- All dates/times below are displayed in `Asia/Singapore` (`UTC+08:00`). Stored timestamps represent the same instants, regardless of their recorded offsets.
- `reserved` quantities and `active` maintenance quantities reduce stock only during their recorded periods. Maintenance fixtures use `equipment_unavailability.quantity_unavailable`, `start_datetime`, and `end_datetime`. Ignore `cancelled` records; report a data error for NULL status. These are confirmed existing unavailability status rules.
- All sessions have the `technical_support` role and RLS access to event details, catalogue stock, requests, overlapping reservations for other events, and maintenance records. RLS permits updating requests. These are setup dependencies, not evidence that the reported live policies have been verified.
- Overlap is `A.start_datetime < B.end_datetime AND B.start_datetime < A.end_datetime`. Adjacent periods do not overlap.
- Availability must suffice throughout the requested period. Separate commitments at different times are not automatically concurrent.
- The approved acceptance RPC provisionally allocates earlier feasible `planning` requests in `requested_at` order without updating them. Earlier infeasible requests do not consume provisional stock. Equal/missing timestamps requiring a priority decision produce an error; no guessed tie-break is allowed. Technical Support review is required before acceptance.

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | AC1–AC4 — Review an existing request, view requirements and availability, accept it as `reserved`, and reopen its confirmation. |
| TC-002 | Boundary | AC2–AC5 — Maintenance reduces stock; accept exactly the remaining quantity and prevent acceptance above it. |
| TC-003 | Negative | AC2, AC5, AC6 — Existing overlapping `reserved` quantities exhaust stock; prevent acceptance and retain both request and reservation history. |
| TC-004 | Negative | AC3–AC6 and earliest-request clarification — Competing pending requests remain uncommitted before review; concurrent acceptance commits only the earlier request when only one unit exists. |
| TC-005 | Boundary | AC2–AC6 and pooled-stock clarification — Allow overlapping reservations within total stock, block excess, and distinguish concurrent from sequential commitments. |
| TC-006 | Boundary | AC2–AC4, AC6 and adjacent-period clarification — Exact period boundaries release stock without a stored status cleanup. |

### TC-001 — Accept an Existing Request for Available Equipment

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that Technical Support can review the required type and quantity, check period availability, accept the existing request, and reopen the saved reservation. |
| **Pre-conditions** | - Technical Support is authenticated and has the access described in Test Setup.<br>- Event `Northstar Industry Forum` has status `planning`.<br>- Its Coordinator-created request for `Presentation Projector` has status `planning`, requires one unit, and has populated `requested_at` and period fields.<br>- Equipment type is `Projector`, total quantity is `1`, and no other reservation, competing request, or maintenance affects the period.<br>- Note the request's existing `reservation_id`. |
| **Test Steps** | 1. Open the existing equipment request for `Northstar Industry Forum`.<br>2. Review the equipment type, required quantity, date, time, and current status.<br>3. Check availability.<br>4. Accept the request following Technical Support review.<br>5. View the confirmation.<br>6. Reopen the same request and event details.<br>7. Repeat in an independent setup with the event initially `confirmed` and an unaccepted `planning` request. |
| **Test Data** | `Event`: `Northstar Industry Forum`<br>`Event status variants`: `planning`, `confirmed`<br>`Equipment`: `Presentation Projector`<br>`Type`: `Projector`<br>`Total / Required quantity`: `1 / 1`<br>`Date`: `20 November 2026`<br>`Period`: `09:00–12:00`<br>`Request status before / after acceptance`: `planning / reserved` |
| **Expected Result** | - The request shows type `Projector`, required quantity `1`, and the Coordinator's requested period.<br>- Before review acceptance, its status remains `planning`; opening/checking availability does not reserve it.<br>- One unit is available throughout the period.<br>- Acceptance updates the existing request to `reserved`, preserving its `reservation_id`, event, equipment, quantity, period, and original submission history; no duplicate row is created.<br>- Confirmation shows `Northstar Industry Forum`, `Presentation Projector`, `20 November 2026`, and `09:00–12:00` in Singapore time.<br>- Reopening shows the saved reservation and status.<br>- The event retains its original status in each variant; acceptance does not automatically confirm it. |

### TC-002 — Apply the Maintenance Quantity Boundary

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Boundary |
| **Test Scenario** | Verify that maintenance reduces available stock, a request for the exact remaining quantity can be accepted, and a larger request cannot be accepted. |
| **Pre-conditions** | - Technical Support has the access described in Test Setup.<br>- `Wireless Microphone` has type `Microphone` and total quantity `3`.<br>- An effective maintenance record makes two units unavailable for the entire requested period; its stored status is `active`.<br>- No reserved stock or competing requests affect the period.<br>- Independent setup A contains a `planning` request for one unit for `Leadership Briefing`; setup B contains a `planning` request for two units for `Panel Discussion`. Both events are `planning`.<br>- Each setup starts with the same stock and maintenance; acceptance in A does not affect B. |
| **Test Steps** | 1. In setup A, open the existing request for `Leadership Briefing`.<br>2. Review requirements and availability, accept the request, and view confirmation.<br>3. In independent setup B, open the existing request for `Panel Discussion`.<br>4. Review requirements and availability.<br>5. Attempt to accept the two-unit request.<br>6. Reopen the request and view its status. |
| **Test Data** | `Equipment`: `Wireless Microphone`<br>`Total quantity`: `3`<br>`Maintenance quantity`: `2`<br>`Remaining available quantity`: `1`<br>`Setup A required quantity`: `1`<br>`Setup B required quantity`: `2`<br>`Date`: `20 November 2026`<br>`Maintenance and request period`: `13:00–15:00` |
| **Expected Result** | - Both setups show only one unit available throughout the period.<br>- Setup A updates its existing request to `reserved` and shows confirmation with event, equipment, date, and time.<br>- Setup B displays a clear insufficient-equipment message and prevents final acceptance.<br>- The two-unit request remains present with status `planning`; no new reservation is inserted and no two-unit `reserved` commitment is saved.<br>- The maintenance record remains unchanged. |

### TC-003 — Prevent Acceptance When Overlapping Reserved Stock Is Exhausted

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Negative |
| **Test Scenario** | Verify that an existing overlapping reservation using the only unit prevents acceptance of another request, while retaining the pending request and original reservation. |
| **Pre-conditions** | - Technical Support has the access described in Test Setup.<br>- `Presentation Projector` has total quantity `1`.<br>- `Northstar Industry Forum` has a `reserved` request for one unit from `09:00` to `12:00`.<br>- Event `Harbor Research Symposium` is `planning`, with an existing `planning` request for one unit from `11:00` to `13:00` on the same date.<br>- No maintenance affects the period. |
| **Test Steps** | 1. Open the existing request for `Harbor Research Symposium`.<br>2. View its requirements and check availability for `11:00–13:00`.<br>3. Attempt to accept the request.<br>4. Reopen the pending request.<br>5. View the existing reservation for `Northstar Industry Forum`. |
| **Test Data** | `Equipment`: `Presentation Projector`<br>`Total / Reserved / Requested quantity`: `1 / 1 / 1`<br>`Date`: `20 November 2026`<br>`Existing period`: `09:00–12:00`<br>`Requested period`: `11:00–13:00` |
| **Expected Result** | - No unit is available during the overlap, so the requested full period cannot be fulfilled.<br>- Final acceptance is prevented and a clear equipment unavailability message is displayed.<br>- The existing `Harbor Research Symposium` request remains `planning`; no additional `reserved` commitment is saved.<br>- The `Northstar Industry Forum` reservation retains its status, quantity, and period. |

### TC-004 — Prioritise the Earliest Request During Concurrent Acceptance

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Negative |
| **Test Scenario** | Verify that pending requests can coexist before review, but competing concurrent acceptance attempts for the only unit commit only the earlier Coordinator request. |
| **Pre-conditions** | - Two Technical Support members are authenticated in separate sessions with the access described in Test Setup.<br>- `Northstar Industry Forum` and `Harbor Research Symposium` are `planning` events.<br>- Each has an existing `planning` request for one `Presentation Projector` for the same period.<br>- Northstar's `requested_at` is earlier than Harbor's.<br>- Total stock is `1`; no reservation or maintenance consumes it.<br>- Both requests already exist before Technical Support review; no database concurrency guarantee is assumed by this fixture. |
| **Test Steps** | 1. In session A, open Northstar's request and check availability.<br>2. In session B, open Harbor's request and check availability before either request is accepted.<br>3. Review both requests without accepting them and reopen their status details.<br>4. Coordinate both staff members to attempt acceptance simultaneously.<br>5. View both outcomes and reopen both requests.<br>6. Repeat from a fresh setup with the same request ordering, but have session B attempt acceptance before session A; then have session A accept its earlier request. |
| **Test Data** | `Session A event`: `Northstar Industry Forum`<br>`Session A requested_at`: `2026-11-19T08:00:00+08:00`<br>`Session B event`: `Harbor Research Symposium`<br>`Session B requested_at`: `2026-11-19T08:01:00+08:00`<br>`Equipment`: `Presentation Projector`<br>`Total quantity`: `1`<br>`Quantity per request`: `1`<br>`Date`: `20 November 2026`<br>`Period`: `09:00–12:00` |
| **Expected Result** | - Both pending requests remain `planning` before acceptance; reviewing them alone does not consume stock.<br>- Physical stock before either acceptance is one unit; it is not a guarantee that both requests may be accepted.<br>- Only Northstar's earlier request changes to `reserved`; its session receives confirmation with the event, equipment, date, and time.<br>- Harbor's request is not accepted and the reviewer receives a clear stock-conflict or earlier-request-priority explanation.<br>- After the attempts, reopening both requests shows exactly one reserved unit for the period, with Harbor's request retained as `planning`.<br>- The later-first variant also preserves earliest-request priority; the order of Technical Support clicks does not give Harbor the unit.<br>- Neither event is automatically confirmed. |

### TC-005 — Share Remaining Stock Across Overlapping Events

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-005 |
| **Category** | Boundary |
| **Test Scenario** | Verify that overlapping events can share remaining units up to the stock limit, and that separate commitments affecting different parts of a period are not added as if concurrent. |
| **Pre-conditions** | - Technical Support has the access described in Test Setup.<br>- All target events are `planning`, with existing `planning` requests; no earlier competing pending requests affect them.<br>- Setup A: `Wireless Microphone` has total quantity `3`; Northstar has two units `reserved` for `09:00–12:00`; Leadership has a pending one-unit request for `11:00–13:00`.<br>- Setup A also contains Panel's later pending one-unit request for `11:30–12:30`.<br>- Independent setup B: the same equipment has total quantity `3`; Northstar reserves two units for `09:00–10:00`, Harbor reserves two units for `11:00–12:00`, and Leadership requests one unit for `09:00–12:00`.<br>- No maintenance affects either setup. |
| **Test Steps** | 1. In setup A, open Leadership's request and check availability.<br>2. Accept it and view confirmation.<br>3. Open Panel's request, check availability, and attempt acceptance.<br>4. Reopen all affected requests.<br>5. In independent setup B, open Leadership's request, check availability for its full period, and accept it.<br>6. View confirmation and reopen the request. |
| **Test Data** | `Equipment`: `Wireless Microphone`<br>`Total quantity`: `3`<br>`Date`: `20 November 2026`<br>`Setup A existing quantity`: `2`, period `09:00–12:00`<br>`Setup A Leadership quantity`: `1`, period `11:00–13:00`<br>`Setup A Panel quantity`: `1`, period `11:30–12:30`<br>`Setup B existing periods`: `09:00–10:00` and `11:00–12:00`, two units each<br>`Setup B requested quantity`: `1`, period `09:00–12:00` |
| **Expected Result** | - Setup A initially shows one unit available throughout Leadership's requested period.<br>- Leadership's existing request becomes `reserved`, with confirmation; the overlapping total reaches three units without exceeding stock.<br>- Panel has no unit available during part of its requested period, so acceptance is prevented with a clear unavailability message and its request remains `planning`.<br>- Existing reserved requests remain unchanged.<br>- Setup B shows at least one unit available throughout Leadership's period and accepts its request as `reserved`.<br>- Setup B's separate two-unit reservations are not counted as four concurrent units; no point exceeds the total stock of three. |

### TC-006 — Allow Adjacent Periods Without Reservation Status Cleanup

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-006 |
| **Category** | Boundary |
| **Test Scenario** | Verify that the same stock can be accepted for a period starting exactly when a previous reservation ends, without requiring the previous row's stored status to be cleared. |
| **Pre-conditions** | - Technical Support has the access described in Test Setup.<br>- `Presentation Projector` has total quantity `1`.<br>- Northstar's event and reservation period end at `12:00`; its one-unit reservation for `09:00–12:00` still has stored status `reserved`.<br>- Harbor is a `planning` event with an existing `planning` one-unit request for `12:00–14:00`.<br>- There is no maintenance or other competing request/reservation.<br>- Independent runs use review times before and after Northstar's event ends. |
| **Test Steps** | 1. Before the first event ends, open Harbor's request and check availability for `12:00–14:00`.<br>2. Accept the request and view confirmation.<br>3. Reopen both requests.<br>4. Repeat from a fresh setup at `12:00`, with Northstar's stored reservation still `reserved`, and accept Harbor's request again. |
| **Test Data** | `Equipment`: `Presentation Projector`<br>`Total quantity`: `1`<br>`Date`: `20 November 2026`<br>`Existing reservation`: `09:00–12:00`, quantity `1`, status `reserved`<br>`Requested period`: `12:00–14:00`, quantity `1`<br>`Review time variants`: `08:00`, `12:00` |
| **Expected Result** | - One unit is available for `12:00–14:00` in both independent runs because the earlier reservation ends exactly at the requested start.<br>- Harbor's existing request becomes `reserved` and confirmation shows its event, equipment, date, and period.<br>- Availability does not depend on a job clearing Northstar's historical status or writing `available`.<br>- Northstar's existing record is preserved, and the same unit is not committed to overlapping periods. |

## Open Questions

- If automatic removal of stored `reserved` after equipment return is still required, which existing status and workflow implements it? TC-006 verifies period-based stock release, not an unspecified cleanup action.

## Execution Dependencies

- Technical Support now uses the existing role-verified Supabase application login. Verify it with real test-account/RLS data before live acceptance testing.
- Verify the reported live RLS changes against Technical Support event SELECT and request SELECT/UPDATE access, including visibility of other events' committed stock. INSERT permission is not needed to accept an existing request.
- Acceptance uses the team-approved `public.accept_equipment_request(p_reservation_id)` in [the supplied SQL](../database/equipment-acceptance-draft.sql), and confirmation uses its returned reservation. Verify deployment of the RPC, stock helper, and guards plus live RLS/isolation behavior before claiming TC-004 passed. No direct-update fallback is allowed.
- Preserve `planning` as the user-confirmed pending equipment request status and `reserved` as accepted; do not copy `requested`, `confirmed`, `approved`, or venue-block statuses from other stories into this workflow without agreement.
- TC-001–TC-006 are not recorded as executed live. Local simulated service/route tests and JavaScript UI tests are recorded separately below.

## Additional Approved-SQL Verification Cases

| Scenario | Expected Result | Verification Scope |
|---|---|---|
| TC-002 maintenance fixture has status `cancelled` | Its quantity is not deducted; stock is available subject to reservations and other active records. | Required live stock-helper check. |
| Unavailability status is NULL | Availability and acceptance report ambiguous data; do not report available stock or set the request to `reserved`. | Local error propagation tested; SQL behavior needs live verification. |
| Equal/missing competing request timestamps require a priority decision | Explain that priority needs clarification; do not guess an order or accept the affected request. | Local error propagation tested; SQL behavior needs live verification. |
| Earlier pending request is infeasible while a later smaller request fits | The infeasible request receives no provisional allocation; the later request may be accepted if otherwise valid. | Required live approved-RPC check. |
| Retry acceptance after an earlier successful save | The RPC returns the existing `reserved` row; no duplicate row or second allocation is created. | Local idempotent-RPC delegation tested; live retry required. |
| Approved RPC is not deployed | Report that acceptance is not configured; never issue an ordinary table update as a fallback. | Automated service test. |

## Local Automated Verification

- Equipment service/route tests: 24 passed. Equipment plus existing authentication selection: 40 passed.
- JavaScript UI tests: 3 passed. These verify escaped display content, Singapore-time formatting, review/acceptance calls, confirmation from returned data, insufficient-stock disabling, and failed acceptance remaining pending.
- Full pytest suite: 146 passed, 133 pre-existing failures after correcting the Flask startup import. Existing unrelated route-registration failures remain outside this story.
- Simulated RPC responses are not proof that AC6 or TC-004 succeeds against the deployed database. No live functional execution or SQL application was performed.

## Supabase Deployment Recheck — 15 October 2026

The user reports that the approved SQL is deployed. A live unauthenticated acceptance call with a nonexistent request ID reached Supabase and returned the expected Technical Support authentication error (`42501`), without changing a reservation. Focused Python tests again passed (40), and JavaScript UI tests again passed (3). TC-001–TC-006 have not been executed against authenticated live data; a Technical Support session is required for that verification.
