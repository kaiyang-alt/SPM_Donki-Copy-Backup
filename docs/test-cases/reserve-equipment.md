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
| TC-001 / AC1 | Organiser submits an event needing equipment. Do not create an equipment row. Sign in as Technical Support, refresh the dashboard and open its card. Repeat with only nonblank technical text and the support flag false. | No card appears while draft/requested/changes_requested. Coordinator moves event to planning, then saved requirements appear and open without an equipment row. Planning/confirmed events allow proposals. |
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

## Local Verification — 22 October 2026

TC-013 (handoff): follow main's flow from organiser submission through initial
Coordinator approval, venue approval, staff proposal, organiser agreement and
staff reservation, then reload Coordinator readiness. Saving equipment must
set only its reservation to `reserved`; the event stays `planning`. The existing
readiness service recognises reserved equipment, and final confirmation remains
a Coordinator action once all arrangements are ready. Automated service
integration now covers accepted equipment appearing in Coordinator readiness,
the event staying in planning after TSS acceptance, successful Coordinator
confirmation, and confirmation blocked while another equipment request is
pending. Live account execution of
this full handoff remains pending.

The latest inbox policy restricts visibility to planning/confirmed events;
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
