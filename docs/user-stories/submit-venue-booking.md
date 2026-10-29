# Submit a Venue Booking Request

## User Story

As an Event Coordinator, I want to submit alternative venue booking requests for an approved event so that Venue Staff can confirm one suitable venue arrangement.

## Acceptance Criteria

- **AC1:** An authenticated Event Coordinator can select an available venue, date, time slot, and setup layout for an event they are authorised to coordinate. For this story, the eligible event status is `approved`.
- **AC2:** Before submission and again before Venue Staff confirmation, check for overlapping confirmed venue bookings and active venue blackout periods using the deployed B1 setup/turnaround occupied-period rules. Reject conflicts without saving the attempted submission or confirmation. Pending alternatives do not block the venue slot for other events.
- **AC3:** An event may have multiple pending alternative venue bookings. Submission saves a non-blocking `requested` booking and does not reserve the venue. Each alternative may have its own date, start/end time and setup layout.
- **AC4:** Persist each booking linked to its Event ID and Venue ID, with its own period and setup layout. Saving another alternative must not overwrite an earlier booking's layout.
- **AC5:** Notify the Venue Staff assigned to the selected venue through the Notification service.
- **AC6:** Display “Pending Venue Approval” in the Coordinator event workspace and retain that display label when the workspace is reloaded. The persisted booking status remains `requested` or `tentative`; the display text is not a database status.
- **AC7:** An event may have at most one confirmed venue booking. When Venue Staff confirms an alternative, automatically change all other `requested` or `tentative` bookings for that event to `cancelled`. Confirmation and cancellation must succeed together or leave all bookings unchanged. Preserve rejected/cancelled records and their history; do not delete alternatives.
- **AC8:** Repeating a successful confirmation must not duplicate its effects. Concurrent attempts to confirm different alternatives for the same event, or overlapping bookings for the same venue, must not commit conflicting confirmations. If another alternative is already confirmed, prevent confirmation of a different alternative; changing a confirmed arrangement is outside this submission workflow.

## Confirmed Project Rules

- The Coordinator submits the request; Venue Staff have final approval authority.
- Multiple pending alternatives are allowed, but only one venue arrangement may be confirmed for the event. Pending alternatives remain non-blocking until Venue Staff reserves the selected venue by confirming it.
- The live `venue_booking.status` CHECK constraint permits exactly `requested`, `tentative`, `confirmed`, `rejected`, and `cancelled`. Do not persist UI labels such as `Pending Venue Approval` or `Approved` as event or booking statuses.
- Both venue and equipment arrangements must be complete before confirming the event. Submitting or approving a venue booking must not automatically confirm the event.
- Existing authentication, Supabase configuration, schema, and RLS must be preserved.

The organiser submits event requirements, the Coordinator gives initial approval,
venue and equipment arrangements proceed, and the Coordinator makes the final
event-confirmation decision. Venue Staff retain authority over venue reservation.

The customer clarifications supplied on 27 October 2026 supersede the one-active-
arrangement rule in the [shared project context](../architecture/project_context.md).
They also supersede the previous assumption that submission immediately places
a blocking hold. Shared-baseline reconciliation is required after approval.

## Requested / Tentative Lifecycle and Expiry

Submission uses `requested`; Venue Staff confirmation uses `confirmed` and
reserves the slot. Unconfirmed alternatives, including existing `tentative`
rows, are non-blocking and are automatically cancelled when another alternative
for their event is confirmed. No new action or status transition for creating
`tentative` rows is introduced by this requirement.

Automatic cancellation is triggered by confirmation of an alternative, not by
elapsed time. No timed expiry duration or automatic time-based expiry has been
specified. Do not invent an expiry period or an `expired` status.

Booking payloads use a same-day convention; overnight bookings are not represented
by this date/start/end payload. Venue conflicts use B1's half-open occupied period
`[start - setup, end + turnaround)`. With 15-minute setup and turnaround, an event
ending at 12:00 permits the next event at 12:30, not 12:29. Retain configured
buffer durations and B1's configuration errors. The existing 30-minute equipment
transfer gap between different venues remains unchanged; it is a separate rule.

## Preconditions and Dependencies

- A valid Supabase session with the `event_coordinator` role for submission and `venue_staff` for venue confirmation.
- The event is visible under the caller's existing RLS policies and is in `approved` status. RLS must enforce which events the Coordinator may coordinate.
- The selected venue exists and the database provides the venue-to-staff assignment relationship.
- RLS must expose the conflicts required to make an availability decision; filtering out another user's reservation must not make its slot appear free.
- Database enforcement must prevent overlapping confirmed bookings for one venue and more than one confirmed booking for one event, while permitting multiple non-blocking alternatives. Confirmation and cancellation of other alternatives require an atomic operation under the caller's existing authentication. Application prechecks alone cannot guarantee this across workers.
- The documented schema stores layout on `event`, not on each `venue_booking`. Independent alternative layouts require approved per-booking persistence; do not overwrite `event.layout_requirements` to represent several different booking layouts.
- The notification insert must be permitted under the existing RLS design.

## Test Cases

[Functional test specification](../test-cases/submit-venue-booking.md)

Automated route/service tests: `tests/test_venue_booking.py`. The fixture uses the actual Flask application so missing blueprint registration is detected. Database calls are simulated; this is not a live schema/RLS or browser end-to-end test.

## Scope

This story covers alternative submission, its pending display state, notification,
and the required confirmation-triggered cancellation contract. Venue Staff
approval integration must be coordinated with that story's owner. Venue editing,
maintenance management, changes to an already confirmed arrangement and final
event confirmation remain owned by their respective workflows.

## Cross-Story Dependencies

- Venue Staff review must reserve only the selected alternative and cancel its siblings atomically, without treating pending alternatives as confirmed conflicts. That story's canonical requirements/tests are not changed here.
- Equipment validation uses the single confirmed selection and ignores non-blocking venue alternatives. Equipment acceptance and transfer checks still require a confirmed venue; initial equipment review may proceed in parallel with venue arrangements.
- Readiness, organiser arrangement displays, venue search and availability calendars must distinguish pending alternatives from the confirmed selection. Cancelled alternatives must not leave a completed venue arrangement displayed as outstanding merely because their records remain present.
- The existing equipment arrangement guard must continue protecting committed equipment against incompatible venue/time changes. Simply removing the submission precheck does not satisfy these dependencies.

## Requirement Revision / Approval Status

Reconciliation of customer clarifications supplied on 27 October 2026.
Story and Acceptance Criteria approved (Human Gate 1) in the conversation on
27 October 2026. The revised functional test specification was also approved
(Human Gate 2) in the conversation on 27 October 2026. Shared changes were approved
at Human Gate 3, followed by the supplied live migration verification on
28 October 2026. The branch now implements the alternative-booking workflow;
execution evidence and remaining limitations are distinguished below.

## Current Implementation / Deployment Evidence — 28 October 2026

The developer supplied the full `venue_booking_alternatives_verification` result:
the booking layout column and confirmation RPC exist, the confirmed-event unique
index is present, all five expected guards/locks are enabled, duplicate confirmed
events are zero, and confirmed occupied-period validation passed. The shared-lock,
equipment decision, B1 request-identity and calculator-EXECUTE flags are true.
Confirmation EXECUTE is authenticated-only; B1 save ownership remains unchanged.
This satisfies the developer execution checkpoint using supplied evidence; no
direct database connection or real-account browser test is claimed.

The Flask service now saves independent booking layouts without updating event
requirements, permits non-blocking alternatives, checks occupied availability
through the deployed RPC, and confirms through `confirm_venue_booking`. Known
database failures are translated to safe UI errors. The existing UI displays each
booking's full period/layout and cancellation outcome, labels pending alternatives
as non-blocking, and requires a new availability check after form criteria change.
Venue search uses the same decision RPC. Equipment proposal forms select the
confirmed period despite pending alternatives. Organiser summaries and readiness
recognise the confirmed selection without treating cancelled alternatives as
outstanding. Stored event statuses and time-based event display are unchanged.

The readiness table and inspection history below describe earlier implementation
stages; they are retained as deployment rationale, not current blockers except
where explicitly stated. AC5 notification routing remains blocked. Other criteria
have local route/service, UI and SQL evidence; live authenticated end-to-end and
production-load verification remain separate checks.

## Relevant UML

[Venue alternatives sequence](../uml/submit-venue-booking.md).

## Implementation Readiness Audit / Approved Human Gate 3 Proposal

Read-only audit against repository code and the documented schema on
27 October 2026. Actual deployed functions, constraints, triggers and policies
have not been inspected in this task. The team proposal below was approved in
the conversation on 27 October 2026 (Human Gate 3). Approval is not evidence of
deployment; no database change has been applied by this task.

| Criterion | Readiness | Evidence / required work |
|---|---|---|
| AC1 | Ready with current architecture | Existing authenticated Coordinator route, assigned planning-event check and venue validation can be reused. |
| AC2 | Requires shared workflow/constraint verification | Booking service treats requested/tentative as conflicts and does not filter blocks to active. Equipment SQL also treats pending venue rows as commitments. Recheck authoritative conflicts under the shared database write lock. |
| AC3 | Requires shared workflow change | Submission rejects any existing active event booking. Remove that restriction only with consistent non-blocking conflict semantics and equipment compatibility. |
| AC4 | Requires shared schema change | No per-booking layout column exists; submission updates event-wide layout. |
| AC5 | Requires another dependency and permission decision | No documented venue-to-staff assignment source or permitted notification INSERT exists. This pre-existing blocker is unresolved. |
| AC6 | Ready with current architecture, dependent on AC4 | Reuse current pending label and list UI; show each booking's persisted layout and full period. |
| AC7 | Requires shared database/workflow change | Current approval updates one booking only. No documented atomic confirmation/sibling cancellation operation exists. |
| AC8 | Requires shared database/constraint change | Current approval rejects a repeat confirmation. Application prechecks do not establish cross-worker concurrency safety. |

### Approved minimum shared-change scope

1. **Per-booking layout (AC4).** Add nullable `venue_booking.setup_layout`
   text storage. New submissions must validate and persist a nonblank supported
   layout there. Keep `event.layout_requirements` as the organiser's event-level
   requirement, without overwriting it on each alternative submission. Legacy
   rows remain readable without inventing an independent layout: backfill from
   event layout only where historical evidence supports it; otherwise display
   missing legacy layout explicitly. Do not impose a blanket NOT NULL constraint
   on historical rows without a reviewed backfill.
2. **Atomic Venue Staff confirmation (AC2, AC7, AC8).** Introduce an
   authenticated `confirm_venue_booking(p_booking_id uuid)` RPC that verifies
   the Venue Staff role and existing RLS access, rechecks confirmed conflicts
   and active blocks, confirms the selected row, and cancels same-event
   requested/tentative siblings in one transaction. Retry returns the already
   saved confirmation. Another confirmed selection or a rejected/cancelled
   target fails without changes. The event status is not changed.
3. **Authoritative enforcement (AC2, AC7, AC8).** Review deployed protections
   before adding replacements. Use the existing equipment transaction advisory
   lock `(212,8401)` for affected booking/block writes and confirmation so the
   equipment guard and venue decision cannot race. Enforce at most one confirmed
   booking per event and prevent confirmed venue overlaps/active-block conflicts
   at the database boundary, including direct writes. A partial unique index on
   confirmed event bookings and compatible validation triggers are proposed;
   preflight existing duplicates/conflicts and abort rather than changing them
   silently. Existing equipment guards must see the final confirmation and
   cancellation result together. Inspect trigger ordering and access before
   choosing the final migration statements.
4. **Narrow permissions (AC2, AC7, AC8).** Keep the write RPC under caller RLS
   and reuse documented Venue Staff SELECT/UPDATE rights. Verify actual conflict
   and block visibility. If complete visibility is unavailable, propose a
   narrowly scoped, read-only trusted-owner conflict checker returning a decision
   only, with authenticated-only execution and internal role checks. Such a
   checker also needs explicit team approval; do not use a service-role client,
   blanket table access or disabled RLS. Never treat hidden rows as free slots.
5. **Assigned compatibility work.** Team approval must explicitly include the
   Venue Staff approval caller, booking UI/service/tests, equipment checker and
   proposal-period selection, and organiser arrangement summary/tests. Equipment
   uses the single confirmed venue and ignores pending alternatives as venue
   commitments; stock, maintenance, consent and transfer checks remain intact.
   A confirmed venue must satisfy the agreed equipment period; do not silently
   move equipment or reuse consent for a different period. Organiser summaries
   retain cancelled history without calling it outstanding when a selection is
   confirmed. Readiness already ignores cancelled/rejected bookings; verify that
   behavior with the new cancellation outcome. Venue search already filters
   confirmed bookings and active blocks; preserve it. Calendar display owners
   must reflect pending alternatives as non-blocking. Other story requirement
   files are outside this assignment.

**Rationale:** application-only checks cannot preserve independent layouts or
make multiple authenticated writes atomic. Removing only the submission check
would leave equipment guards rejecting alternatives and organiser summaries
reporting cancelled alternatives as unfulfilled arrangements.

**Risks / compatibility:** deployed SQL may differ from local drafts; existing
confirmed conflicts and ambiguous historical layouts need explicit resolution.
Confirmation retry changes an existing test expectation. The global shared lock
serialises affected writes, so concurrency testing must cover acceptance versus
confirmation/block changes. Do not deploy an old equipment draft afterwards that
restores the old venue-count or pending-conflict semantics.

**AC5 remains blocked:** the team must supply the intended venue-to-staff
assignment source and approve notification write permissions/delivery contract.
This proposal does not invent that relationship or claim a notification warning
satisfies the acceptance criterion.

**Can unaffected implementation proceed independently?** Partially: existing
authentication/validation can be reused. Core alternative submission, independent
layouts and atomic confirmation remain coupled to these shared changes. Runtime
the original audit awaited deployed-definition inspection and the developer
execution checkpoint. These are now covered by the supplied verification above.
AC5 is still blocked on its assignment/notification contract; the approval does
not supply that missing data.

### Developer execution steps — deployment inspection

1. Open the shared ConnectSphere project's Supabase SQL Editor as the existing
   database owner. Use the project serving this application.
2. Open [venue-booking-alternatives-preflight.sql](../database/venue-booking-alternatives-preflight.sql)
   and run its complete SELECT. This is a read-only inspection, not a migration;
   it changes no records, policies, functions or schema.
3. Return the complete `venue_booking_preflight` result to the developer preparing
   the approved migration. Export the full result if the editor truncates its
   display. If a query fails, return its error instead of changing the schema to
   make it pass. Do not send credentials or JWTs.
4. The developer compares live definitions with the approved design and prepares
   the exact migration and verification steps. Unknown live triggers/functions
   must not be overwritten using assumptions from local draft SQL.
5. After the migration is supplied, the designated shared-change owner executes
   it, verifies the resulting schema/guards, confirms completion and updates the
   database schema document. Dependent runtime work resumes after that checkpoint,
   as required by the primary implementation workflow.

No Supabase database connection is available to this task. The preflight returns
catalogue definitions and aggregate conflict counts, without event/user details.
The current SQL files are unversioned deployment artifacts under `docs/database`;
no existing canonical venue-alternatives migration was found. The preflight is
kept there without creating a new migration directory or changing repository
structure.

### Supplied live inspection findings — 27 October 2026

The developer supplied the original preflight result in the conversation. It
confirms no duplicate confirmed selections, overlapping confirmed booking pairs,
confirmed-booking/active-block overlaps, invalid confirmed periods/links, or
pending siblings alongside a confirmed selection at inspection time (all five
aggregate counts are zero). These counts must still be checked transactionally
when the eventual migration executes.

The proposal columns/functions and equipment arrangement/locking triggers are
present in the supplied database definitions. The deployed equipment checker
still counts requested/tentative venue bookings as active commitments, confirming
the approved compatibility change is necessary. The booking indexes supplied
contain only its primary key, and no `confirm_venue_booking` function appears in
the supplied result. `venue_booking.setup_layout` is absent.

An additional deployed B1 capability was discovered: `venue.setup_minutes`,
`turnaround_minutes`, `buffer_config_revision`, the B1 venue guard, and controlled
buffer-save/read functions owned by `b1_venue_buffer_executor`. Their definitions
are absent from the repository baseline. The save function invokes
`b1_buffer_conflicts`, includes pending-hold assessment limitations and takes
venue/event locks. That helper was not captured by the original function-name
filter, so occupied-period and lock compatibility remain unverified. Do not
overwrite, remove or redefine the B1 capability as part of this story.

The preflight file now includes a separate read-only `venue_buffer_supplement`
SELECT for the missing B1 functions and buffer/venue schema definitions, without
re-requesting the already supplied function bodies or event/user records. The
implementation owner needs this result and any relevant B1 occupied-period
contract to prepare the exact migration without bypassing a deployed rule.
Shared-change approval is already recorded; this is missing deployment evidence,
not a repeat story or architecture approval request.

### Buffer supplement findings / additional shared-owner decision

The supplied `venue_buffer_supplement` resolves the missing function definitions.
`b1_occupied_period` defines a half-open occupied venue period as event start
minus setup minutes through event end plus turnaround minutes. It rejects null,
zero or negative durations, invalid/non-finite periods and out-of-range dates.
`b1_buffer_conflicts` compares these expanded periods against other bookings
and active bounded blocks. Confirmed conflicts are classified as `identified`;
pending rows still have the historical `potential_hold_validity_unavailable`
classification. Pending uncertainty must not be mistaken for a blocking booking
under this story's newly approved lifecycle.

This reveals a requirement reconciliation needed before the final migration:
the current story/tests describe adjacency using raw event periods, whereas B1
has expanded venue occupancy. With 15-minute setup and turnaround durations,
an event ending at 12:00 and the next starting at 12:00 have overlapping occupied
periods; a 12:30 next start gives adjacent occupied periods. The equipment
same-venue transfer rule is separate and is not changed by venue buffers.

**Reconciliation accepted in the conversation:** the developer confirmed keeping
the existing half-hour gap and non-blocking alternatives. Submission and
confirmation should use the existing B1 occupied-period calculation for configured
venues; pending alternatives remain non-blocking. Preserve B1's explicit errors
for unconfigured/zero durations instead of guessing zero buffers. Update only
the affected story/functional boundaries; do not interpret this as changing the
equipment transfer gap or replacing B1's configured durations with a new fixed
venue duration.

**Additional shared ownership:** `b1_save_venue_buffers` locks a venue and reads
booking conflicts before its venue UPDATE reaches the existing equipment write
lock. The approved booking/equipment lock must be coordinated with that save
path before claiming consistent concurrent assessment. A narrowly scoped B1
integration change would obtain the shared lock before reading/recomputing the
buffer-save outcome, preserving existing receipts, revision checks, notification
routing and retained-booking behavior. Inspect all B1 callers and test the common
lock order before finalising this change. Updating the B1 save function is newly
discovered cross-story work, not included implicitly in the earlier list of
booking/equipment/organiser callers.

No further definition query is currently needed. The migration artifact includes
the scoped B1 lock integration while preserving its receipts, revision checks,
conflict reports, notifications and existing execute grants. No live B1 SQL,
runtime code, data or schema has been changed by this task.

### Approved migration execution checkpoint

Prepared [migration](../database/venue-booking-alternatives-migration.sql) and
[read-only verification](../database/venue-booking-alternatives-verification.sql).
They target the supplied deployed definitions. The migration checks those
definitions for drift and aborts before schema changes if they differ. It is
transactional and leaves existing rows/layouts untouched, rejecting pre-existing
confirmed occupied-period conflicts or inconsistent selections rather than
silently fixing them. There is no automatic legacy layout backfill.

1. Coordinate a pause of writes from this application and other booking/buffer
   clients on the shared development/staging Supabase project. Keep the app
   paused until its matching runtime implementation is ready; the old submission
   code does not send the new required per-booking layout.
2. As `postgres` in Supabase SQL Editor, run the complete migration file from
   `BEGIN` through `COMMIT`, not selected fragments. It preserves existing table
   RLS, adds no role or new reservation status, and does not apply the local test
   fixture to Supabase. If it fails, return the error; the transaction rolls back.
3. Run the complete read-only verification file. Expect a true layout-column
   flag, the confirmed-event unique index, a confirmation RPC, authenticated
   execute true, anonymous execute false, both integration flags true, five
   enabled validation/lock triggers, zero duplicate confirmed events and true
   confirmed occupied-period validation. Empty confirmed schedules validate true.
4. Return the verification result and explicit migration completion. The
   designated shared-change owner then updates the approved database-schema
   document to the verified state. Runtime changes, frontend caller integration
   and their tests resume after this developer execution checkpoint.
5. Do not run the older equipment proposal/status scripts afterwards; they
   overwrite the new venue-aware decision. B1 buffer configuration and the
   existing 30-minute equipment transfer allocator are preserved.

Venue Staff notification routing (AC5) remains an independent existing blocker;
neither migration approval nor these SQL changes provide the missing assignment
relationship or notification permission contract.

### Deployment-role correction

The supplied live error reports `must be owner of function b1_save_venue_buffers`.
The subsequent role query shows `postgres` is a member of the B1 executor role
but does not inherit its privileges. The migration now explicitly tests SET ROLE
before schema changes and replaces that function under its existing owner.
If schema CREATE is absent for the executor, it is granted and revoked within
the same migration transaction, so no schema CREATE grant persists at commit.
Ownership, the save function's execute grants, and membership inheritance remain
unchanged. The postgres-owned availability checker receives only the necessary
EXECUTE privilege on the pure B1 occupied-period calculator; authenticated/anon
calculator privileges are not broadened.

The earlier SQL tests used a superuser and did not establish this deployment-role
path. `tests/test_venue_booking_migration_permissions.sql` adds a non-superuser,
non-inheriting postgres simulation, verifies migration/rerun and permissions,
then exercises real buffer calculation and authenticated confirmation. It is
local-only fixture code and must never be run in Supabase. The application and
live database remain unchanged until the developer reruns the corrected migration
and supplies verification.

### Confirmed buffer configuration for the blocked venue

After the migration reported `B1_CONFIGURATION_REQUIRED`, the supplied read-only
result identified Test Conference Hall with one confirmed booking, null setup
and turnaround values, and revision 0. The developer confirmed 15 minutes before
the event for setup and 15 minutes after it for turnaround. Consecutive events
at that venue therefore need a 30-minute gap between their event periods.

The B1 maintainer must save those values through `b1_save_venue_buffers` using
the established authenticated Venue Staff execution flow, expected revision 0
if still current, and a fresh operation UUID. No arbitrary staff identity is to
be substituted into SQL-editor JWT settings. A normal SQL-editor owner session
does not itself satisfy the function's `auth.uid()`/Venue Staff check. The current
workspace has no B1 buffer-save route/UI, so no such screen is assumed here.
This configuration is confirmed but not applied or verified by this task; it
does not introduce global defaults or overwrite other venues' configuration.

### Hosted Auth-schema compatibility correction

The developer's buffer-save attempt failed during actor initialisation with
`permission denied for schema auth`. The B1 executor cannot call `auth.uid()`
under the supplied hosted permissions. Supabase documents that hosted postgres
cannot necessarily grant USAGE on its managed Auth schema, so expanding managed
schema grants is not the fix used here.

The [standalone B1 patch](../database/venue-buffer-auth-context-patch.sql) changes
only actor initialisation to read the same request settings used by `auth.uid()`:
the individual `request.jwt.claim.sub`, falling back to the JSON claims `sub`.
It retains the nonnull identity and existing Venue Staff role check, function
ownership, execute ACLs, revision/receipt behavior and notification routing.
It adds no identity parameter, role membership, Auth-schema grant or new
authentication method. Owner-role switching and transaction-local schema CREATE
handling are retained. The main migration includes the same correction and
recognises the original, patched and already-migrated definitions.

Execution order for the blocked venue: run the complete standalone patch as
postgres; save the approved 15/15 configuration through the existing B1 function;
run the complete updated alternatives migration; then run verification. An
authorised SQL maintenance transaction may supply the operator's own existing
Venue Staff identity transaction-locally, as described in the conversation; it
must not fabricate a staff identity or claim to be an application login.

Local PostgreSQL checks passed with B1 Auth-schema USAGE explicitly revoked and
the deployment role non-superuser/non-inheriting: standalone patch/rerun, rejection
of missing identity, preserved validation, migration/rerun, owner/ACL preservation,
real buffer save, authenticated confirmation and existing venue/equipment SQL
regressions. These are synthetic tests, not evidence of live deployment.

**Shared Baseline Update Required:** after approval/integration, reconcile
`docs/architecture/project_context.md` from one active arrangement to multiple
non-blocking pending alternatives and one confirmed selection. The designated
shared-change owner must update `docs/architecture/database_schema.md` when the
approved database change is actually applied and verified. No baseline or live
schema documentation is rewritten speculatively here.

## Outstanding Integration Verification

- The implementation uses the confirmed live columns: `booking_id`, `requested_start`, `requested_end`, `requested_by`, `venue_block_id`, `start_datetime`, and `end_datetime`. A live Supabase integration test is still required to verify the deployed schema and policies.
- AC5 remains blocked. The unchanged database has no venue-to-staff assignment relationship, and the current notification RLS policies do not permit a Coordinator to insert notifications. Successful booking responses explicitly report `notification_sent: false` with a warning.
- Atomic confirmation/cancellation, unique confirmed-event selection and validation triggers are now documented and confirmed by the supplied migration verification. Real JWT/browser execution and production-load verification remain outstanding; local concurrent PostgreSQL checks are recorded in the functional specification.
- The Coordinator and Venue Staff interfaces use real role-verified Supabase sessions. The Coordinator flow checks eligible venues, submits requests, and reloads persisted booking status.
- New bookings persist their layout in `venue_booking.setup_layout`; the event-level organiser requirement is preserved. Legacy missing layouts require review rather than fabricated backfill.
- User-entered dates and times are interpreted as Singapore time (`UTC+08:00`) before being written to the `timestamptz` booking and block columns.
- A saved booking reports `notification_sent: false` and a warning. Do not retry the booking itself merely because notification delivery is unavailable.

## Team Status Alignment — 29 October 2026

The team confirmed initial event approval as `approved`, followed by venue and
equipment arrangements, then final event `confirmed`. Venue submission/context
now require an assigned approved event. Earlier planning references in this
inspection history describe the superseded implementation. Alternative booking
statuses, non-blocking behavior, buffers and atomic confirmation are unchanged.
