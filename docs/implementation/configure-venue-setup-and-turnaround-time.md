# B1 runtime implementation report

Scope: [Configure Venue Setup and Turnaround Time](../user-stories/configure-venue-setup-and-turnaround-time.md)
and its [approved functional cases](../test-cases/configure-venue-setup-and-turnaround-time.md).
The installed contract is documented in [database_schema.md](../architecture/database_schema.md).
The approved external executable/migration designs govern B1-OCC-v1 and the
database RPC. No schema, policy, grant, SQL artifact or live data was changed by
this runtime work. The authenticated B1 RPCs remain disabled; venues have not
been populated. Existing story/test specifications and shared architecture
baseline files were preserved.

## Application path

- Staff-only `GET /api/venues/<venue_id>/buffers` returns the current pair,
  `buffer_config_revision` and explicit configuration state. NULL remains NULL.
- Staff-only `PUT /api/venues/<venue_id>/buffers` accepts only `setup_minutes`,
  `turnaround_minutes`, `expected_revision` and UUID `operation_id`. It validates
  exact integers (excluding booleans, decimals and strings), required revision/
  token, negative values and technical representation bounds. Zero produces
  the existing decision-required response, not a business invalidity rule.
- The service calls `b1_save_venue_buffers` with the caller JWT through the
  existing authenticated client. It never writes B1 columns or notifications
  directly. Recipients, records, notice content and lifecycle remain derived
  by the installed database operation.
- Stable error codes distinguish stale revision, token reuse, assessment
  blockers, zero decision, disabled capability and an unconfirmed save. SQL
  DETAIL/HINT and internal exception text are not returned. An unconfirmed save
  must be retried using the same intent/token.
- Existing `PUT /api/venues/<venue_id>` retains its capacity, supported-layout
  and accessibility behaviour. A separate Staff navigation item provides the
  B1 form in the existing design. It shows values/revision, saves positive
  whole-minute values, preserves retry intent after lost responses, and
  displays conflicts, incomplete assessment and incomplete routing separately.
  Coordinator venue/request views display durations and occupied times without
  edit controls. JavaScript refuses unsafe integer revisions rather than
  rounding a bigint into a different expected revision.
- Coordinator-only `GET /api/venue-buffer-notifications` reads only the caller's
  `venue_buffer_conflict` notices through existing recipient RLS, with no notice
  write/mark-read action. A B1-specific inbox section supplements the existing
  notification page; other stories' presentation is preserved.

## Shared occupancy and consumer audit

`app/services/venue_occupancy.py` implements B1-OCC-v1 once: timezone-aware UTC
instants, integer minutes, half-open intervals, exact touching non-conflicting,
NULL configuration-required, zero decision-required and explicit invalid/
overflow failures. Booking scheduled times are preserved. Blocks use their
recorded bounded interval without extra expansion. Retained rows carry
occupied times/assessment state; conflicts and limitations are separate data.

| Consumer | Runtime integration and boundary |
| --- | --- |
| Staff schedule `/api/venues/<id>/schedule` | Shared occupied periods, conflict flags, preserved records, configuration and visible assessment blockers/limitations |
| Staff availability `/api/venue/availability` | Same shared assessment; requested/tentative shown as potential holds, unknown/malformed data retained and flagged |
| Coordinator booking context | Read-only configured durations and occupied times for visible records; no assertion that the restricted snapshot is a full venue calendar |
| Venue search | Removed raw timestamp/status-only prefilters; full visible intervals use the shared assessor; incomplete venues are excluded from the available list with explicit limitations |
| Booking availability/submission | Shared candidate occupancy; no zero fallback; missing authority/configuration or unresolved holds block a free-slot/write assertion |
| Primary pending-request approval | Preserves the selected request and returns `B2_HOLD_VALIDITY_REQUIRED`; excluding it from pair comparisons cannot establish its lifecycle validity |
| Legacy `venue_service.update_venue_booking_request_status` | Other-owner dependency: still uses legacy requested_date/start_time/id and pending/approved semantics. Not rewritten as a B1 lifecycle change |
| Both operational-block writers | Contract A dependency: existing raw/legacy block-write behaviour is not implemented or redesigned by B1; must consume B1 and adopt locking before cohort activation |
| Readiness/replacement | C2/C1 ownership; no implementation or status mutation in this task |

Read queries request exact counts. Capped/unverifiable responses cannot establish
availability; they remain incomplete rather than silently omitting arrangements.
Confirmed malformed schedules, unknown/NULL booking/block status and active
blocks without assessable bounded intervals are blockers, never free periods.
Read calendars retain the problematic rows. The database save itself rolls back
on authoritative assessment failure, as already installed.

## Remaining dependencies and enablement decision

**Live RPC enablement technically ready: NO.** The configuration adapter/UI can
be tested with mocks, but unrestricted live B1 activation still requires:

1. B2 authoritative requested/tentative hold validity. No active/expired state,
   expiry, cancellation or automatic lifecycle change is inferred. Any such row
   keeps a venue's availability incomplete, including a non-overlapping hold
   whose validity is still unknown.
2. Full Coordinator post-change conflict-calendar integration. The documented
   booking/block SELECT policies already establish read authority for both
   Venue Staff and Event Coordinators, and the runtime recognises both roles.
   Complete exact-count reads are still required; an empty result alone is not
   proof of availability. Coordinator-only fixtures now exercise that supported
   read path without Staff membership. The separate restricted planning-event
   snapshot remains unchanged and is not a full conflict calendar. No new RLS,
   privileged read RPC or service-role bypass is needed for existing authority.
3. Participating booking/hold/block and C1/C2 writers adopting the venue-first,
   event-second database locking protocol, with coordinated race verification.
   Existing REST read/check/write sequences cannot provide those transaction
   locks. Legacy approval and block writers remain explicit owner dependencies;
   successful Python snapshot tests do not establish end-to-end race safety.
4. Separately authorised Staff population through the approved save operation
   and coordinated consumer activation. No customer values are guessed or
   backfilled, and no RPC grant has been enabled to run tests.

## AC and test coverage

| AC / approved case | Implemented verification | Live/integration limit |
| --- | --- | --- |
| AC1; TC-001 | Independent venue readback, exact integer/revision/token validation, caller-JWT RPC, NULL state, duration UI | Persistence is exercised through a mocked RPC contract; no live save |
| AC2; TC-001/002 | OCC-EXAMPLE, independent durations, cross-date setup/turnaround, UTC offset transition, setup-only/turnaround-only conflict, touch/non-touch and overflow vectors | Existing database conformance verification is not rerun by this task |
| AC3; TC-001/002 | Shared search/booking/calendar helper; Coordinator-only read authority, potential hold preservation, no status-only validity, incomplete read/count boundary | B2 validity and writer protocol dependencies above |
| AC4/5; TC-003 | 15/15 to 30/45 conflict; successful mocked conflict-save response; original booking/event data unchanged; Staff calendar flags | Actual transactional save/impact behaviour stays in the installed disabled RPC |
| AC6; TC-003 | Staff calendar retains records and occupied conflicts; Coordinator own visible periods are read-only | Full Coordinator post-change conflict-calendar integration remains incomplete |
| AC7; TC-003 | Persisted-notice and durable-routing-exception response handling; UI distinguishes incomplete routing; Coordinator own-notice inbox filters recipient/type under caller JWT | No new live notice/delivery claim; database-derived results mocked |
| AC8; TC-003/004 | Coordinator-only edit denied, no Coordinator edit navigation, no event/booking mutation by buffer adapter; ordinary venue detail regression | Later human assessment/C1/C2 decisions remain with their owners |

New tests live in `tests/test_venue_occupancy.py` and
`tests/test_venue_buffers.py`; existing venue tests include consumer regressions.
The Node VM UI harness verifies Staff-only editor registration, unconfigured
rendering, escaped conflict/routing feedback and identical retry-token/payload
reuse after a lost response. RPC mocks do not claim to test deployed SQL
permissions, SQL transaction rollback or real notice delivery.

The read-authority correction removes Staff membership from positive Coordinator
fixtures. Tests cover Coordinator-only complete empty reads, visible confirmed
conflicts, unresolved requested/tentative holds, malformed authoritative records,
and truncated/count-unverified booking and block reads. Role checks also verify
that other roles, or another user's Staff role, do not establish caller authority.
The restricted planning-event snapshot and all activation boundaries are unchanged.

## Validation results

- Targeted B1 and existing venue suites: **256 passed**.
- Full pytest suite: **364 passed**.
- `python scripts/project_health.py`: **PASS**, including production app import,
  its full 364-test regression run and all bundled checks.
- `python scripts/validate_docs.py`: **PASS**, 12/12 story references.
- `python scripts/validate_structure.py`: **PASS**, 12 required files and 16
  required directories.
- `git diff --check`: **PASS**.
- Node syntax checks for all three changed venue scripts and the offline UI
  contract harness: **PASS**. No live RPC was enabled or called for validation.

Only B1 route/service/helper, venue frontend, venue regression/B1 tests and this
report were changed by this runtime task. The pre-existing dirty schema and
story/specification changes were left untouched. The current feature branch
already contains fetched `origin/main`; no commit or push was made.
