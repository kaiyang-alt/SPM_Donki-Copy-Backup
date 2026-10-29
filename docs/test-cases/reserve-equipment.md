# Test Cases — Reserve Equipment

Specification for [Reserve Equipment](../user-stories/reserve-equipment.md).
Use synthetic accounts and catalogue/venue data. Functional targets below are
separate from the recorded local execution results.

## Setup

Two organisers, Technical Support, Coordinator and Venue Staff use existing
Supabase auth roles. Equipment has a known total quantity. Events have a single
confirmed venue booking matching the equipment period unless a negative case
changes it. Pending reservations use `requested`, accepted use `reserved`.
All clocks below are Singapore time.

## Functional Cases

| ID / Criteria | Steps / Test data | Expected result |
|---|---|---|
| TC-001 / AC1 | Organiser submits an event needing equipment. Do not create an equipment row. Sign in as Technical Support, refresh the dashboard and open its card. Repeat with only nonblank technical text and the support flag false. | No card appears while draft/requested/planning/changes_requested. Coordinator moves event to approved, then saved requirements appear and open without an equipment row. Approved/confirmed events allow proposals. |
| TC-002 / AC2 | For an eligible event, save suggested quantities blank, zero, negative, fractional, then three. Include an existing structured requested quantity five. | Invalid values fail; three saves as `requested`, five stays intact, and stock is not committed. Text-only original requirements remain text, never a guessed numeric quantity. |
| TC-003 / AC3, AC7 | Organiser opens Equipment proposals, reviews three offered from five requested, and agrees. Attempt read/consent with another organiser and attempt direct quantity/status edits. | Only owner can read/respond. Agreement stores the reviewed version; arbitrary organiser edits fail. No stock commitment yet. |
| TC-004 / AC4, AC6 | Try acceptance before consent, then agree and accept with stock and venue available. Retry after success. | Before consent fails. Successful RPC reserves exactly three, preserves five and returns saved metadata. Retry returns same row; no duplicate allocation. |
| TC-005 / AC4 | Reduce available stock through overlapping reservations and active maintenance; repeat with cancelled maintenance and intervals overlapping different portions of the candidate period. | Calculate minimum free quantity over time, not a sum of unrelated overlaps. Reject over-allocation. Cancelled maintenance has no effect. Failure retains pending state. |
| TC-006 / AC5 | One unit; event A same venue ends12:00; event B starts12:00. Check and accept in both orders. | Immediate same-venue reuse succeeds when all other checks pass. Actual periods remain unchanged. |
| TC-007 / AC5 | One unit; different venue UUIDs in same building; A ends12:00. Test B starts12:00,12:29,12:30,12:31 and reversed acceptance order. Repeat with an independent spare unit, then maintenance removing the spare. | Reused unit requires at least30min. Spare can serve independently only while available. Same names/building do not bypass UUID comparison. |
| TC-008 / AC1, AC7 | Open dashboard/assignment cards and refresh details. Check availability, then accept. Simulate missing metadata, failed RPC and account change during loading. | Real data/errors appear; no prototype substitutes or optimistic reservation. Refresh clears old availability; stale account responses cannot populate the new session. |
| TC-009 / AC3 | Agree to version1, revise quantity or period, then submit agreement for version1 and try acceptance. | Revision clears consent. Stale agreement and acceptance fail until organiser agrees to current version. Original requirements remain intact. |
| TC-010 / AC4, AC8 | Remove confirmed venue; add a second active booking; mismatch period; deactivate venue; add overlapping venue booking/block; include null/invalid effective data. Repeat incompatible changes after reservation. | Invalid final acceptance fails; changes invalidating an existing commitment roll back. Hidden venue commitments cannot make the schedule appear free. |
| TC-011 / AC4, AC6 | Two agreed requests compete. Accept later first; repeat with infeasible earlier request, equal/missing timestamps and simultaneous acceptances. | Earlier feasible agreed request retains provisional priority. Infeasible request consumes none. Ambiguous priority fails. Concurrent calls cannot double allocate. |
| TC-012 / AC7 | Call RPCs anonymously or as unrelated role; try direct table edits forging agreement/version. Apply migration twice in isolated database; include infeasible legacy reserved schedule. | Permissions/guards block bypasses. Rerun preserves data; invalid legacy schedule aborts migration atomically. |
| TC-014 / AC4, AC6 | An older agreed proposal has no confirmed venue (including a non-overlapping 2029 period). Check availability and accept a later-requested, agreed 2026 event with its own confirmed venue. Then try accepting the venue-less proposal itself. Repeat with a feasible earlier overlapping request. | The venue-less proposal contributes no provisional allocation and remains pending. The ready event can reserve available stock and retry safely. The venue-less candidate itself is rejected. Feasible earlier overlapping demand still blocks over-allocation; failed acceptance commits nothing. |
| TC-015 / AC1, AC6, AC7 | Review an auto-assigned planning event as its Coordinator, approve it, arrange a venue, propose equipment, obtain organiser agreement, check availability and accept, then confirm through readiness. Try proposing/reserving during planning and forging the approval audit as an organiser. | Resource work starts only at approved. Equipment reservation preserves event approved; readiness can move it to confirmed. Planning work is blocked, audit role/assignment/state restrictions remain, and SQL patches can be rerun. |

## Local Verification — 22 October 2026

TC-013 (handoff): follow main's flow from organiser submission through initial
Coordinator approval, venue approval, staff proposal, organiser agreement and
staff reservation, then reload Coordinator readiness. Saving equipment must
set only its reservation to `reserved`; the event stays `approved`. The existing
readiness service recognises reserved equipment, and final confirmation remains
a Coordinator action once all arrangements are ready. Automated service
integration now covers accepted equipment appearing in Coordinator readiness,
the event staying in approved after TSS acceptance, successful Coordinator
confirmation, and confirmation blocked while another equipment request is
pending. Live account execution of
this full handoff remains pending.

The latest inbox policy restricts visibility to approved/confirmed events;
Python/UI regressions cover the revised gate. The updated SQL policy still
requires live deployment and verification.

- Python regression suite: **331 passed**; equipment service/route checks include
  Coordinator-approved inbox events, offer validation, ownership, consent and RPC delegation.
- JavaScript UI suite: **20 passed**, including organiser events with no equipment
  rows, suggested quantity, consent gating, stale agreement and session changes.
- Isolated PostgreSQL17 with synthetic RLS: migration/rerun, organiser inbox
  visibility before equipment rows, original5/offered3, consent/ownership,
  reserved-stock accounting, revision invalidation, immutable accepted offers,
  venue-change guard, same-venue reuse, different-venue transfer boundaries,
  reverse order, final RPC transfer checks, spare stock/maintenance and RPC
  grants passed. Unrelated organiser description edits remain permitted.
- Project import, documentation, repository structure and whitespace checks pass.

SQL tests use `tests/equipment_proposals_fixture.sql`, the existing acceptance
baseline, the full proposal migration and `tests/test_equipment_proposals.sql`.
The fixture is local-only and must never be run against Supabase. Python/UI tests
use simulated Supabase responses; PostgreSQL checks use real local SQL with
synthetic policies. No live Supabase deployment or browser/account verification
was performed. Concurrent acceptance/load remains a deployment verification
requirement; local serial checks do not establish production concurrency behavior.

## Pending-Venue Priority Regression — 29 October 2026

The shared-data diagnosis found an earlier agreed 2029 proposal with no confirmed
venue aborting a ready 2026 event's availability check. TC-014 reproduces this
with real local PostgreSQL 17: it fails on the original functions and passes
with the scoped patch. Both availability and final acceptance skip the earlier
venue-less proposal; the candidate's own venue requirement, retry behavior and
feasible overlapping demand priority remain enforced.

The SQL proposal suite, patch rerun and venue-alternatives SQL compatibility
checks passed locally. Project health passed with 348 Python tests; the equipment
UI suite passed 21 tests. This correction has not been applied to live Supabase;
Family Day's successful live reservation remains pending deployment and retest.

## Approved Workflow Alignment — 29 October 2026

TC-015 is covered by the application regressions and
`tests/test_coordinator_review_workflow.sql`. The SQL test reproduces the supplied
Coordinator audit policy, applies its patch twice, and checks real authenticated
approval audit writes, rejected organiser forgeries, approved equipment visibility,
consent, availability, reservation and status preservation. It also checks that
planning is insufficient for equipment proposals. The Python handoff test verifies
readiness confirms an approved event only when other arrangements are complete.

Final project health: **355 Python tests passed**. Venue/equipment UI suites:
**29 tests passed**. Local PostgreSQL proposal and venue-alternatives suites,
both scoped patches and patch retries passed. These results use synthetic RLS;
they are not evidence that the new patches are deployed or that the full live
browser workflow has passed. Reconcile other story owners' canonical status
wording with the shared team decision without changing unrelated behavior.

## Subsequent Developer Confirmation

After receiving the patches and aligned app, the developer reported that the
workflow and status update work. Record this as user-reported functional evidence,
not a new catalogue inspection or a pass for every case above. Individual live
results for stock exhaustion, overlap/transfer boundaries and concurrent requests
were not supplied with this confirmation.

## Post-Patch Catalogue Verification — 29 October 2026

The developer supplied a fresh export captured at 08:24:13 UTC (16:24:13 Singapore
time). Its two changed equipment function bodies exactly match the priority
patch, and the only changed RLS policy exactly matches the Coordinator audit
patch. All other catalogue sections and routine metadata are unchanged from
the earlier export. This verifies deployment in the shared database, in addition
to the developer's functional confirmation. Earlier pending-deployment notes
above describe preparation stages and are superseded by this evidence. No new
case-by-case live stock-exhaustion, transfer-boundary or concurrency results were
provided, so those are not marked passed by this inspection.
