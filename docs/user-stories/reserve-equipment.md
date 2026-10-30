# Reserve Equipment

## User Story

As Technical Support Staff, I want to review an organiser’s equipment requirements,
propose the quantity I can provide, and reserve the agreed equipment so that the
event has a feasible technical arrangement.

## Workflow and Ownership

Keep the workflow on `main`: organiser submits → Coordinator gives initial
approval (`planning`) → Coordinator requests a venue and Venue Staff approves
it; Technical Support arranges equipment → Coordinator checks readiness and
gives final confirmation (`confirmed`).

This story owns only Technical Support equipment review/proposal/reservation
and the organiser response needed for that proposal. It does not replace
Coordinator review, venue booking, Venue Staff approval or final confirmation.
Technical Support may propose equipment during planning while the venue is
being arranged; committing equipment requires the confirmed venue so transfer
checks can use the actual venue UUID and period.

After organiser agreement, Technical Support reserves the offered quantity.
Saving `equipment_reservation.status = reserved` supplies the existing
Coordinator readiness service with the equipment outcome. No event status
change, duplicate approval queue or new notification workflow is required.
The TSS success message directs the handoff to the assigned Coordinator's
existing Event Readiness page. The Coordinator reloads readiness to see the
saved reservation and performs final confirmation when all arrangements pass.

## Acceptance Criteria

- **AC1 — Organiser handoff:** Coordinator-approved events with technical support enabled or
  nonblank technical requirements appear in the Technical Support inbox even
  before an equipment reservation exists. Cards open the saved event details.
  Events in `draft`, `requested` or `changes_requested` are excluded. Coordinator
  approval moves the event into `planning`; `confirmed` events remain eligible.
- **AC2 — Suggested quantity:** Staff select catalogue equipment and enter a
  positive whole suggested quantity and a valid period. Preserve the organiser’s
  original requirements and any existing structured requested quantity. Do not
  infer a quantity from free text. Saving a proposal does not commit stock.
- **AC3 — Organiser agreement:** The event’s organiser reviews the offered item,
  quantity and period and agrees to that version. If five were requested and
  three offered, retain five and propose three. Staff cannot finalise before
  agreement. A changed item, quantity, period or requirements snapshot invalidates
  previous consent. Other organisers cannot view or agree to the offer.
- **AC4 — Availability:** Final acceptance checks the venue and equipment for
  the selected period, all reserved quantities, active maintenance and earlier
  feasible agreed requests. Unagreed offers do not consume provisional stock.
  Missing or ambiguous data fails validation. Displayed availability uses the
  same venue/transfer allocation rules; it is not a stock guarantee.
- **AC5 — Transfer:** Compare `venue_booking.venue_id`, not building/name text.
  Reusing units at the same venue allows a 12:00 finish / 12:00 start. At another
  venue, 12:29 is rejected and 12:30 is permitted when the earlier finish is
  12:00. Check chronological order regardless of acceptance order. Independent
  spare units may serve the second venue, subject to maintenance and stock.
- **AC6 — Atomic acceptance:** Technical Support accepts through the existing
  `accept_equipment_request` RPC. Recheck current consent and availability under
  the shared write lock, commit only `quantity_suggested`, and change `requested`
  to `reserved`. Failure leaves no partial commitment. Repeating a successful
  acceptance returns the saved row without allocating twice.
- **AC7 — Permissions and errors:** Use existing Supabase authentication and RLS.
  Report failed checks in the UI and prevent stale account responses, stale
  agreement and direct edits from bypassing validation. Do not substitute demo
  data or silently reduce an agreed quantity.
- **AC8 — Arrangement changes:** Venue/time/block/catalogue changes must not
  silently invalidate committed equipment. An accepted arrangement must be
  released/reviewed before an incompatible change. This does not automatically
  confirm the event or implement physical equipment return.

## Relevant Customer Clarifications

Confirmed in this conversation on 22 October 2026: the organiser creates the
source request; Technical Support supplies a suggested quantity; a smaller offer
waits for organiser agreement; same location means the same venue; different
venues require a 30-minute transfer gap. These supersede the earlier assumption
that every inbox card requires a Coordinator-created equipment row.

The existing Coordinator event-review and Venue Staff approval responsibilities
remain. This implementation requires exactly one active venue booking, confirmed
for the proposal’s exact period, before final equipment reservation. Equipment
requirements become visible after Coordinator approval; final reservation also
waits for Venue Staff approval.

Periods use half-open overlap (`start < other_end AND end > other_start`). Display
Singapore time; compare timestamp instants. Active maintenance consumes units;
cancelled maintenance is ignored. Equal/missing competing request timestamps
require a priority decision rather than a guessed order. Availability is
calculated; no equipment `available` status is introduced.

## Preconditions / Dependencies

The caller has the appropriate Supabase role. Catalogue and authenticated
policies must be deployed. The local proposal feature additionally requires the
[full migration](../database/equipment-proposals-migration.sql). For inbox
visibility alone, the [SELECT policy patch](../database/equipment-organiser-inbox-access.sql)
is sufficient alongside the updated app. These artifacts have not been applied
to live Supabase by this implementation.

Legacy reserved rows continue using their original quantity without fabricated
organiser agreement. Existing pending rows require an explicit proposal and
agreement before acceptance. The migration aborts on infeasible legacy schedules.

## Implementation and Scope

Routes → Equipment service → authenticated Supabase RPCs. The isolated equipment
script extends the existing Technical Support dashboard, assignments and equipment
pages and provides an organiser Equipment proposals page. No new auth method,
reservation status, automatic event confirmation or persistent notifications are
introduced. Issues/Notifications remain separate stories.

The SQL checker searches allocations of anonymous stock units and fails closed
when its search budget is exhausted. Large schedules require manual allocation
review; this is not an equipment serial-number tracking system.

## Test Case Reference

[Functional test specification](../test-cases/reserve-equipment.md), TC-001–TC-012.

## Relevant UML Reference

No equipment-specific UML currently exists. The existing
[authentication sequence](../uml/event-organiser-login.puml) describes the shared
session pattern. The workflow here is: organiser submission → Coordinator approval → staff proposal →
organiser agreement → staff availability check and final acceptance.

## Remaining Questions / Cross-Story Work

Physical return/status cleanup is not defined by the current requirement; past
reservation periods cease consuming current stock without a status rewrite.
Coordinator readiness and event confirmation remain owned by their stories.
Live Supabase deployment, real-account RLS verification and concurrent production
load verification remain deployment checks.
