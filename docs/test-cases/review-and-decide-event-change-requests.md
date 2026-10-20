# Test Cases — Review and Decide Event Change Requests

**Review state:** APPROVED — Human Gate 2, 2026-10-20. Implementation-readiness and any required shared-change approval remain pending.  
**Human Gate 1:** Approved by the assigned developer on 2026-10-20.  
**Approved working interpretation:** Option B — successful approval immediately applies requested event changes; it does not bypass Venue Staff or Technical Support authority.

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | AC1, AC2, AC3, AC4, AC5 — Compare Proposed Changes and Display Venue and Equipment Issues |
| TC-002 | Boundary | AC3, AC5 — Exclude Own Booking Without Hiding Real Venue Conflicts |
| TC-003 | Boundary | AC4, AC5 — Identify Time-Specific Equipment Shortage |
| TC-004 | Happy Path | AC6, AC7, AC9, AC10, AC11 — Approve and Immediately Apply a Conflict-Free Change |
| TC-005 | Negative | AC2, AC3, AC4, AC5, AC7, AC11 — Prevent Approval When Fresh Revalidation Detects a New Issue |
| TC-006 | Negative | AC6, AC8, AC9, AC10, AC11 — Reject Requires Reason and Does Not Apply Changes |
| TC-007 | Negative | AC6, AC8, AC9, AC10, AC11 — Request More Information Requires an Explanation |
| TC-008 | Negative | AC6, AC9, AC11 — Deny Decisions by a Coordinator Not Assigned to the Event |
| TC-009 | Negative | AC7, AC9, AC10, AC11 — Report Partial-Application and Notification Failures Accurately |

## Functional Test Cases

### TC-001 — Compare Proposed Changes and Display Venue and Equipment Issues

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Coordinator compares current and proposed details and sees distinct, actionable capacity, booking, maintenance and equipment issues. |
| **Pre-conditions** | - Coordinator COORD-201 is authenticated and assigned to event EVT-201.<br>- Event EVT-201 and pending change request CR-201 exist.<br>- Venue VEN-101 uses the proposed theatre layout with permitted capacity 180.<br>- For the proposed period, another event has an overlapping active VEN-101 booking; VEN-101 also has an overlapping active maintenance block.<br>- The proposed equipment quantity cannot be met during part of the period. |
| **Test Steps** | 1. Open change request CR-201 as the assigned Coordinator.<br>2. Compare current and proposed date/time, attendance, venue/layout and equipment requirements.<br>3. Read the organiser's stated reason.<br>4. Examine each flagged validation issue and its affected arrangement. |
| **Test Data** | Event: EVT-201<br>Change request: CR-201; status pending<br>Current: 20 Nov 2026, 10:00–14:00 SGT; 120 guests<br>Proposed: 20 Nov 2026, 11:00–15:00 SGT; 210 guests; VEN-101 theatre layout<br>Venue permitted capacity: 180 guests<br>Competing VEN-101 booking: 12:00–13:00 SGT<br>VEN-101 maintenance block: 13:00–13:30 SGT<br>Requested equipment: 3 wireless microphones; available quantity: 2 during 11:30–12:00 SGT<br>Organiser reason: Additional invited speakers and guests |
| **Expected Result** | - Current and proposed details appear side by side, with changed fields highlighted and the organiser's reason shown.<br>- The capacity issue identifies VEN-101, the theatre layout, proposed 210 guests and capacity 180.<br>- Booking and maintenance issues identify VEN-101 and the overlapping periods as separate conflicts.<br>- The equipment issue identifies wireless microphones, the requested/available quantities and the affected period.<br>- The UI does not report the proposed arrangement as conflict-free. |

### TC-002 — Exclude Own Booking Without Hiding Real Venue Conflicts

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Boundary |
| **Test Scenario** | A request is not flagged against its own booking, while other genuine overlaps are detected and adjacent slots are not treated as overlapping. |
| **Pre-conditions** | - Coordinator COORD-202 is assigned to event EVT-202 and change request CR-202.<br>- Event EVT-202 has its own existing confirmed booking BKG-202 at venue VEN-102.<br>- The proposed event time is 10:00–12:00 SGT on 21 Nov 2026.<br>- Another event has an adjacent confirmed VEN-102 booking from 12:00–14:00 SGT; no maintenance block overlaps the proposed slot. |
| **Test Steps** | 1. Open CR-202 and inspect venue conflicts for the proposed slot.<br>2. Confirm the result excludes EVT-202's existing booking BKG-202.<br>3. Confirm the other booking beginning exactly at 12:00 does not appear as a conflicting overlap.<br>4. Change the test fixture so another event's booking runs from 11:30–12:30, then reopen the review. |
| **Test Data** | Own booking: BKG-202; 10:00–12:00 SGT<br>Other adjacent booking: BKG-203; 12:00–14:00 SGT<br>Overlapping variant: BKG-203; 11:30–12:30 SGT |
| **Expected Result** | - The event's own existing booking is never incorrectly counted as a conflicting external booking.<br>- A separate booking starting exactly when the proposed slot ends is not flagged as overlapping.<br>- When BKG-203 actually overlaps, the issue is displayed with the affected booking/venue and overlap period. |

### TC-003 — Identify Time-Specific Equipment Shortage

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Boundary |
| **Test Scenario** | Availability assessment catches a partial-interval equipment shortage instead of checking just the total or start-of-event quantity. |
| **Pre-conditions** | - Coordinator COORD-203 is assigned to event EVT-203 and pending CR-203.<br>- Equipment EQ-301 (wireless microphones) has total quantity 5.<br>- Other committed reservations and an unavailability period affect EQ-301 during the proposed event. |
| **Test Steps** | 1. Open CR-203 for an event proposed from 10:00–13:00 SGT.<br>2. Review the equipment availability assessment and issues.<br>3. Examine the requested quantity and overlap times shown for EQ-301. |
| **Test Data** | Proposed period: 22 Nov 2026, 10:00–13:00 SGT<br>Requested EQ-301 quantity: 3<br>Total EQ-301 quantity: 5<br>Other committed reservations: 2 units from 11:00–12:00 SGT<br>Equipment unavailability: 1 unit from 11:30–12:00 SGT |
| **Expected Result** | - A shortage of 1 wireless microphone is identified from 11:30–12:00 SGT, when only 2 of the requested 3 are available.<br>- The issue identifies EQ-301 and the affected quantity/time period.<br>- The request is not marked as equipment-available merely because 3 units were available at its start. |

### TC-004 — Approve and Immediately Apply a Conflict-Free Change

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Happy Path |
| **Test Scenario** | Successful approval revalidates current availability, immediately applies approved event fields, records the decision and notifies the organiser. |
| **Pre-conditions** | - Coordinator COORD-204 is authenticated and assigned to event EVT-204.<br>- Pending request CR-204 was submitted by organiser ORG-204.<br>- Venue layout capacity, applicable bookings/blocks, and equipment quantities are sufficient at the time of final decision.<br>- The proposed field changes are unambiguous and valid under the approved shared payload contract. |
| **Test Steps** | 1. Open CR-204 and review its proposed changes and organiser reason.<br>2. Select Approve.<br>3. Submit the decision and inspect the returned outcome.<br>4. Reopen EVT-204 and CR-204.<br>5. As ORG-204, inspect the notification of the decision. |
| **Test Data** | Event: EVT-204; request: CR-204; initial request status: pending<br>Current attendance: 120; proposed attendance: 140<br>Current time: 23 Nov 2026, 10:00–12:00 SGT; proposed time: 11:00–13:00 SGT<br>Unchanged event name: Analytics Forum<br>Coordinator: COORD-204; organiser: ORG-204 |
| **Expected Result** | - The system performs a fresh capacity/venue/equipment check before final approval, not solely a previously cached check.<br>- The event's saved attendance and time reflect 140 guests and 11:00–13:00 SGT immediately after successful approval; its unchanged name stays Analytics Forum.<br>- The request displays Approved and has a corresponding persisted decision state under the approved status contract.<br>- The decision records COORD-204 and the decision date/time, with a consistent applied-change outcome.<br>- ORG-204 receives an approval notification.<br>- The approval does not itself mark a venue booking confirmed or equipment reservation accepted without their authorised workflows. |

### TC-005 — Prevent Approval When Fresh Revalidation Detects a New Issue

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-005 |
| **Category** | Negative |
| **Test Scenario** | A previously acceptable change becomes conflicting just before approval; the new conflict blocks approval without applying changes. |
| **Pre-conditions** | - Coordinator COORD-205 is assigned to event EVT-205 with pending CR-205.<br>- Initial review found the proposed arrangement available.<br>- Before the Coordinator confirms approval, another confirmed booking or equipment commitment makes part of the proposed arrangement unavailable. |
| **Test Steps** | 1. Open CR-205 and review the initial availability result.<br>2. Make a new external conflicting booking effective for the proposed venue/period before clicking Approve.<br>3. Click Approve and examine the newly detected issue.<br>4. Reopen EVT-205 and CR-205.<br>5. Repeat with an unavailable equipment quantity or failed required availability lookup as independent variants. |
| **Test Data** | Proposed time: 24 Nov 2026, 12:00–15:00 SGT<br>VEN-105 newly conflicting booking: 13:00–14:00 SGT<br>Equipment variant: request 3 units; available drops to 2 from 13:30–14:00 SGT<br>Initial request status: pending |
| **Expected Result** | - The system reruns the necessary checks when approval is attempted.<br>- The new venue or equipment conflict is displayed with its affected arrangement and overlapping period; a failed required check is not treated as availability.<br>- Approval is prevented and CR-205 retains its pre-decision status.<br>- No proposed changes are applied to EVT-205, and no successful approval is recorded or announced. |

### TC-006 — Reject Requires Reason and Does Not Apply Changes

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-006 |
| **Category** | Negative |
| **Test Scenario** | A Coordinator cannot reject without a reason; with a reason, the rejection is recorded and sent to the organiser without modifying the event. |
| **Pre-conditions** | - Coordinator COORD-206 is assigned to event EVT-206 with pending change request CR-206 from ORG-206. |
| **Test Steps** | 1. Open CR-206 and choose Reject.<br>2. Attempt to confirm with the rejection reason blank.<br>3. Enter the rejection reason and confirm.<br>4. Reopen CR-206 and EVT-206.<br>5. As organiser ORG-206, view the resulting notification. |
| **Test Data** | Change request: CR-206; status pending<br>Proposed attendance: 200; current attendance: 100<br>Initially blank reason, then: Venue capacity cannot support the new guest count. |
| **Expected Result** | - Blank rejection reason is not accepted and does not change CR-206 or EVT-206.<br>- With the reason provided, CR-206 displays Rejected, with a saved decision, COORD-206 identity, timestamp and the exact reason.<br>- EVT-206 retains its previous attendance and other existing details.<br>- ORG-206 receives a rejection notification containing the reason. |

### TC-007 — Request More Information Requires an Explanation

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-007 |
| **Category** | Negative |
| **Test Scenario** | The Coordinator must specify what information is needed; a successful information request is recorded and conveyed without applying changes. |
| **Pre-conditions** | - Coordinator COORD-207 is assigned to event EVT-207 with pending request CR-207 submitted by ORG-207. |
| **Test Steps** | 1. Open CR-207 and select Request More Information.<br>2. Try confirming without specifying the information required.<br>3. Enter a description of the missing information and confirm.<br>4. Reopen CR-207 and EVT-207.<br>5. As ORG-207, view the resulting request for information. |
| **Test Data** | Change request: CR-207; status pending<br>Required information: Please specify the wireless microphone quantity and updated session timetable. |
| **Expected Result** | - A blank information-request description prevents the decision from being recorded.<br>- After a valid description, CR-207 displays Awaiting Information, with an approved persisted status mapping.<br>- The saved decision includes the Coordinator's identity, decision timestamp and requested details.<br>- The proposed event changes remain unapplied.<br>- ORG-207 receives the specific information request in a notification. |

### TC-008 — Deny Decisions by a Coordinator Not Assigned to the Event

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-008 |
| **Category** | Negative |
| **Test Scenario** | A Coordinator who is not assigned to the event cannot decide another Coordinator's change request. |
| **Pre-conditions** | - Request CR-208 belongs to EVT-208, which is assigned to COORD-208.<br>- A different authenticated Event Coordinator COORD-999 is not assigned to EVT-208. |
| **Test Steps** | 1. Authenticate as COORD-999.<br>2. Attempt to open CR-208 and submit an approval or rejection decision.<br>3. Reopen CR-208 as an authorised user and check the event and request history. |
| **Test Data** | Event: EVT-208<br>Assigned Coordinator: COORD-208<br>Unassigned Coordinator: COORD-999<br>Request status before attempt: pending |
| **Expected Result** | - COORD-999 cannot access or decide CR-208 through the assigned-Coordinator review workflow.<br>- No event changes, decision state or decision audit entries are created from the unauthorised attempt. |

### TC-009 — Report Partial-Application and Notification Failures Accurately

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-009 |
| **Category** | Negative |
| **Test Scenario** | Failures do not yield a misleading approved-and-applied result or a false notification success claim. |
| **Pre-conditions** | - Coordinator COORD-209 is assigned to EVT-209 with pending CR-209.<br>- The proposed changes satisfy all known constraints at final revalidation.<br>- Failure scenarios can be introduced for decision/event persistence and organiser notification independently. |
| **Test Steps** | 1. Open CR-209, select Approve and cause the event update or decision persistence step to fail.<br>2. Examine the response and the persisted request/event details.<br>3. Independently repeat from a clean pending request while allowing the decision and event changes to save but making the notification operation fail.<br>4. Examine the saved decision and the UI's delivery feedback. |
| **Test Data** | Event: EVT-209; request: CR-209<br>Current attendance: 100; proposed attendance: 130<br>Failure A: event change/decision persistence fails<br>Failure B: event change and decision succeed, organiser notification fails |
| **Expected Result** | - Failure A is not reported as a successful approval or a successfully applied change; the recorded request and authoritative event state must not misleadingly contradict one another.<br>- Failure B preserves the recorded decision and applied event changes, but explicitly reports that notification did not succeed.<br>- In neither variant does the UI falsely tell the Coordinator that an unsuccessful operation completed fully. |

## Acceptance Criterion Coverage

| Acceptance Criterion | Covered by |
|---|---|
| AC1 | TC-001 |
| AC2 | TC-001, TC-005 |
| AC3 | TC-001, TC-002, TC-005 |
| AC4 | TC-001, TC-003, TC-005 |
| AC5 | TC-001, TC-002, TC-003, TC-005 |
| AC6 | TC-004, TC-006, TC-007, TC-008 |
| AC7 | TC-004, TC-005, TC-009 |
| AC8 | TC-006, TC-007 |
| AC9 | TC-004, TC-006, TC-007, TC-008, TC-009 |
| AC10 | TC-004, TC-006, TC-007, TC-009 |
| AC11 | TC-004, TC-005, TC-006, TC-007, TC-008, TC-009 |

## Implementation Dependencies — Do Not Narrow Approved Expectations

- **Proposed-change contract:** The existing organiser submission uses textual date/time, venue and equipment requirement values that do not directly match authoritative event and reservation columns. An approved and unambiguous mapping is required before TC-001 through TC-005 can run against live data.
- **Status transitions:** The documented change-request statuses are pending, agreed, rejected, applied and cancelled. The approved story requires user-facing Approved and Awaiting Information; the persisted representation and organiser-response transition remain unresolved.
- **Capacity/availability sources:** Layout capacity, other active venue bookings and holds, maintenance blocks, applicable setup/turnaround buffers, multiple bookings and tentative hold expiry must follow the latest approved customer rules. Live data visibility under RLS needs verification.
- **Equipment calculation:** Time-sliced quantities and unavailable units must use the shared equipment data contract; the pending equipment feature cannot be assumed merged.
- **Apply-on-approval consistency:** Updating an event and the change-request decision must not yield a misleading partial success or act as unapproved venue/equipment authorization. The cross-service atomicity/retry design requires shared review.
- **Decision notes and notification:** Current event_change_request has processed_by and processed_at but no dedicated decision-message field. The documented notification RLS lacks an INSERT policy; a team-approved persistence and notification mechanism is required.
- **Assigned Coordinator/Lead:** Check the current Coordinator Lead assignment policy before relying on the legacy event.coordinator_id rules.

## Open Questions for Implementation Readiness

1. Which approved persisted status corresponds to Awaiting Information, and how can the organiser submit more details to resume review?
2. Does an approved change to venue/time/equipment create, replace, invalidate or flag existing dependent bookings/reservations, without bypassing their approval authorities?
3. What structured proposed-change payload and database-side consistency mechanism will be approved?
4. How will audit reasons and notification delivery be persisted under approved RLS?

These are shared implementation dependencies, not grounds to weaken the expected functional outcomes.

## Human Gate 2

Developer approved these nine functional cases in the 2026-10-20 follow-up. Human Gate 2 is cleared. Do not change runtime code, pytest tests or shared schema/RLS, or create a release PR, until implementation-readiness is complete and any required shared-change approval is obtained.
