# Review and Decide Event Change Requests

**Status:** APPROVED — Human Gate 1, 2026-10-20  
**Story owner:** Ai Wei  
**Interpretation updated:** 2026-10-20 — the developer selected Option B: approval immediately applies approved proposed changes. This is the working story interpretation, not an independently verified customer clarification.

## User Story

As an Event Coordinator, I want to review and decide change requests submitted by an Event Organiser so I can assess whether the proposed changes are acceptable given the event's venue and equipment constraints.

## Acceptance Criteria

### AC1 — Compare Current and Proposed Event Details

- The assigned Event Coordinator can view the current event details and proposed changes side by side.
- The system highlights differences and shows the Event Organiser's stated reason.

### AC2 — Detect Venue Capacity Issues

- The system identifies whether the proposed guest count exceeds the permitted capacity of the affected venue under the proposed layout.
- Capacity that cannot be verified is not silently treated as sufficient.

### AC3 — Detect Venue Booking and Maintenance Conflicts

- The system identifies overlapping active venue bookings, holds and operational-unavailability or maintenance blocks affecting the proposed event period.
- The event's own existing booking is excluded from self-conflict detection without ignoring genuine conflicts involving other arrangements.
- Checks respect the applicable approved setup, event-use and turnaround occupancy rules.

### AC4 — Detect Equipment Availability Issues

- For the proposed event period, the system identifies any required equipment that cannot be supplied in the requested quantity for any overlapping part of the period.
- The assessment considers other committed reservations and recorded equipment unavailability.

### AC5 — Show Actionable Issues

- The Coordinator can view each detected issue and identify the affected venue or equipment arrangement.
- Relevant conflicting time ranges, quantities or capacity details are displayed as appropriate so the issue can be understood and resolved.

### AC6 — Choose a Decision

- An authorised Coordinator assigned to the event can Approve, Reject or Request More Information for a change request that remains eligible for review.

### AC7 — Revalidate at Approval Time

- Immediately before approval, the system rechecks applicable venue capacity, venue/maintenance availability and equipment availability against the proposed changes.
- If any issue remains unresolved or a necessary availability check cannot be completed, approval is prevented, the request retains its existing status and the outstanding issues are displayed.
- A blocked approval must not apply any of the proposed changes to the live event.

### AC8 — Require Decision Explanations

- Reject requires a non-empty rejection reason.
- Request More Information requires a non-empty description of the information needed.
- Missing required explanations prevent the decision from being saved.

### AC9 — Record Decision and Audit Information

- Successful decisions record the outcome, Coordinator identity, decision date/time and any accompanying rejection reason or information request.
- The UI presents outcomes as **Approved**, **Rejected** and **Awaiting Information**.
- Persisted status values, transitions and storage of decision explanations must use the approved shared contract rather than invented database fields or values.

### AC10 — Notify the Event Organiser

- The organiser is notified of the recorded decision with any rejection reason or requested information.
- The system distinguishes a successfully recorded decision from an unsuccessful notification; it must not falsely claim notification delivery.

### AC11 — Apply Approved Changes Immediately (Option B)

- After successful final revalidation, selecting Approve immediately applies the approved proposed event changes to the authoritative event data as part of the approval workflow; approval is not merely a recorded agreement.
- The saved event details and the change-request decision must reflect a consistent outcome. A partial application must not be reported as a successful approval; failure handling and transactional enforcement require implementation-readiness review.
- Reject and Request More Information do not apply the proposed event changes.
- Applying event details does not by itself confer Venue Staff approval of bookings or Technical Support approval of equipment. When approved event changes affect existing venue/equipment arrangements, the required linked-arrangement behaviour must be confirmed as a shared workflow contract before implementing those dependent updates.

## Working Interpretation and Requirement Boundaries

- The developer selected **Option B** on 2026-10-20: approval should immediately apply the proposed changes. This choice is used to draft AC11; it does not establish that every dependent booking or reservation may be changed by the Coordinator.
- This story reviews *submitted event change requests*. It is separate from the initial **Review Event Request** story, which handles new event submissions.
- Approval applies only changes actually requested and approved; unspecified fields remain unchanged.
- The existing event's status is not assumed to change merely because event details change. Any safety re-review or other downstream gate introduced by newer customer requirements remains a separate shared workflow dependency.
- The terms **Approved** and **Awaiting Information** are user-facing outcomes. Their mapping to persisted change-request statuses remains subject to the approved data contract.

## Preconditions / Dependencies

- A change request exists for an event assigned to the authenticated Event Coordinator and remains eligible for decision under the approved workflow.
- The organiser's current event, proposed changes and reason are readable under RLS.
- Current venue, venue-booking, venue-block, equipment-reservation and equipment-unavailability information required for the checks is accessible.
- The current release's setup/turnaround buffers, multiple bookings and tentative-hold expiry rules must be considered when applicable.
- Revalidation and final application must protect against stale requests or concurrent changes.
- Any schema/RLS changes, new statuses, cross-service transaction mechanism or notification-writing permission require team approval before implementation.

## Cross-Story Impacts (Do Not Transfer Ownership)

- **Request Event Changes** — the organiser submission payload currently stores several proposed changes as textual values or under keys that are not direct `event` columns. A compatible, unambiguous mapping is needed.
- **Event Coordinator Review Event Request** — distinct initial-submission workflow; do not modify its statuses or behaviour.
- **Venue Search/Booking and Venue Availability** — layout capacity, active holds, bookings, operational blocks and setup/turnaround rules.
- **Multiple Venue Bookings and Tentative Hold Expiry** — availability semantics and dependent arrangement handling.
- **Equipment Reservations** — time-based quantities, committed status and unavailability.
- **Coordinator Assignment / Coordinator Lead** — authorised decision-maker and assigned-event visibility.
- **Event Readiness / Safety** — determine which material changes trigger renewed downstream checks without bypassing approval authorities.

## Open Questions for Readiness / Shared Contract

1. **Applying related arrangements:** If an approved change alters the event's venue, timing or equipment needs, must existing venue/equipment reservations be updated, cancelled, re-requested, or marked for re-review? Who authorises each subsequent booking/reservation decision?
2. **Structured proposed changes:** What approved payload maps organiser-entered dates/times, venue selections/layout and equipment IDs/quantities to the authoritative event and arrangement records without losing meaning?
3. **Decision statuses:** Which persisted statuses represent Approved-and-Applied and Awaiting Information, and what transition permits the organiser to provide requested details? The documented set is `pending`, `agreed`, `rejected`, `applied`, `cancelled`.
4. **Decision notes and notification:** Where are reasons/information requests linked to their exact change request, and how are organiser notifications sent under existing Supabase RLS?
5. **Consistency:** What approved database-side mechanism prevents a successful decision record with only partially applied event changes or stale availability results?

These are implementation dependencies. They do not weaken the approved business requirements or authorise speculative shared changes.

## Implementation Notes

- Reuse authenticated Flask route → service → Supabase patterns and the existing organiser change-request submission flow.
- Do not merge this feature with the initial event-request review service or silently alter another owner's story.
- Reuse approved venue/equipment availability helpers where they implement the current customer rules; avoid introducing contradictory checks.
- Follow the existing frontend visual system.
- Do not independently add tables, change status values, disable RLS, use a service-role bypass or implement an unapproved shared migration.
- The implementation-readiness audit and any Human Gate 3 approval follow Human Gate 2 test approval.


## Human Gate 3 Proposal — Structured Change Request Payload (NOT YET APPROVED)

**Prepared:** 2026-10-21. **State:** Shared integration proposal; not a change to the approved Acceptance Criteria and not permission to edit the organiser submission story, shared database, or runtime code.

### Problem and Minimal Change

The existing organiser form posts human-readable `date`, `time`, `venue_requirements` and `equipment_requirements`. The submission service persists them under the existing `event_change_request.proposed_changes` JSONB column. A Coordinator can display those fields but cannot safely interpret free-text time ranges, venue references, equipment identities or requested quantities when checking resource constraints.

**Propose an additive versioned JSONB contract (`schema_version: 1`) using the existing column.** No new table or column is required merely to store structured proposed changes. The final input/field mapping must be agreed with the Request Event Changes story owner before modifying that owner's form/service.

### Illustrative Stored `proposed_changes` JSONB v1

```json
{
  "schema_version": 1,
  "event_updates": {
    "start_datetime": "2026-11-20T10:00:00+08:00",
    "end_datetime": "2026-11-20T16:00:00+08:00",
    "expected_attendance": 180,
    "layout_requirements": "Theatre",
    "venue_requirements": "Lecture theatre with a stage",
    "technical_requirements": "On-site support during setup"
  },
  "programme_timings": "Opening keynote at 10:00 AM",
  "venue_arrangements": [
    {
      "venue_id": "11111111-1111-4111-8111-111111111111",
      "layout": "Theatre"
    }
  ],
  "equipment_requirements": [
    {
      "equipment_id": "22222222-2222-4222-8222-222222222222",
      "quantity_requested": 2
    }
  ]
}
```

The identifiers and time are illustrative. **An organiser is not required to select a concrete venue** when the business workflow only asks for venue requirements; `venue_arrangements` is therefore optional. When no venue arrangement is proposed, the Coordinator must assess the linked existing bookings, if any, and must not guess a venue from descriptive text. `equipment_requirements` is likewise optional when no equipment change is requested. Where resources are changed, a concrete identity and quantity must be supplied before a definitive stock decision.

### Proposed Semantics and Validation

| Field | Proposed rule |
|---|---|
| `schema_version` | Integer `1`; reject unknown versions rather than guessing |
| `event_updates` | Object containing only explicitly changed, allowlisted event columns; absent fields mean **unchanged** |
| `start_datetime`, `end_datetime` | ISO 8601 with explicit UTC offset; positive, valid interval if the schedule changes; Singapore input may be converted to `+08:00` |
| `expected_attendance` | Positive integer, not a numeric string or Boolean |
| `layout_requirements`, `venue_requirements`, `technical_requirements` | Strings; free-text narratives remain descriptive, not a resource identifier |
| `venue_arrangements` | Optional array of proposed venue selections with UUID `venue_id` and a specified layout; no implied Venue Staff approval; identify pre-existing bookings server-side, not by trusting arbitrary client booking IDs |
| `equipment_requirements` | Optional array of UUID `equipment_id` and positive-integer `quantity_requested`; reject duplicate equipment IDs; explicit empty array means request no equipment, whereas omission means no change |
| `programme_timings` | Optional readable description; no existing event column has been approved for this content, so do not claim it is applied to the event automatically |
| Server-managed values | `event_id`, `requested_by`, `status`, `created_at`, `processed_by`, `processed_at` and `reason` stay in their existing top-level request record or API contract; do not trust client-supplied decision/identity fields |

**Open shared decision:** The live `event` table has both `preferred_start_datetime`/`preferred_end_datetime` and `start_datetime`/`end_datetime`. This example uses actual event time columns; the team must confirm how planning-versus-confirmed events map schedule changes before enabling automatic approval.

### Backward Compatibility and Rollout

1. **Phase 1 — agree on the contract:** Confirm with the organiser submission owner and the team which UI fields are selected versus descriptive, and the exact schema version, optional-field semantics, and event timestamp mapping.
2. **Phase 2 — update the submission story by its owner:** Accept new typed v1 submissions, validate before saving, and keep legacy submissions working. Maintain the existing `reason` and pending status behavior. An updated input form should use time selectors and available venue/equipment catalogue IDs where those identities are required.
3. **Phase 3 — implement this Coordinator story:** Read both legacy and v1 requests. Display historical free-text data unchanged. Do **not** infer venue IDs/quantities/time intervals from old narratives; if required values are ambiguous, show a **Needs clarification** validation issue and prevent automatic approval, while leaving appropriate review actions available.
4. **Phase 4 — integration:** Wire the v1 payload into the shared venue/equipment availability interface only after its contract and the Human Gate 3 resource/RLS decisions are approved. Never bypass Venue Staff or Technical Support authorisation.
5. **Tests:** Legacy submission regression; v1 success; invalid/unzoned/reversed time values; string attendance; missing/duplicate resource IDs; unchanged-field semantics; one approved-change request maps to the expected event columns. Correct partial-application and concurrent-resource behavior require separate approved transactional design.

### Change Ownership and Risk

- **Request Event Changes owner (organiser submission):** Own the current submission UI and service changes after cross-story agreement. Do not alter their canonical story from this branch.
- **This Coordinator review story:** Own the v1/legacy display and safe interpretation of the approved shared contract, followed by the approval integration after shared gates are cleared.
- **Shared database/integration owner:** Decide on transactional approval, notification RLS, equipment-unavailability visibility and status transitions separately.
- **Compatibility impact:** Existing `proposed_changes` JSONB rows are not automatically migrated. Keep them readable and safe to review; do not discard them or silently convert ambiguous values.

**Human Gate 3 decision required:** Approve or revise this contract with the affected story owner/team before implementing or deploying shared submission-format behavior.

## Test Case Reference

`docs/test-cases/review-and-decide-event-change-requests.md` — Human Gate 2 approved; proceed to implementation-readiness audit.

## Requirement Revision

- 2026-10-20: New separately assigned Event Coordinator change-request decision story.
- 2026-10-20: Developer selected Option B; added AC11 to require immediate application on successful approval.
- 2026-10-20: Developer confirmed the complete story and acceptance criteria at Human Gate 1.
- 2026-10-20: Developer approved the nine functional scenarios in the ensuing confirmation; Human Gate 2 cleared. Awaiting implementation-readiness and any required shared-change approval.
