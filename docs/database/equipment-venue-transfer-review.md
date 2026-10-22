# Equipment Venue-Transfer SQL Review

Prepared 22 October 2026. The inspection/design discussion below records the
earlier stock-only deployment and the subsequent proposal design. The current
implementation is [Reserve Equipment](../user-stories/reserve-equipment.md).
No live Supabase changes were applied by this implementation.

## Current Deployment Steps

For the reported missing organiser cards, run the complete
[inbox SELECT patch](equipment-organiser-inbox-access.sql) in Supabase SQL Editor,
then restart Flask, hard-refresh and select Refresh in the Technical Support
dashboard. Coordinator-approved requirements appear even before an equipment
row exists. Draft/requested/changes_requested events remain excluded. This patch grants no write access and does not
implement proposals by itself.

For the complete suggested-quantity → organiser agreement → final reservation
workflow, review and deploy the complete
[proposal migration](equipment-proposals-migration.sql) with the matching app.
It includes the inbox policy, so applying both files is unnecessary. Keep the
existing stock/acceptance functions and triggers installed as prerequisites.
Do not reapply the old status-only patch or stock-only draft afterwards: they
would overwrite the enhanced acceptance guards.

Final reservation requires a planning/confirmed event and exactly one active,
confirmed venue booking matching the equipment period. Submitted requirements
become visible after Coordinator approval; final reservation also waits for
Venue Staff approval. Proposals do not hold stock;
organiser agreement does not guarantee later availability.

The migration and RLS workflow were verified using synthetic data in isolated
PostgreSQL17, including rerun, five requested/three offered, owner consent,
stock accounting, venue-change guards and same/different-venue transfer checks.
See [test results](../test-cases/reserve-equipment.md). Live authenticated RLS and
concurrent-load verification remain necessary. The local fixture/test SQL must
never be run against Supabase.

The historical statements below describing a pending implementation are
superseded by this deployment section and the current story/test specification.

## Confirmed Requirement

- Same location means the same venue, compared using venue UUIDs.
- Reusing equipment at the same venue allows consecutive events without a gap.
- Different venues require at least 30 minutes from the earlier event's end to
  the later event's start, even when the venues are in the same building.
- The computer must validate venue and equipment availability before allowing
  the booking to be made, and revalidate before assignment/acceptance is saved.
- Existing pooled-stock, maintenance, request priority, RLS, and Technical
  Support review rules still apply. A preliminary check does not commit stock.

Canonical requirements and acceptance targets:
[story](../user-stories/reserve-equipment.md) and
[tests](../test-cases/reserve-equipment.md).

## Required Database Changes

### Observed Deployment Constraints — 22 October 2026

The user has supplied all four inspection results: constraints, equipment
function definitions, non-internal triggers, and relevant RLS policies.

- `equipment_reservations_status_check` permits `requested`, `reserved`,
  `rejected`, and `cancelled`; it does not permit `planning`. The user has now selected
  `requested` to align the feature with this existing constraint. The deployed
  functions need the status patch described below; no constraint change is needed.
- `equipment_unavailability_status_check` permits `active` and `cancelled`,
  matching the maintenance statuses used by this story.
- `venue_bookings_status_check` permits `requested`, `tentative`, `confirmed`,
  `rejected`, and `cancelled`.
- Foreign keys confirm the equipment-reservation → event and venue-booking →
  event/venue links needed for venue comparison.
- No venue-per-event uniqueness constraint appears in the supplied output.
  Do not assume this establishes the absence of a unique index or trigger;
  those mechanisms require separate inspection.

The list below remains proposed change scope, not a verified deployment plan.

### Observed Functions, Triggers, and Policies — 22 October 2026

- All five supplied equipment functions are SECURITY INVOKER. Their stock,
  maintenance, priority, and locking logic is materially consistent with the
  local acceptance draft; none resolves or compares event venues.
- Both `accept_equipment_request(uuid)` and
  `cs_equipment_acceptance_guard()` require pending equipment status `planning`.
  The supplied CHECK constraint forbids that status. Consequently a fresh
  pending request cannot follow the intended acceptance path under these
  definitions: `requested` is allowed by the table but rejected by the RPC,
  while saving `planning` is rejected by the table. Returning an already
  `reserved` row on retry does not establish that new acceptance works.
- Seven equipment-related triggers are installed and enabled for normal
  execution. The supplied trigger results contain no non-internal triggers on
  `event` or `venue_booking`, so those results show no trigger protection for
  accepted equipment when an event time or venue booking changes.
- Technical Support already has SELECT policies on venue bookings and venues
  for events linked to equipment reservations. Do not add duplicate blanket
  read policies based on the older local schema documentation.
- The event SELECT policy already calls
  `cs_technical_support_can_view_event(event_id)`. Its definition was outside
  the original equipment-function query; policy presence alone does not verify
  helper ownership, implementation, or absence of recursive RLS behavior.
- Technical Support can read all equipment reservation/unavailability rows
  under the supplied role policies, but its venue-booking access is scoped to
  supported events. That scope may suffice for comparing equipment commitments'
  venues; it does not establish visibility of unrelated bookings that could
  make a selected venue unavailable. A venue-availability check needs an
  authoritative result without silently ignoring those hidden bookings.
- Venue Staff has no equipment-reservation SELECT policy in the supplied
  results. An invoker trigger on venue writes cannot assume a Venue Staff-only
  caller can see the complete equipment pool. The shared enforcement/access
  design must address this explicitly.
- The supplied ACLs explicitly grant EXECUTE to `anon`, `authenticated`, and
  `service_role` as well as the owner. They differ from the local draft's
  intended authenticated-only RPC grants. Acceptance still checks the user's
  role internally; this ACL observation alone does not prove unauthorized
  acceptance. Review intended grants during migration rather than treating
  privileges as identical to the draft.

### Status Alignment Decision

The user selected **`requested`** as the pending equipment status on 22 October
2026. This supersedes the earlier `planning` equipment-status decision and
matches the deployed constraint. Event eligibility remains `planning` or
`confirmed`. No CHECK-constraint or existing-data migration is required.

The local service, UI, baseline SQL draft, and tests now use
`requested` → `reserved`. The inspected deployed functions still use the old
status until the [status-alignment patch](equipment-requested-status-patch.sql)
is reviewed and applied. That patch replaces only the acceptance guard/RPC;
it preserves event eligibility, stock guards, locking, privileges, and retry
behavior. It does **not** implement the venue/transfer requirement.


1. **Resolve venue context.** Follow `equipment_reservation.event_id` to the
   agreed selected `venue_booking` row, then compare `venue_id`. No new location
   column is needed solely for this join. Do not use `equipment.location`,
   which describes catalogue/storage location, or compare display names.
   Agree which booking statuses are eligible and how missing/multiple choices
   are handled; do not select an arbitrary row with `LIMIT 1`.
2. **Add a venue-aware feasibility checker.** The current
   `cs_equipment_free_quantity(equipment_id, start, end, extra)` only knows
   stock and time. A proposed new request-aware RPC can take `reservation_id`
   and derive event, venue, quantity, and timing under caller permissions.
   Submission needs the same validation for the proposed request before it is
   saved. Keep the existing helper's stock-only contract explicit; changing
   parameter types creates another PostgreSQL function, not a replacement of
   existing callers.
3. **Update acceptance and priority guards.** Integrate feasibility into
   `cs_equipment_acceptance_guard()` and the earlier feasible-request
   allocation. Keep `accept_equipment_request(uuid)` as the atomic acceptance
   entry point and preserve its retry behavior. Its existing transaction lock
   must cover the new validation and state change. Protect direct table writes
   too; browser/Python checks alone are insufficient.
4. **Protect all feasibility-changing writes.** Review
   `cs_equipment_capacity_guard()` for stock/maintenance changes, and add
   appropriate revalidation for event times and venue-booking
   insert/update/delete/status changes. Use the same transaction-lock protocol
   for affected writes so a venue change cannot race equipment acceptance.
   Scope these shared triggers with the venue/event owners. They must reject
   or explicitly resolve an invalid change, not leave an accepted allocation
   impossible after a venue change.
5. **Review RLS/grants.** Supplied live Technical Support policies expose
   equipment reservations and venue bookings for supported events. Coordinators
   can see venue bookings but only their own events' equipment requests. Venue
   Staff lacks a documented equipment read policy. A complete checker
   needs authoritative visibility of competing commitments. Agree a narrowly
   scoped access solution; do not silently disable RLS, add a service-role
   client, or introduce SECURITY DEFINER. Invoker functions cannot detect rows
   that RLS silently hides just by counting the visible rows.
6. **Update Flask callers and error handling.** Availability must call the new
   venue-aware contract, not continue reporting stock-only availability as
   bookable stock. Map transfer conflicts and unresolved venue context to
   clear errors. Venue-booking creation/approval requires coordination with
   that story owner; the current equipment acceptance RPC alone does not
   protect venue booking writes.

No table or column additions are proposed at this stage. The status-only function patch reflects the user's selected contract;
the separate venue/transfer function, trigger, and any RLS changes remain shared
database work requiring team agreement.

## Transfer Predicate and Pooled Quantities

For one unit being reused, after ordering events chronologically, the proposed
predicate is:

```sql
-- Expression only; variables must come from validated database rows.
-- NULL venue IDs or invalid periods must not be treated as a successful check.
next_start >= prior_end
  + CASE WHEN prior_venue_id = next_venue_id
         THEN interval '0 minutes'
         ELSE interval '30 minutes'
    END
```

This predicate alone is not a complete pooled-stock allocator. One projector
in transit must not block a second independent free projector. Equally, several
events cannot all reuse the same last unit just because their pairwise checks
each appear feasible. The checker must establish a feasible assignment of
quantities across the complete affected schedule, including existing accepted
rows, maintenance, and provisionally allocated earlier pending requests.

Do not simply add 30 minutes to every reservation, sum all neighboring rows,
or reject every pair of different-venue requests. These shortcuts can reject
valid same-venue or pooled allocations. Review the allocation algorithm before
claiming this requirement is implemented without physical-unit identifiers.

## Read-Only Deployment Inspection

Run these SELECT queries in the Supabase SQL editor and retain the output for
the migration review. They inspect definitions, not application credentials or
event/person records. They make no schema or data changes.

```sql
-- Deployed equipment functions, signatures, privileges, and bodies.
SELECT p.oid::regprocedure AS signature,
       p.prosecdef AS security_definer,
       p.proacl AS privileges,
       pg_get_functiondef(p.oid) AS definition
FROM pg_proc AS p
JOIN pg_namespace AS n ON n.oid = p.pronamespace
WHERE n.nspname = 'public'
  AND p.prokind = 'f'
  AND (p.proname LIKE 'cs_equipment_%'
       OR p.proname = 'accept_equipment_request')
ORDER BY p.oid::regprocedure::text;

-- Current triggers on every table affected by equipment/venue feasibility.
SELECT c.relname AS table_name, t.tgname, t.tgenabled,
       pg_get_triggerdef(t.oid, true) AS definition
FROM pg_trigger AS t
JOIN pg_class AS c ON c.oid = t.tgrelid
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname IN ('event', 'venue_booking', 'equipment',
                   'equipment_reservation', 'equipment_unavailability')
  AND NOT t.tgisinternal
ORDER BY c.relname, t.tgname;

-- Current access policies, including role/profile lookup dependencies.
SELECT tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('event', 'venue_booking', 'venue', 'equipment',
                    'equipment_reservation', 'equipment_unavailability',
                    'profile', 'user_role')
ORDER BY tablename, policyname;

-- Existing constraints relevant to selecting a venue and interpreting statuses.
SELECT c.relname AS table_name, con.conname,
       pg_get_constraintdef(con.oid, true) AS definition
FROM pg_constraint AS con
JOIN pg_class AS c ON c.oid = con.conrelid
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname IN ('event', 'venue_booking', 'equipment_reservation',
                   'equipment_unavailability')
ORDER BY c.relname, con.conname;
```

## Migration Readiness and Validation

Before producing the enforcement migration, agree eligible selected-venue
statuses and the authoritative time source when event, venue-booking, and
equipment-request periods differ. Determine whether “booking creation” means
equipment-request submission, venue-booking submission, or both; the user's
automatic-check requirement is recorded, but the cross-story transaction
boundary is not yet defined. Inspect actual deployed definitions above rather
than rerunning the original `CREATE FUNCTION` / `CREATE TRIGGER` draft.

Validate same venue at 12:00; different venues at 12:00/12:29 (blocked) and
12:30/12:31 (allowed); reverse acceptance order; same building/different venue
IDs; spare independent stock; competing earlier requests; maintenance; missing
venue context; direct writes; venue/time changes; and concurrent acceptance
versus venue changes. Existing mocked tests do not prove these SQL guarantees.

PostgreSQL references:
[function replacement and signatures](https://www.postgresql.org/docs/current/sql-createfunction.html),
[transaction/advisory locking](https://www.postgresql.org/docs/current/explicit-locking.html).

## Organiser-Originated Requests and Quantity Proposals — 22 October 2026

This later user clarification supersedes the earlier Coordinator-created,
full-request-quantity acceptance workflow. The organiser submits the event and
its equipment requirements. Technical Support must see that event card even
when no separate equipment-reservation row exists yet. Staff enters a quantity
it can provide. If five units are requested and three are offered, save three
as a proposal and wait for organiser agreement. Do not reserve three or mark the
original five-unit request fulfilled at proposal submission.

### Current Implementation Gaps

- The organiser form persists `event.technical_requirements` as text and a
  `technical_support_required` flag, not structured equipment item/quantity rows.
  Do not automatically parse an authoritative quantity from free text.
- The Technical Support list starts from `equipment_reservation`, so an organiser
  event with no equipment row cannot appear there. It must instead support an
  event-based requirements inbox linked by `event_id`.
- The supplied Technical Support event SELECT policy only exposes events with
  equipment reservations. It does not establish access to the first event card
  before those rows exist. Its helper definition must be reviewed for the new
  access scope; the supplied function query did not include that helper.
- Organisers lack equipment-reservation SELECT/UPDATE policies in the supplied
  inspection. They need an authorised way to read/respond to their own offers.
- Current acceptance takes only a reservation ID and commits `quantity_requested`.
  It does not save a proposal, obtain organiser agreement, or reserve a different
  agreed quantity. The deployed status patch alone cannot support this workflow.

### Proposed Storage Change for Team Review

The following is a proposed schema contract, **not an approved or applied
migration**. Retain `quantity_requested` as the original structured requirement
when known; retain the organiser's original textual requirements on the event.
Do not overwrite it with the quantity Technical Support offers.

```sql
-- PROPOSAL ONLY: do not execute before team agreement and migration review.
ALTER TABLE public.equipment_reservation
  ADD COLUMN quantity_suggested integer,
  ADD COLUMN suggested_by uuid REFERENCES public.profile(user_id),
  ADD COLUMN suggested_at timestamptz,
  ADD COLUMN proposal_version bigint NOT NULL DEFAULT 0,
  ADD COLUMN organiser_agreed_version bigint,
  ADD COLUMN organiser_agreed_by uuid REFERENCES public.profile(user_id),
  ADD COLUMN organiser_agreed_at timestamptz;
```

Proposed constraints/guards must require a positive whole suggested quantity,
nonnegative proposal versions, and a complete proposer identity/timestamp once
an offer exists. Agreement must identify the event's actual organiser and the
current proposal version, including event, equipment, quantity and period.
The quantity, equipment or period must not be editable silently after agreement;
a revision increments `proposal_version` and clears agreement fields. A reserved
row's accepted proposal is immutable through the proposal workflow.

Keep status `requested` while awaiting agreement, and use `reserved` only after
final acceptance. No extra reservation status is proposed. Existing reserved
rows need an explicit compatibility/backfill plan: preserve their historical
committed quantity without fabricating past organiser consent. Do not apply
new consent guards to old rows without that reviewed migration decision.

### Proposed RPC Contracts

All three operations use authenticated caller identity, validate ownership/role
inside the database, use the existing transaction-lock protocol, and protect
against direct-write bypass under RLS/grants/triggers.

1. `propose_equipment_quantity(reservation_id, quantity_suggested,
   expected_proposal_version)`: Technical Support only. Save a new/revised offer,
   retain `requested`, invalidate earlier agreement, and return the saved offer.
   A first offer for an event without an equipment row needs a reviewed
   event/item/period creation contract as well; it cannot be created through
   this existing-row signature.
2. `agree_equipment_proposal(reservation_id, expected_proposal_version)`:
   the linked event's organiser only. Read the proposed values from the database,
   record agreement to that exact version, and retain `requested`.
3. `accept_equipment_request(reservation_id)`: Technical Support final acceptance.
   Require current organiser agreement; recheck venue eligibility, all committed
   quantities, maintenance, transfer gaps and agreed-request priority atomically.
   Commit only the agreed `quantity_suggested`, then set `reserved`.

A positive quantity is a proposal, not a stock guarantee. Stock may change while
waiting for organiser agreement. If final validation fails, retain the proposal
and agreement for review and explain the conflict; do not silently reduce the
quantity. Showing agreement does not permit overriding a failed stock check.
The chosen design preserves the existing Technical Support final-acceptance
role. Whether organiser agreement should itself perform final reservation is
not confirmed; do not implement that alternative implicitly.

### Affected Workspace and Shared Owners

- Equipment service/routes: event-based inbox, offer validation, proposal and
  final-acceptance endpoints; pass the caller's existing authenticated client.
- Technical Support UI: open organiser event cards; show original requirements,
  suggested quantity input, saved proposal and agreement state. Disable final
  acceptance until the current offer is agreed. Do not present the old single
  acceptance button as implementing this new workflow.
- Organiser UI: show offered item/quantity/period and allow agreement to the exact
  saved version. Coordinate this with the organiser/event-request story owner;
  no changes to that story's files are made by this review.
- Stock and priority SQL: accepted rows consume the agreed offered quantity,
  rather than the organiser's original requested quantity. Review earlier-request
  allocation with the new agreement stage. Venue/transfer enforcement remains
  required and is not supplied by the status-only patch.
- RLS/grants: permit Technical Support to see eligible organiser events needing
  equipment before reservation rows exist, and permit organisers to read/respond
  only to offers belonging to their own events. Do not grant organisers arbitrary
  UPDATE access to status, equipment, quantity, or decision fields.

Implementation depends on team agreement for the proposed columns, RPC contracts,
RLS scope, legacy-row compatibility and cross-story handoff. No shared database
change or new proposal runtime has been applied by this review.
