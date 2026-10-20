# Test Cases — Configure Venue Setup and Turnaround Time

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
| --- | --- | --- |
| TC-001 | Happy Path | AC1, AC2, AC3: independent venue configuration/readback, full event/active-hold occupancy, independent duration changes |
| TC-002 | Boundary / Conflict | AC2, AC3: setup-only and turnaround-only conflicts recognised consistently by search, booking requests and new holds |
| TC-003 | Cross-Cutting Quality / Conflict | AC4, AC5, AC6, AC7, AC8: save changed buffers despite confirmed-booking conflict; Staff feedback, calendar flags, Coordinator notices and arrangement preservation |
| TC-004 | Negative / Authorisation | AC1, AC8: Coordinator viewing/assessment authority does not grant configuration editing |

Requirement baseline: approved canonical story
`docs/user-stories/configure-venue-setup-and-turnaround-time.md`.
Human Gate 1 is explicitly approved. This specification is PROPOSED for Human
Gate 2; no scenarios or implementation tests have been executed.

Times are Singapore local time. Identities are fictional; use authenticated
accounts with the stated roles and event relationships. All venues have explicit
configuration, all relevant events have assigned Coordinators, and all durations
are concrete test data, not defaults, minimums, maximums or precision rules.
No maintenance blocks are present. All overlaps have positive duration; no
exact-touch boundary rule is assumed. Any hold used is active and unexpired,
and no buffer change affects a pre-existing hold/request in these scenarios.

### TC-001 — Configure Independent Venues and Consume Full Occupancy

| **Item** | **Content** |
| --- | --- |
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **AC Traceability** | AC1, AC2; AC3 for positive calendar/hold occupancy consumption |
| **Test Scenario** | Verify saved per-venue values, independent setup/turnaround changes and the resulting full occupied periods. |
| **Pre-conditions** | - Authorised Venue Staff are authenticated; the Coordinator is authorised to view relevant availability.<br>- VENUE-A and VENUE-B each have explicit setup 15 minutes and turnaround 15 minutes; these are fixture values, not defaults.<br>- On 10 March 2027, VENUE-A has a confirmed event 10:00–12:00 and an active unexpired hold 14:00–15:00; VENUE-B has a confirmed event 10:00–12:00.<br>- There are no other restrictions or arrangements, and all configuration values used here keep these arrangements separated.<br>- B1 consumer calendar and hold-validity support are available (ID1/ID2). |
| **Test Data** | Initial configuration: A = 15/15 minutes; B = 15/15 minutes.<br>First saved configuration: A = setup 30 / turnaround 45; B = setup 45 / turnaround 30.<br>A event occupancy = 09:30–12:45; A hold occupancy = 13:30–15:45; B event occupancy = 09:15–12:30.<br>Later independent edits on A: setup 45 with turnaround still 45, then turnaround 30 with setup still 45. |
| **Test Steps** | 1. As Venue Staff, set/save A to 30/45 and B to 45/30 minutes.<br>2. Leave and reopen each venue's operating information.<br>3. View the event and hold occupied periods in the authorised availability view, including as the relevant Coordinator.<br>4. Change only A's setup to 45, save and reopen its configuration/availability.<br>5. Change only A's turnaround to 30, save and reopen its configuration/availability.<br>6. Reopen B and view its configuration/availability again. |
| **Expected Result** | - The first saved values remain A = 30/45 and B = 45/30 after reopening; one venue does not overwrite the other.<br>- A's event occupies 09:30–12:45 and its active hold occupies 13:30–15:45; B's event occupies 09:15–12:30, not merely the advertised times.<br>- Changing A's setup alone retains turnaround 45 and yields event occupancy 09:15–12:45.<br>- Changing A's turnaround alone retains setup 45 and yields event occupancy 09:15–12:30; B remains 45/30 with its original arrangement.<br>- The values are visibly distinct setup and turnaround information, not a layout selection or an inferred default. |
| **Requirement / Risk Covered** | Per-venue or per-field cross-contamination; unsaved configuration; reversed before/after arithmetic; treating active hold occupancy differently from event occupancy. |

### TC-002 — Recognise Setup-Only and Turnaround-Only Conflicts Across Consumers

| **Item** | **Content** |
| --- | --- |
| **Test Case ID** | TC-002 |
| **Category** | Boundary / Conflict |
| **AC Traceability** | AC2, AC3 |
| **Test Scenario** | Verify conflicts outside advertised event times are recognised using one occupied-period interpretation in availability, search, booking requests and tentative-hold placement. |
| **Pre-conditions** | - VENUE-A has explicitly configured setup 30 minutes and turnaround 45 minutes.<br>- A confirmed reference booking exists on each isolated date for 10:00–12:00, occupying 09:30–12:45.<br>- The Coordinator is authorised for the relevant candidate events; venue suitability requirements are otherwise satisfied.<br>- Booking-request and tentative-hold workflows are available (ID1/ID2). Each request/hold attempt uses an isolated equivalent fixture, so one attempt cannot affect another.<br>- No candidate hold/request exists before the test; no configuration changes or blocks occur during it. |
| **Test Data** | Variant S, 11 March 2027: candidate event/hold 09:00–09:15, occupied 08:30–10:00. Occupancy overlap with reference = 09:30–10:00, wholly within the reference booking's setup.<br>Variant T, 12 March 2027: candidate event/hold 13:00–13:30, occupied 12:30–14:15. Overlap = 12:30–12:45, wholly within the reference booking's turnaround.<br>In both variants advertised candidate times do not overlap the reference event's advertised times. |
| **Test Steps** | 1. For each variant, view the reference booking's occupied period in availability.<br>2. Search for VENUE-A using the candidate's scheduled times and otherwise suitable event requirements.<br>3. Through the supported booking-request workflow, attempt the candidate period. If selection is already prevented, confirm the conflicting request cannot be completed.<br>4. In an equivalent isolated state, attempt to place the candidate as a new tentative hold through its supported workflow.<br>5. Reopen relevant availability and request/hold views. |
| **Expected Result** | - Availability reflects the reference 09:30–12:45 occupancy.<br>- Neither variant is offered as available for the candidate use simply because advertised event times are separated.<br>- The booking-request and new-hold workflows recognise each buffered conflict and do not complete a conflicting arrangement; the user can identify the unavailable period/conflict.<br>- The reference booking remains associated with its original event.<br>- No exact HTTP path, status code, payload, database row shape or message wording is prescribed. |
| **Requirement / Risk Covered** | Raw-time-only search or submission checks; ignoring setup-only or turnaround-only conflicts; disagreement between search, requests and hold placement. This is an occupancy boundary test, not an exact-touch rule or numeric limit test. |

### TC-003 — Save a Buffer Change With Confirmed Conflicts and Preserve Assessment

| **Item** | **Content** |
| --- | --- |
| **Test Case ID** | TC-003 |
| **Category** | Cross-Cutting Quality / Conflict |
| **AC Traceability** | AC4, AC5, AC6, AC7, AC8 |
| **Test Scenario** | Verify the complete changed-buffer impact workflow without automatic booking/event disposition. |
| **Pre-conditions** | - Authorised Venue Staff and two affected assigned Coordinators have supported access.<br>- VENUE-A explicitly has setup 15 minutes and turnaround 15 minutes.<br>- On 15 March 2027, BK-A belongs to Confirmed event EVT-A assigned to Coordinator Alpha; BK-B belongs to Confirmed event EVT-B assigned to Coordinator Beta.<br>- BK-A is scheduled 10:00–12:00 and BK-B 13:00–14:00. Original identities, venues, timings and event details are available for comparison.<br>- No other action changes event/booking status, and no hold, pending request or maintenance block is involved.<br>- Notification and calendar integrations are available (ID1/ID3). |
| **Test Data** | Before: BK-A occupies 09:45–12:15; BK-B occupies 12:45–14:15, safely separated.<br>Change VENUE-A to setup 30 / turnaround 45 minutes.<br>After: BK-A occupies 09:30–12:45; BK-B occupies 12:30–14:45.<br>Resulting overlap: 12:30–12:45.<br>Recipients: coordinator.alpha@example.test for EVT-A and coordinator.beta@example.test for EVT-B. |
| **Test Steps** | 1. As Venue Staff, change/save VENUE-A's durations to 30/45.<br>2. View the save-time identified impacts and reopen the venue configuration.<br>3. View both bookings and the conflicting period on the Staff calendar.<br>4. As each relevant authorised Coordinator, view the affected arrangement/calendar and notifications.<br>5. Reopen the two events and their booking information before any Coordinator assessment decision is made. |
| **Expected Result** | - The change saves despite the resulting booking conflict; reopening shows 30/45.<br>- Staff see BK-A and BK-B identified as conflicting, with the resulting 12:30–12:45 overlap identifiable.<br>- Relevant authorised Staff/Coordinator calendar views retain both bookings and flag the overlap under the changed values.<br>- Both affected assigned Coordinators receive relevant buffer-change conflict notifications, without requiring a fixed channel, wording or numerical latency.<br>- Original booking identities, timings, venues, event associations and original event information remain available; neither booking/event is cancelled or replaced automatically.<br>- The buffer save does not automatically resolve the conflict, select/approve a replacement or transition the events out of their existing Confirmed stage. No operational block was recorded to trigger the separate Contract A transition.<br>- The arrangements remain flagged for the relevant Coordinator's assessment; saving is not contingent on obtaining a new Coordinator approval first and does not itself perform that approval. |
| **Requirement / Risk Covered** | Hard-rejecting a conflict-producing configuration save; silently grandfathering/removing confirmed bookings; missing save-time/calendar feedback or Coordinator notices; confusing a configuration edit with operational-unavailability cancellation, replacement or status effects. |

### TC-004 — Coordinator Viewing Does Not Authorise Configuration Editing

| **Item** | **Content** |
| --- | --- |
| **Test Case ID** | TC-004 |
| **Category** | Negative / Authorisation |
| **AC Traceability** | AC1, AC8 |
| **Test Scenario** | Verify that relevant Coordinator access/assessment responsibilities do not grant Venue Staff configuration-edit authority. |
| **Pre-conditions** | - coordinator.alpha@example.test is authenticated with the Coordinator role only, and has authorised availability access.<br>- VENUE-A has explicitly saved setup 30 minutes and turnaround 45 minutes.<br>- venue.staff@example.test is an authorised Venue Staff account.<br>- No other actor changes configuration during the case. |
| **Test Data** | Existing VENUE-A values = 30/45 minutes.<br>Coordinator attempted values = setup 45 / turnaround 30 minutes. Values are ordinary test inputs, not validation-boundary assertions. |
| **Test Steps** | 1. As the Coordinator, open the relevant venue availability/operating information.<br>2. Attempt to change configuration through any supported configuration action. If editing is not offered, verify that no such authorised action is available; any attempted supported submission must still be denied.<br>3. As authorised Venue Staff, reopen VENUE-A's operating information. |
| **Expected Result** | - Relevant Coordinator viewing remains available.<br>- The Coordinator is not permitted to apply the configuration change merely because they can view/assess the arrangement.<br>- Staff readback remains setup 30 / turnaround 45; the attempted change has not been saved.<br>- No exact transport error or UI-control representation is prescribed. |
| **Requirement / Risk Covered** | Confusing authorised viewing/Coordinator arrangement approval with Venue Staff configuration maintenance; an unauthorised edit being silently accepted. |

## AC → Test Traceability

| Acceptance Criterion | Functional test evidence |
| --- | --- |
| AC1 | TC-001: save/readback, independent venues/fields; TC-004: unauthorised edit denied |
| AC2 | TC-001: full arithmetic; TC-002: buffered-period conflict consequences |
| AC3 | TC-001: event/active-hold calendar occupancy; TC-002: search, request and new-hold conflict consumption |
| AC4 | TC-003: reassess existing confirmed bookings under changed values and retain original information |
| AC5 | TC-003: save despite conflict, Staff feedback, no automatic disposition |
| AC6 | TC-003: Staff/Coordinator calendar retains bookings and flags resulting overlap |
| AC7 | TC-003: notify relevant affected Coordinators |
| AC8 | TC-003: Coordinator assessment remains outstanding; no automatic replacement/approval; TC-004: no Coordinator configuration authority |

AC8's later human approval outcome is not implemented/tested as another story's
workflow here. TC-003 verifies that the save has not usurped that assessment.
No claim is made that these proposed scenarios have passed.

## Implementation Dependencies

- **ID1 — Authoritative configuration and consumer integration:** Saved
  per-venue values and common occupancy interpretation must be consumable by
  calendar, search, request/approval and hold workflows. Current inspected
  raw-time checks/configuration handling do not establish that capability.
  The required behaviour remains unchanged; persistence, interfaces and shared
  changes are assessed after Gate 2, not designed in these tests.
- **ID2 — Holds and booking workflow ownership:** Hold placement and B2's
  active/expired distinction are supplied by their owners. Cases use explicit
  active holds and new attempts; no expiry or existing-hold lifecycle rule is
  invented. Request/review owners retain their own conflict protections.
- **ID3 — Conflict visibility and notification integration:** Configuration
  change must expose affected arrangements to Staff/calendar and inform
  assigned Coordinators. These integration capabilities are required, not
  evidence that current schema/RLS already permits them. No particular
  notification mechanism or transaction design is selected.
- **ID4 — Assessment/status and replacement ownership:** C1/C2 retain later
  replacement, safety and reconfirmation decisions. B1 does not execute them.
  Contract A consumes B1 for operational blocks but its effects are not tested
  as a buffer-save outcome.
- **ID5 — Role boundaries:** Existing authentication and authorised venue access
  must enforce Staff configuration maintenance versus Coordinator viewing/
  assessment. No policy or privileged-operation design is selected here.

## Open Questions Excluded From Expected Results

1. Missing/default durations: all fixtures have explicit values; zero is not
   assumed and initial missing-value behaviour is not tested.
2. Minimum/maximum/precision: no acceptance/rejection threshold, zero rule,
   integer-only rule, rounding or fixed increment is asserted.
3. Per-booking overrides: none is supplied or tested.
4. Changed-buffer effects on existing holds/requests: TC-001's active hold
   remains safely separated throughout; TC-002 uses new attempts. No
   cancellation, suspension, invalidation or expiry change is asserted.
5. Extra maintenance-block buffers: no blocks occur in these cases; no
   block-side expansion or open-ended-block rule is assumed.
6. Exact-touch semantics: all conflicts have positive overlap and all safe
   arrangements have positive separation.
7. Missing Coordinator: all affected events have assigned Coordinators; no
   rollback, silent omission, escalation recipient or fallback notice is assumed.

These are business ambiguities, distinct from the technical integrations above.
The separately unresolved existing-hold/request lifecycle under a later
operational block is likewise not tested.

## Duplicate / Redundant Test Analysis

Four focused cases cover the approved eight ACs:

- TC-001 proves normal saved configuration, independent fields/venues and
  positive full event/hold occupancy. It does not create conflicts.
- TC-002 proves full-occupancy conflicts across consumers. Its setup-only and
  turnaround-only variants are necessary directional checks, not arbitrary
  Cartesian combinations.
- TC-003 proves the distinct changed-configuration workflow: reassess existing
  confirmed bookings, save despite conflict, expose impacts, notify and
  preserve Coordinator assessment/arrangements. Splitting each effect into a
  separate test would duplicate the same action and fixture.
- TC-004 is the distinct supported authorisation failure. No unsupported
  numeric-validation or infrastructure-failure case is added.

The integrated consumer assertions are required by AC3, not separate
architectural-layer tests. No one-functional-case-to-one-pytest mapping is
prescribed. No existing cases for this new story were found, changed, removed
or retired; TC-001–TC-004 are newly proposed stable IDs within this file.

## Human Gate 2

Proposed specification only. Await explicit functional-test approval.
Do not perform an implementation-readiness audit, design schema/RLS, implement
runtime code, write pytest, commit or push.
