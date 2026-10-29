# Test Cases — Submit a Venue Booking Request

## Test Cases

Functional specification approved in the conversation on 27 October 2026
(Human Gate 2). These are acceptance targets, not execution
results. Automated tests have been reconciled to the non-blocking workflow.
Live authenticated RLS execution, assigned-staff delivery,
per-booking layouts and atomic confirmation/cancellation require integration
verification. Automated verification results are recorded separately below;
the developer supplied successful shared database verification on 28 October 2026.

The later buffer clarification retains deployed B1 occupied-period checks and
the existing 30-minute equipment transfer gap. Configure positive setup and
turnaround durations in the synthetic venue data. Venue adjacency below means
adjacent occupied periods, not merely adjacent event times; pending alternatives
remain non-blocking.

Story: [Submit a Venue Booking Request](../user-stories/submit-venue-booking.md).

### Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | AC1–AC6 — Submit a non-blocking alternative, preserve its details after reload and notify assigned Venue Staff; AC5 has an implementation dependency |
| TC-002 | Negative | AC2 — Reject submission overlapping a confirmed booking or active blackout |
| TC-003 | Negative | AC1 — Prevention of venue booking request for unapproved events |
| TC-004 | Negative | AC1 — Validation failure when required submission fields are missing |
| TC-005–TC-006 | Negative | AC1 — Authentication, role and assigned-event access |
| TC-007 | Happy Path | AC3, AC4, AC6 — Multiple alternatives with independent periods/layouts; pending alternatives do not block other events |
| TC-008–TC-009 | Boundary | AC2 — Confirmed-booking/active-block overlap and half-open boundaries |
| TC-010–TC-012 | Negative | AC1, AC2, AC5 — Invalid input, persistence failure and explicit notification failure |
| TC-013 | Cross-Cutting Quality | AC7, AC8 — Concurrent confirmation cannot reserve two alternatives or double-book a venue |
| TC-014–TC-016 | Cross-Cutting Quality | AC1, AC4–AC6 — Recipient assignment, persisted UI and actual schema/RLS |
| TC-017 | Happy Path | AC7 — Confirm one alternative and automatically cancel pending siblings only |
| TC-018 | Negative | AC2, AC7 — Recheck conflicts at confirmation; failure rolls back confirmation and sibling cancellation |
| TC-019 | Negative | AC7, AC8 — Retry successful confirmation safely; prevent a second confirmed alternative |

---

### TC-001 — Submit a Non-Blocking Alternative and Notify Venue Staff

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an Event Coordinator can submit an available venue, period and layout as a non-blocking alternative, notify assigned Venue Staff, and reload its saved details. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- Event `EVT-101` exists in `approved` status.<br>- Venue `VEN-001` (Grand Hall) has no existing bookings or blackout blocks on `2026-11-15` for time slot `09:00 - 12:00`.<br>- Venue Staff user `STF-301` is assigned to Venue `VEN-001`. |
| **Test Steps** | 1. Navigate to the Coordinator Event Workspace for event `EVT-101`.<br>2. Select the option to submit a venue booking request.<br>3. Select Venue `VEN-001`, Date `2026-11-15`, Time Slot `09:00 - 12:00`, and Setup Layout `Theatre`.<br>4. Submit the booking request.<br>5. Reload the workspace and review its saved details and status.<br>6. Check the assigned Venue Staff's notifications. |
| **Test Data** | `Event ID`: `EVT-101`<br>`Venue ID`: `VEN-001`<br>`Date`: `2026-11-15`<br>`Time Slot`: `09:00 - 12:00`<br>`Setup Layout`: `Theatre` |
| **Expected Result** | - The conflict check passes.<br>- A booking is saved as `requested`, linked to `EVT-101` and `VEN-001`, with the selected period and its own `Theatre` layout.<br>- The pending alternative does not reserve or block the venue.<br>- A notification is created for assigned Venue Staff `STF-301` via the Notification Service.<br>- After reload the saved period/layout remain visible and the booking displays `Pending Venue Approval`; this label is not a persisted status.<br>- The event remains `approved`. |

---

### TC-002 — Rejection of Submission Due to Schedule Conflict or Blackout Date

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Negative |
| **Test Scenario** | Verify that submission is blocked when the selected slot overlaps a confirmed venue booking or active venue blackout. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- Event `EVT-102` exists in `approved` status.<br>- Venue `VEN-001` has a blackout record (`venue_block`) or confirmed booking on `2026-11-15` for `14:00 - 18:00`. |
| **Test Steps** | 1. Navigate to the Coordinator Event Workspace for event `EVT-102`.<br>2. Select the option to submit a formal venue booking request.<br>3. Select Venue `VEN-001`, Date `2026-11-15`, Time Slot `14:00 - 18:00`, and Setup Layout `Theatre`.<br>4. Attempt to submit the booking request. |
| **Test Data** | `Event ID`: `EVT-102`<br>`Venue ID`: `VEN-001`<br>`Date`: `2026-11-15`<br>`Time Slot`: `14:00 - 18:00`<br>`Setup Layout`: `Theatre` |
| **Expected Result** | - The conflict check flags the collision.<br>- No booking or notification is created for the failed attempt.<br>- An explicit message explains that the venue slot is unavailable.<br>- Existing bookings remain unchanged. |

---

### TC-003 — Prevention of Venue Booking Submission for Unapproved Event

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Negative |
| **Test Scenario** | Verify that the system restricts venue booking request submissions to approved events and prevents requests for unapproved or draft events. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- Event `EVT-103` exists in `draft` status (unapproved).<br>- Venue `VEN-002` is available on `2026-11-20`. |
| **Test Steps** | 1. Navigate to the Coordinator Workspace for event `EVT-103`.<br>2. Attempt to initiate or submit a venue booking request for event `EVT-103`. |
| **Test Data** | `Event ID`: `EVT-103`<br>`Event Status`: `draft`<br>`Venue ID`: `VEN-002` |
| **Expected Result** | - The option to submit a venue booking request is disabled or blocked for `EVT-103`.<br>- The system displays an error or warning indicating that venue bookings can only be requested for approved events in approved status. |

---

### TC-004 — Validation Failure When Required Submission Fields Are Missing

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Negative |
| **Test Scenario** | Verify that attempting to submit a venue booking request with missing required selection fields fails validation and prevents record creation. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- Event `EVT-104` exists in `approved` status. |
| **Test Steps** | 1. Navigate to the Coordinator Event Workspace for event `EVT-104`.<br>2. Select the option to submit a formal venue booking request.<br>3. Select Venue `VEN-001` and Date `2026-11-15`, but leave Time Slot and Setup Layout unselected.<br>4. Attempt to submit the booking request. |
| **Test Data** | `Event ID`: `EVT-104`<br>`Venue ID`: `VEN-001`<br>`Date`: `2026-11-15`<br>`Time Slot`: `[Unselected]`<br>`Setup Layout`: `[Unselected]` |
| **Expected Result** | - Submission is rejected by input validation.<br>- Validation error messages highlight the unselected required fields.<br>- No booking or notification is created. |

## Additional Regression and Integration Cases

| ID | Scenario | Expected result | Verification |
|---|---|---|---|
| TC-005 | Missing/invalid session; caller lacks Coordinator role | 401/403; no booking or notification | Existing regression target; rerun after implementation |
| TC-006 | Missing event, event hidden by RLS or assigned to another Coordinator | 404; no writes | Automated and live RLS verification required |
| TC-007 | Multiple pending alternatives and another event requesting their slot | Independent details retained; pending alternatives do not block submission/confirmation | Local Python and SQL passed |
| TC-008 | Partial overlap, enclosing interval, enclosed interval, identical interval | Reject conflicts with confirmed bookings or active venue blocks | Local Python and SQL passed |
| TC-009 | With 15-minute setup and turnaround, an earlier event ends 12:00 and the next starts 12:29 / 12:30; requested/tentative/rejected/cancelled bookings and cancelled blocks | 12:29 conflicts; 12:30 has adjacent occupied periods and is permitted if otherwise valid. Pending/inactive records do not block. | Local Python delegation and real SQL boundary checks passed |
| TC-010 | Non-object/malformed JSON, wrong field types, blank strings, invalid calendar date, invalid/reversed/equal times | 400; no writes | Existing regression target; rerun after implementation |
| TC-011 | Database failure before booking insertion | Sanitised error; no notification | Existing regression target; rerun after implementation |
| TC-012 | Notification fails after booking saved | Return saved booking and explicit notification warning; UI must not automatically resubmit the saved booking | Existing regression target; rerun after implementation |
| TC-013 | Simultaneous confirmation for the same event or venue slot | At most one conflicting confirmation commits; losing attempt does not cancel the winner | Detailed case below; real concurrent database execution required |
| TC-014 | Two venues have different assigned staff | Notify only staff assigned to the selected venue | Blocked: no assignment relationship or notification INSERT policy exists |
| TC-015 | Coordinator submits multiple alternatives then reloads | Each saved `requested` booking displays `Pending Venue Approval` and retains its own period/layout | Local Python/UI tests passed; real-account browser execution pending |
| TC-016 | Actual Supabase schema and policies | Per-booking layout persists; JWT preserved; authoritative conflicts checked; unauthorised confirmation/cancellation denied | Supplied migration verification passed; local synthetic RLS passed; live-account execution pending |

### TC-002 execution variants

Run the conflict case independently for a confirmed booking and active blackout.
Include each overlap shape in TC-008 and adjacent boundaries in TC-009. Repeat
with pending alternatives and cancelled blocks to establish that they do not
block the slot. A failed submission leaves booking and notification counts
unchanged.

### TC-001 assertions

Verify persisted Event ID/Venue ID, period, independent layout, `requested`
status and response display status. Verify recipient assignment against real
venue relationships and the workspace through the browser. A predefined mock
booking response alone is insufficient.

### TC-007 — Keep Multiple Alternatives Without Blocking Their Slots

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-007 |
| **Category** | Happy Path |
| **Test Scenario** | Submit alternatives with different periods/layouts and verify their non-blocking behavior. |
| **Pre-conditions** | A Coordinator is assigned approved events `EVT-101` and `EVT-102`. Grand Hall supports Theatre; Seminar Room supports Classroom. Both periods below have no confirmed booking or active blackout. |
| **Test Steps** | 1. Submit alternative A for `EVT-101`.<br>2. Submit alternative B for the same event.<br>3. Reload both alternatives.<br>4. Submit a request for `EVT-102` at A's venue and overlapping period.<br>5. As Venue Staff, confirm the `EVT-102` request.<br>6. Repeat the pending-alternative variant with A recorded as `tentative`. |
| **Test Data** | A: Grand Hall, `15 November 2026 09:00–12:00`, Theatre.<br>B: Seminar Room, `16 November 2026 13:00–16:00`, Classroom.<br>Other event: Grand Hall, `15 November 2026 10:00–11:00`. |
| **Expected Result** | Both alternatives save as `requested` and retain their own dates, periods and layouts after reload. Neither overwrites the other. Pending alternatives do not block the other event's submission or Venue Staff confirmation. The same holds for an existing `tentative` alternative. Confirming the other event does not cancel `EVT-101`'s alternatives. |

### TC-013 — Prevent Conflicting Concurrent Confirmations

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-013 |
| **Category** | Cross-Cutting Quality |
| **Test Scenario** | Race real database transactions confirming alternatives for one event, and requests for one venue slot. |
| **Pre-conditions** | Two authorised Venue Staff sessions are available. Each variant starts with pending bookings and no confirmed conflicts. |
| **Test Steps** | 1. Confirm A and B simultaneously using independent sessions.<br>2. Reload both bookings and their event.<br>3. Repeat with C and D.<br>4. Reload all affected bookings and any pending siblings. |
| **Test Data** | A/B: same event, different venues/periods.<br>C/D: different events, same Grand Hall slot, `15 November 2026 09:00–12:00`. |
| **Expected Result** | Exactly one competing confirmation succeeds in each variant. Same-event pending siblings become `cancelled` with the winner's confirmation. The losing operation cannot reverse the winner or leave partial sibling cancellations. For different events the losing request stays pending and its siblings remain unchanged. A clear conflict/stale-state result is returned. Mocks or serial calls alone do not establish this guarantee. |

### TC-017 — Confirm One Alternative and Cancel Pending Siblings

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-017 |
| **Category** | Happy Path |
| **Test Scenario** | Venue Staff confirms the selected alternative and automatically cancels only the same event's remaining pending alternatives. |
| **Pre-conditions** | `EVT-101` is approved with alternatives A/B/C and historical D/E. An unrelated event has pending F. A has no confirmed conflict or active blackout. |
| **Test Steps** | 1. As Venue Staff, confirm A.<br>2. Reload Venue Staff and Coordinator views.<br>3. Inspect the saved alternatives and event status. |
| **Test Data** | A: requested Grand Hall, `15 November 2026 09:00–12:00`, Theatre.<br>B: requested Seminar Room, `16 November 2026 13:00–16:00`, Classroom.<br>C: tentative Studio, `17 November 2026 10:00–11:00`, Theatre.<br>D: rejected; E: cancelled; F: requested for `EVT-102`. |
| **Expected Result** | A becomes `confirmed` and reserves its venue/period. B/C become `cancelled` automatically in the same operation. D/E/F remain unchanged. All booking records, periods and layouts are retained. Reload shows the saved results; the event remains `approved`. Cancellation follows confirmation, with no invented timed expiry. |

### TC-018 — Recheck Availability and Roll Back Failed Confirmation

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-018 |
| **Category** | Negative |
| **Test Scenario** | A conflict introduced after submission or a failure during sibling cancellation must not partially confirm an alternative. |
| **Pre-conditions** | `EVT-101` has requested A/B and tentative C. A was available at submission. A controlled isolated database supports failure injection for the rollback variant. |
| **Test Steps** | 1. Arrange a confirmed booking for another event overlapping A.<br>2. Attempt to confirm A and reload A/B/C.<br>3. Repeat independently with an active blackout instead of the confirmed booking.<br>4. With no conflict, induce a database failure during automatic cancellation and attempt confirmation again. |
| **Test Data** | A: Grand Hall, `15 November 2026 09:00–12:00`.<br>Competing confirmed booking or active block: same venue, `10:00–11:00`. |
| **Expected Result** | Each failure displays an error and leaves A/B/C in their original statuses. A is not reserved, siblings are not partially cancelled, and the event remains `approved`. Rollback is verified against the database, not only a simulated error response. |

### TC-019 — Retry Confirmation Safely and Prevent a Second Selection

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-019 |
| **Category** | Negative |
| **Test Scenario** | Retrying the selected booking is harmless; a stale attempt to confirm an alternative cannot replace it. |
| **Pre-conditions** | A/B are alternatives for approved event `EVT-101`. A is successfully confirmed and B automatically cancelled. A stale Venue Staff view still shows B as pending. |
| **Test Steps** | 1. Repeat the successful confirmation of A.<br>2. Attempt to confirm B from the stale view and directly through the same API.<br>3. Reload both bookings.<br>4. In a separate synthetic legacy fixture with confirmed A and pending B, attempt to confirm B. |
| **Test Data** | A: Grand Hall, `15 November 2026 09:00–12:00`.<br>B: Seminar Room, `16 November 2026 13:00–16:00`. |
| **Expected Result** | Repeating A returns the saved outcome without duplicating confirmation effects. B cannot become confirmed in either fixture; A is unchanged. No new booking is created, unrelated records remain unchanged and no automatic event confirmation occurs. |

## Implementation Dependencies

- AC4: approved per-booking layout storage is present in the supplied deployment verification and used by the application. Legacy unknown layouts remain explicit rather than invented.
- AC2, AC7, AC8: the approved atomic RPC, occupied-period decision and database guards are present in the supplied verification. Local concurrent SQL checks passed. Separate browser/Python mocks alone do not prove these guarantees.
- AC5: venue-to-staff assignment and notification INSERT permission remain blocked in the documented schema/RLS. Tests retain the required notification outcome; current warning responses do not satisfy AC5.
- Venue Staff approval integration requires coordination with that story's owner. This specification tests only the approved confirmation/cancellation contract and does not redefine the rest of Venue Staff review.
- Equipment validation, venue availability/search, readiness and organiser arrangement displays have cross-story dependencies recorded in the approved story. Their owners must verify compatibility; other stories' canonical tests are unchanged.

### Separate workflow regression checks

Preserve staff authentication/authorisation, supported persisted statuses and
rejection of attempts to approve rejected/cancelled rows. The old blanket rule
rejecting repeat confirmation of a confirmed row is superseded by AC8's safe
retry requirement. Required caller/test updates follow functional-test approval;
this document does not claim full acceptance of other staff workflows.

## Local Database Verification — 27 October 2026

Migration preparation follows approved Human Gate 3 and the buffer clarification.
These results record the database stage, before the later application integration.

- PostgreSQL 17 in a synthetic isolated Docker database: initial migration and
  rerun passed; no live Supabase changes were made.
- `tests/venue_booking_alternatives_fixture.sql` reuses the equipment fixtures
  and migrations, then installs the inspected B1 buffer definitions and synthetic
  role policies. Never execute this fixture in Supabase.
- `tests/test_venue_booking_alternatives.sql` passed: independent layouts,
  non-blocking alternatives, tentative sibling cancellation, unchanged unrelated
  requests, identical confirmation retry, failed conflicting confirmation,
  buffer boundary/maintenance checks, injected cancellation rollback, equipment
  acceptance with a pending venue alternative, 29/30-minute cross-venue transfer,
  B1 revision/receipt retry and no automatic event confirmation.
- Independent concurrent PostgreSQL transactions passed for same-event competing
  alternatives, different-event requests for one venue slot, and a buffer save
  racing confirmation. The losing confirmation could not commit or cancel the
  winner's arrangement. Confirmation rechecked updated buffers after waiting.
- These are local synthetic SQL results, not live-account/browser verification
  or production-load evidence. The developer later supplied deployment verification;
  application caller integration is recorded below.

Reproduce serial SQL checks in a fresh isolated PostgreSQL cluster using
`psql -U postgres -v ON_ERROR_STOP=1` with, in order, the fixture above,
`docs/database/venue-booking-alternatives-migration.sql` (twice to check rerun),
then `tests/test_venue_booking_alternatives.sql`. The fixture expects a fresh
cluster because it creates synthetic roles. The SQL test rolls back its data.

## Python / UI Application Verification

`tests/test_venue_booking_alternatives.py` exercises the real Flask routes using
the existing simulated Supabase fixture extended with the approved per-booking
layout column. It covers multiple non-blocking alternatives, independent layouts,
context reload, authoritative availability including 29/30-minute decisions,
cancelled blocks, atomic-RPC delegation, error handling and confirmation retry.

All pending-implementation expected-failure markers have been removed. Run
`python3 -m pytest tests/test_venue_booking_alternatives.py -v`. The existing
booking tests now expect non-blocking alternatives, per-booking layouts, confirmed
occupied-period conflicts and safe confirmation retries. Additional checks cover
unknown availability, sanitised RPC errors and trigger races, and readiness/
organiser handling of cancelled alternatives without changing event status.

Run `node --test tests/venue-booking.test.js tests/equipment-reservations.test.js`
for saved period/layout display, non-blocking calendar labels, stale-form
availability checks, confirmation reload/failure behavior and selection of the
confirmed equipment period despite pending alternatives. Python mocks and Node
UI checks do not establish SQL atomicity, buffer arithmetic or concurrency;
use the PostgreSQL integration tests for those. Notification delivery remains
blocked by AC5; successful booking responses retain the explicit warning.

## Final Local Application Results — 28 October 2026

- `python3 scripts/project_health.py`: production import, **343 Python tests**,
  documentation links, repository structure and whitespace checks passed.
- Node venue/equipment suites: **28 tests passed**.
- No expected-failure markers remain in the venue-alternatives Python file.
- Supplied live database verification matches the approved migration. Real-account
  browser execution and production-load checks were not performed by this task.

| Acceptance Criterion | Functional cases | Evidence / limitation |
|---|---|---|
| AC1 | TC-001, TC-003–TC-006, TC-010 | Flask authentication, assignment and input regressions passed; real JWT browser execution pending. |
| AC2 | TC-002, TC-008–TC-009, TC-018 | Authoritative-RPC delegation, sanitised failures, trigger conflicts and local SQL buffer boundaries passed. |
| AC3 | TC-007 | Multiple independent non-blocking alternatives passed in local Python/SQL. |
| AC4 | TC-001, TC-007, TC-015 | Per-booking period/layout persistence and preservation of event requirements passed locally; column verified in supplied live result. |
| AC5 | TC-001, TC-014 | Blocked: venue-staff assignment and notification write/delivery contract remain unresolved. Warning is explicit and is not counted as delivery. |
| AC6 | TC-001, TC-015 | API context and UI display/reload checks passed locally; real-account browser check pending. |
| AC7 | TC-017–TC-018 | Real local SQL atomic cancellation/rollback and Python RPC-return checks passed. |
| AC8 | TC-013, TC-019 | Local concurrent SQL, saved-row retry and prevention of conflicting confirmation passed. Production-load verification pending. |

Status gate update, 29 October 2026: booking submission now requires event
`approved`; `planning` is included among negative pre-approval cases. Existing
venue confirmation does not itself change the event to `confirmed`.
