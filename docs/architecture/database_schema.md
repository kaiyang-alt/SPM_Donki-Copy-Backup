# Supabase Database Reference

Snapshot supplied by the developer: **29 October 2026, 08:24:13 UTC
(16:24:13 Singapore time)**, executed as `postgres`, PostgreSQL **17.6**.
Source: the full result of [current-schema-inspection.sql](../database/current-schema-inspection.sql).
This replaces earlier partial catalogue/RLS descriptions with the observed
`public` schema: **15 tables, 148 columns, 70 constraints, 20 indexes, 77 policies,
32 routines and 22 non-internal triggers**. All 15 tables have RLS enabled;
`venue_buffer_operation` also has forced RLS. No public views or enums were returned.

This is a supplied catalogue snapshot, not a live connection, data-quality audit,
or proof that every application path works. It does not inventory managed
`auth`/`storage` schemas, application rows, sequences, scheduled jobs or external
services. Snapshot metadata describes deployment; approved requirements still
follow [requirement precedence](../requirements/README.md). Repeat the inspection
after database deployments. Do not rerun historical migrations simply to make
this document match the database.

## Team Workflow and Subsequent Functional Confirmation

The developer reported the workflow/status update working and then supplied a
fresh catalogue export. Comparison with the earlier 07:18:33 UTC snapshot
confirms exactly the intended changes: the pending-venue skip in two equipment
functions and planning as an allowed old review state in one audit INSERT policy.
Routine ownership/ACLs, tables, columns, constraints, indexes, triggers and the
remaining policies are unchanged. Both patches are verified in the supplied
08:24:13 UTC export; no further application of them is needed for this database.
Individual negative/concurrency live acceptance results remain separate evidence.

The team contract is:

- Initial Coordinator approval saves event `approved`.
- Venue booking starts only for an assigned `approved` event. Venue Staff confirm
  the selected booking; this does not change the event to `confirmed`.
- Equipment proposals/reservations allow event `approved` or `confirmed`, require
  current organiser agreement for acceptance, and preserve the event status.
- Final Coordinator readiness confirms an `approved` event only after all required
  arrangements pass, saving event `confirmed`.
- Existing `planning` is pre-approval/legacy state, not permission to book resources.
  Existing records are reviewed through the app rather than bulk-reclassified.

No new table, column, status or event backfill is required for this alignment.
The SQL corrections change two equipment function bodies and one existing
Coordinator audit INSERT policy. Keep both patches with the application changes;
merging Git code alone does not apply SQL to another database.

## Deployed Workflow and Remaining Boundaries

| Area | Observed database behavior | Team consequence |
|---|---|---|
| Coordinator assignment | Enabled `trg_event_auto_assign_coordinator` assigns an unassigned submitted (`requested`) event and moves it to `planning`. | Assignment is deployed despite the older assignment story's implementation note. Selection is lowest active workload, then oldest last event creation time (never assigned first), then UUID. This records implementation, not new customer approval of the selection rule. |
| Coordinator review / equipment status | `event` permits both `planning` and `approved`. Equipment proposal creation, acceptance and earlier-request availability filtering use `approved`/`confirmed`. Auto-assignment uses `planning`. | The team confirmed `approved`/`confirmed` for arrangements and final approval. The branch gates and installed review audit patch support this handoff. The developer reports the workflow working; exhaustive live acceptance is not claimed. |
| Venue alternatives | Per-booking `setup_layout`, one-confirmed-per-event index, non-blocking requested/tentative rows and atomic confirmation/sibling cancellation are installed. | Save layout on each new booking; an event-level layout alone does not satisfy the guard. Missing historical layout needs review before confirmation. Different events have independent venue decisions subject to occupied-period conflicts. |
| Earlier equipment proposals | Both availability and acceptance skip earlier pending proposals with no confirmed venue when allocating provisional stock. | The [priority patch](../database/equipment-pending-venue-priority-patch.sql) is verified deployed. The candidate itself still needs a confirmed venue; the existing `approved`/`confirmed` status checks are retained. |
| Equipment operational status | `equipment.operational_status` and its reservation trigger/RPC are installed. | Requested/reserved writes require active equipment with operational status `available`. This is distinct from calculated free quantity. Older local fixtures do not prove this live guard works across every path. |
| B1 buffers | Configured occupied periods, operation receipts, request-claim identity and the shared equipment/venue lock are installed. | Setup/turnaround are per venue, not globally fixed at 15/15. Snapshot has no venue rows, so it does not prove particular configured durations. B1 functions retain their executor owner and narrow ACLs. |
| Change requests | `awaiting_information`, change-request audit/notification links and decision/catalogue/notification RPCs are installed. | Use the documented RPC contracts; do not infer a supported approve/apply action from these decision functions, which implement reject/request-information only. |
| Venue notifications | No venue-to-staff assignment relationship appears in this public schema. | Venue-booking AC5 routing remains unresolved; other notification policies/RPCs do not establish assigned Venue Staff delivery. |

### Observed Workflow Details

- Auto-assignment considers active profiles with `event_coordinator`. Workload
  counts events in `requested`, `changes_requested`, `planning`, `confirmed`;
  it does not count `approved`. No eligible coordinator leaves the event
  `requested` and unassigned. Successful assignment writes notices to organiser
  and coordinator inside the trigger operation. Existing assignments are retained.
- Venue confirmation requires Venue Staff, uses caller RLS and the shared
  `(212,8401)` transaction lock, returns a confirmed retry unchanged and cancels
  only the same event's pending siblings. It does not confirm the event.
  Confirmed occupied periods include setup/turnaround; active blocks also block.
- Equipment offers preserve original requirements, are versioned and need current
  organiser agreement. Final acceptance uses the actual confirmed venue/period,
  maintenance, quantities, provisional priority and cross-venue transfer checks.
  Earlier pending proposals without confirmed venues no longer claim provisional
  stock. Same-venue equipment reuse and venue setup/turnaround are separate constraints.
- `update_equipment_operational_status` checks Technical Support and accepts
  `available`, `damaged`, `under_repair`, `unavailable`. Its body updates the
  catalogue row; it does not itself release reservations or add maintenance rows.
- Change-request decisions require the assigned Coordinator and nonblank
  explanation. They write `rejected` or `awaiting_information` and an audit row;
  notification is a separate, idempotent RPC keyed by change request/type.
  These functions do not automatically rewrite the event's status.

## Table `profile`

### Columns

| Name | Type | Nullability / default |
|---|---|---|
| `user_id` | `uuid` | NOT NULL |
| `name` | `text` | NOT NULL |
| `active` | `boolean` | NOT NULL; DEFAULT `true` |
| `created_at` | `timestamp with time zone` | NOT NULL; DEFAULT `now()` |

### Constraints

| Name | Definition | Validated |
|---|---|---|
| `profiles_pkey` | `PRIMARY KEY (user_id)` | true |
| `profiles_user_id_fkey` | `FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE` | true |


## Table `user_role`

### Columns

| Name | Type | Nullability / default |
|---|---|---|
| `user_id` | `uuid` | NOT NULL |
| `role` | `text` | NOT NULL |

### Constraints

| Name | Definition | Validated |
|---|---|---|
| `user_role_role_check` | `CHECK (role = ANY (ARRAY['event_organiser'::text, 'event_coordinator'::text, 'event_coordinator_lead'::text, 'venue_staff'::text, 'technical_support'::text, 'attendee'::text]))` | true |
| `user_roles_pkey` | `PRIMARY KEY (user_id, role)` | true |
| `user_roles_user_id_fkey` | `FOREIGN KEY (user_id) REFERENCES profile(user_id) ON DELETE CASCADE` | true |


## Table `event`

### Columns

| Name | Type | Nullability / default |
|---|---|---|
| `event_id` | `uuid` | NOT NULL; DEFAULT `gen_random_uuid()` |
| `organiser_id` | `uuid` | NOT NULL |
| `coordinator_id` | `uuid` | Nullable |
| `name` | `text` | Nullable |
| `purpose` | `text` | Nullable |
| `description` | `text` | Nullable |
| `preferred_start_datetime` | `timestamp with time zone` | Nullable |
| `preferred_end_datetime` | `timestamp with time zone` | Nullable |
| `start_datetime` | `timestamp with time zone` | Nullable |
| `end_datetime` | `timestamp with time zone` | Nullable |
| `expected_attendance` | `integer` | Nullable |
| `registration_limit` | `integer` | Nullable |
| `venue_requirements` | `text` | Nullable |
| `accessibility_needs` | `text` | Nullable |
| `layout_requirements` | `text` | Nullable |
| `technical_support_required` | `boolean` | Nullable |
| `technical_requirements` | `text` | Nullable |
| `registration_enabled` | `boolean` | Nullable |
| `registration_open_at` | `timestamp with time zone` | Nullable |
| `registration_close_at` | `timestamp with time zone` | Nullable |
| `status` | `text` | Nullable |
| `created_at` | `timestamp with time zone` | Nullable |
| `updated_at` | `timestamp with time zone` | Nullable |

### Constraints

| Name | Definition | Validated |
|---|---|---|
| `events_coordinator_id_fkey` | `FOREIGN KEY (coordinator_id) REFERENCES profile(user_id)` | true |
| `events_organiser_id_fkey` | `FOREIGN KEY (organiser_id) REFERENCES profile(user_id)` | true |
| `events_pkey` | `PRIMARY KEY (event_id)` | true |
| `events_status_check` | `CHECK (status = ANY (ARRAY['draft'::text, 'requested'::text, 'changes_requested'::text, 'planning'::text, 'approved'::text, 'confirmed'::text, 'completed'::text, 'cancelled'::text, 'withdrawn'::text, 'rejected'::text]))` | true |


## Table `event_action_log`

### Columns

| Name | Type | Nullability / default |
|---|---|---|
| `action_id` | `uuid` | NOT NULL; DEFAULT `gen_random_uuid()` |
| `event_id` | `uuid` | NOT NULL |
| `actor_id` | `uuid` | Nullable |
| `action_type` | `text` | Nullable |
| `details` | `text` | Nullable |
| `old_status` | `text` | Nullable |
| `new_status` | `text` | Nullable |
| `created_at` | `timestamp with time zone` | Nullable |
| `change_request_id` | `uuid` | Nullable |

### Constraints

| Name | Definition | Validated |
|---|---|---|
| `cs_event_action_log_change_request_event_fkey` | `FOREIGN KEY (change_request_id, event_id) REFERENCES event_change_request(change_request_id, event_id)` | true |
| `event_action_logs_actor_id_fkey` | `FOREIGN KEY (actor_id) REFERENCES profile(user_id)` | true |
| `event_action_logs_event_id_fkey` | `FOREIGN KEY (event_id) REFERENCES event(event_id)` | true |
| `event_action_logs_pkey` | `PRIMARY KEY (action_id)` | true |


## Table `event_change_request`

### Columns

| Name | Type | Nullability / default |
|---|---|---|
| `change_request_id` | `uuid` | NOT NULL; DEFAULT `gen_random_uuid()` |
| `event_id` | `uuid` | NOT NULL |
| `requested_by` | `uuid` | NOT NULL |
| `proposed_changes` | `jsonb` | Nullable |
| `reason` | `text` | Nullable |
| `status` | `text` | Nullable |
| `created_at` | `timestamp with time zone` | Nullable |
| `processed_by` | `uuid` | Nullable |
| `processed_at` | `timestamp with time zone` | Nullable |

### Constraints

| Name | Definition | Validated |
|---|---|---|
| `cs_change_request_event_pair_key` | `UNIQUE (change_request_id, event_id)` | true |
| `event_change_requests_event_id_fkey` | `FOREIGN KEY (event_id) REFERENCES event(event_id)` | true |
| `event_change_requests_pkey` | `PRIMARY KEY (change_request_id)` | true |
| `event_change_requests_processed_by_fkey` | `FOREIGN KEY (processed_by) REFERENCES profile(user_id)` | true |
| `event_change_requests_requested_by_fkey` | `FOREIGN KEY (requested_by) REFERENCES profile(user_id)` | true |
| `event_change_requests_status_check` | `CHECK (status = ANY (ARRAY['pending'::text, 'agreed'::text, 'rejected'::text, 'applied'::text, 'cancelled'::text, 'awaiting_information'::text]))` | true |


## Table `event_coordinator_reassignment`

### Columns

| Name | Type | Nullability / default |
|---|---|---|
| `reassignment_id` | `uuid` | NOT NULL; DEFAULT `gen_random_uuid()` |
| `event_id` | `uuid` | NOT NULL |
| `from_coordinator_id` | `uuid` | NOT NULL |
| `to_coordinator_id` | `uuid` | NOT NULL |
| `status` | `text` | Nullable |
| `requested_at` | `timestamp with time zone` | Nullable |
| `responded_at` | `timestamp with time zone` | Nullable |

### Constraints

| Name | Definition | Validated |
|---|---|---|
| `coordinator_reassignments_event_id_fkey` | `FOREIGN KEY (event_id) REFERENCES event(event_id)` | true |
| `coordinator_reassignments_from_coordinator_id_fkey` | `FOREIGN KEY (from_coordinator_id) REFERENCES profile(user_id)` | true |
| `coordinator_reassignments_pkey` | `PRIMARY KEY (reassignment_id)` | true |
| `coordinator_reassignments_status_check` | `CHECK (status = ANY (ARRAY['pending'::text, 'accepted'::text, 'rejected'::text, 'cancelled'::text]))` | true |
| `coordinator_reassignments_to_coordinator_id_fkey` | `FOREIGN KEY (to_coordinator_id) REFERENCES profile(user_id)` | true |


## Table `venue`

### Columns

| Name | Type | Nullability / default |
|---|---|---|
| `venue_id` | `uuid` | NOT NULL; DEFAULT `gen_random_uuid()` |
| `name` | `text` | Nullable |
| `location` | `text` | Nullable |
| `capacity` | `integer` | Nullable |
| `facilities` | `jsonb` | Nullable |
| `accessibility` | `text` | Nullable |
| `supported_layouts` | `jsonb` | Nullable |
| `operating_hours` | `text` | Nullable |
| `active` | `boolean` | Nullable |
| `setup_minutes` | `integer` | Nullable |
| `turnaround_minutes` | `integer` | Nullable |
| `buffer_config_revision` | `bigint` | NOT NULL; DEFAULT `0` |

### Constraints

| Name | Definition | Validated |
|---|---|---|
| `b1_venue_buffer_pair` | `CHECK ((setup_minutes IS NULL) = (turnaround_minutes IS NULL))` | true |
| `b1_venue_buffer_revision_nonnegative` | `CHECK (buffer_config_revision >= 0)` | true |
| `b1_venue_setup_nonnegative` | `CHECK (setup_minutes IS NULL OR setup_minutes >= 0)` | true |
| `b1_venue_turnaround_nonnegative` | `CHECK (turnaround_minutes IS NULL OR turnaround_minutes >= 0)` | true |
| `venues_pkey` | `PRIMARY KEY (venue_id)` | true |

### Venue buffer contract

Setup/turnaround must be both null or both populated. New venues start
unconfigured. `b1_save_venue_buffers` requires Venue Staff request identity,
positive durations, an expected revision and an operation UUID. Zero values need
an explicit B1 decision; null/zero must not be treated as implicit zero buffers.
The save uses the shared lock, revision checks and operation receipts, retaining
arrangements while reporting conflicts and notification-routing limitations.
Occupied periods are `[requested_start - setup, requested_end + turnaround)`.
The save reads existing request claims and remains executor-owned; its owner-only
ACL is recorded below. This snapshot does not assert direct browser access.


## Table `venue_booking`

### Columns

| Name | Type | Nullability / default |
|---|---|---|
| `booking_id` | `uuid` | NOT NULL; DEFAULT `gen_random_uuid()` |
| `venue_id` | `uuid` | NOT NULL |
| `event_id` | `uuid` | NOT NULL |
| `requested_start` | `timestamp with time zone` | Nullable |
| `requested_end` | `timestamp with time zone` | Nullable |
| `status` | `text` | Nullable |
| `requested_by` | `uuid` | NOT NULL |
| `requested_at` | `timestamp with time zone` | Nullable |
| `decided_by` | `uuid` | Nullable |
| `decided_at` | `timestamp with time zone` | Nullable |
| `decision_reason` | `text` | Nullable |
| `setup_layout` | `text` | Nullable |

### Constraints

| Name | Definition | Validated |
|---|---|---|
| `venue_bookings_decided_by_fkey` | `FOREIGN KEY (decided_by) REFERENCES profile(user_id)` | true |
| `venue_bookings_event_id_fkey` | `FOREIGN KEY (event_id) REFERENCES event(event_id)` | true |
| `venue_bookings_pkey` | `PRIMARY KEY (booking_id)` | true |
| `venue_bookings_requested_by_fkey` | `FOREIGN KEY (requested_by) REFERENCES profile(user_id)` | true |
| `venue_bookings_status_check` | `CHECK (status = ANY (ARRAY['requested'::text, 'tentative'::text, 'confirmed'::text, 'rejected'::text, 'cancelled'::text]))` | true |
| `venue_bookings_venue_id_fkey` | `FOREIGN KEY (venue_id) REFERENCES venue(venue_id)` | true |


### Venue alternatives deployment — observed 29 October 2026

The `setup_layout` column above is nullable for legacy rows. New alternatives
require a nonblank per-booking layout; supported-layout validation is also an
application responsibility. The current snapshot confirms the partial index
`cs_venue_one_confirmed_per_event` and enabled venue guards/locks listed below.
Earlier supplied verification reported zero duplicate confirmed events and valid
occupied periods on 28 October; this metadata-only snapshot does not recheck
those data counts.

`confirm_venue_booking(uuid)` uses authenticated caller RLS and checks Venue Staff
membership. It confirms one selection and cancels requested/tentative siblings
atomically, without changing event status. Successful retries return the saved
row. Authenticated EXECUTE is enabled and anonymous EXECUTE is disabled.
`cs_venue_period_available(uuid,timestamptz,timestamptz,uuid)` returns a narrow,
trusted-owner availability decision including setup/turnaround, confirmed
bookings and active blocks. Pending alternatives are non-blocking. Existing RLS
policies still authorise originating writes; the migration adds no table policy.
The shared `(212,8401)` write lock coordinates venue/block/equipment changes.

Equipment validation now uses the single confirmed selection, ignoring pending
venue alternatives, while retaining stock, maintenance, consent and the
30-minute cross-venue equipment transfer rules. Supplied verification confirms
the integration flags, B1 ownership/request-identity handling, and postgres
EXECUTE on the pure buffer calculator required by the trusted checker.

## Table `venue_block`

### Columns

| Name | Type | Nullability / default |
|---|---|---|
| `venue_block_id` | `uuid` | NOT NULL; DEFAULT `gen_random_uuid()` |
| `venue_id` | `uuid` | NOT NULL |
| `start_datetime` | `timestamp with time zone` | Nullable |
| `end_datetime` | `timestamp with time zone` | Nullable |
| `reason` | `text` | Nullable |
| `created_by` | `uuid` | NOT NULL |
| `created_at` | `timestamp with time zone` | Nullable |
| `status` | `text` | Nullable |

### Constraints

| Name | Definition | Validated |
|---|---|---|
| `venue_blocks_created_by_fkey` | `FOREIGN KEY (created_by) REFERENCES profile(user_id)` | true |
| `venue_blocks_pkey` | `PRIMARY KEY (venue_block_id)` | true |
| `venue_blocks_status_check` | `CHECK (status = ANY (ARRAY['active'::text, 'cancelled'::text]))` | true |
| `venue_blocks_venue_id_fkey` | `FOREIGN KEY (venue_id) REFERENCES venue(venue_id)` | true |


## Table `equipment`

### Columns

| Name | Type | Nullability / default |
|---|---|---|
| `equipment_id` | `uuid` | NOT NULL; DEFAULT `gen_random_uuid()` |
| `name` | `text` | Nullable |
| `type` | `text` | Nullable |
| `description` | `text` | Nullable |
| `total_quantity` | `integer` | Nullable |
| `location` | `text` | Nullable |
| `active` | `boolean` | Nullable |
| `operational_status` | `text` | NOT NULL; DEFAULT `'available'::text` |

### Constraints

| Name | Definition | Validated |
|---|---|---|
| `equipment_operational_status_check` | `CHECK (operational_status = ANY (ARRAY['available'::text, 'damaged'::text, 'under_repair'::text, 'unavailable'::text]))` | true |
| `equipment_pkey` | `PRIMARY KEY (equipment_id)` | true |


## Table `equipment_reservation`

### Columns

| Name | Type | Nullability / default |
|---|---|---|
| `reservation_id` | `uuid` | NOT NULL; DEFAULT `gen_random_uuid()` |
| `event_id` | `uuid` | NOT NULL |
| `equipment_id` | `uuid` | NOT NULL |
| `quantity_requested` | `integer` | Nullable |
| `start_datetime` | `timestamp with time zone` | Nullable |
| `end_datetime` | `timestamp with time zone` | Nullable |
| `technical_requirements` | `text` | Nullable |
| `status` | `text` | Nullable |
| `requested_by` | `uuid` | NOT NULL |
| `requested_at` | `timestamp with time zone` | Nullable |
| `decided_by` | `uuid` | Nullable |
| `decided_at` | `timestamp with time zone` | Nullable |
| `decision_reason` | `text` | Nullable |
| `quantity_suggested` | `integer` | Nullable |
| `suggested_by` | `uuid` | Nullable |
| `suggested_at` | `timestamp with time zone` | Nullable |
| `proposal_version` | `bigint` | NOT NULL; DEFAULT `0` |
| `organiser_agreed_version` | `bigint` | Nullable |
| `organiser_agreed_by` | `uuid` | Nullable |
| `organiser_agreed_at` | `timestamp with time zone` | Nullable |

### Constraints

| Name | Definition | Validated |
|---|---|---|
| `cs_equipment_proposal_values` | `CHECK ((quantity_suggested IS NULL OR quantity_suggested > 0) AND proposal_version >= 0 AND (organiser_agreed_version IS NULL AND organiser_agreed_by IS NULL AND organiser_agreed_at IS NULL OR organiser_agreed_version IS NOT NULL AND organiser_agreed_by IS NOT NULL AND organiser_agreed_at IS NOT NULL AND organiser_agreed_version = proposal_version AND proposal_version > 0 AND quantity_suggested IS NOT NULL))` | true |
| `equipment_reservation_organiser_agreed_by_fkey` | `FOREIGN KEY (organiser_agreed_by) REFERENCES profile(user_id)` | true |
| `equipment_reservation_suggested_by_fkey` | `FOREIGN KEY (suggested_by) REFERENCES profile(user_id)` | true |
| `equipment_reservations_decided_by_fkey` | `FOREIGN KEY (decided_by) REFERENCES profile(user_id)` | true |
| `equipment_reservations_equipment_id_fkey` | `FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)` | true |
| `equipment_reservations_event_id_fkey` | `FOREIGN KEY (event_id) REFERENCES event(event_id)` | true |
| `equipment_reservations_pkey` | `PRIMARY KEY (reservation_id)` | true |
| `equipment_reservations_requested_by_fkey` | `FOREIGN KEY (requested_by) REFERENCES profile(user_id)` | true |
| `equipment_reservations_status_check` | `CHECK (status = ANY (ARRAY['requested'::text, 'reserved'::text, 'rejected'::text, 'cancelled'::text]))` | true |


### Equipment proposal deployment — supplied live inspection

The proposal columns and functions are present in this snapshot. The
[proposal migration](../database/equipment-proposals-migration.sql) is a local
deployment artifact, not an exact reconstruction of every later shared change.
See the timestamped deployment differences and subsequent workflow confirmation
above before deployment.

Agreement fields must be all absent or complete/current. Revisions clear them.
Existing `quantity_requested` and original event requirements are preserved;
free text is not parsed into a numeric request. No new status or table is added.

RPCs: `propose_equipment_quantity`, `agree_equipment_proposal`, existing
`accept_equipment_request`, and `cs_equipment_request_available`. RPC calls use
the caller's authenticated role. Narrow read-only schedule validation and the
arrangement-change guard use trusted-owner functions to check hidden venue
commitments without returning other users' booking details; RLS still controls
the originating writes. The allocator is private. Venue/event writes join the
existing equipment advisory-lock protocol.

The [pending-venue priority patch](../database/equipment-pending-venue-priority-patch.sql)
is verified in this snapshot: availability and acceptance skip earlier pending
proposals with no confirmed venue when allocating provisional stock. The
candidate's own venue and all reserved commitments remain fully validated.
Function signatures, owners, ACLs and `approved`/`confirmed` status gates are
unchanged. No reservation or event rows are rewritten by this patch.

The deployed Technical Support requirements policy uses `approved` or
`confirmed` independently of reservation existence. A second policy delegates
to `cs_technical_support_can_view_event`, which checks role and reservation
existence without an event-status filter. As these are permissive policies,
either can expose a row. Organisers may read their own offers and update guarded
agreement fields; catalogue SELECT is limited to offered items for organisers.

For inbox visibility alone, the separate
[inbox SELECT patch](../database/equipment-organiser-inbox-access.sql) updates
only that event SELECT policy and adds no columns or write permissions.

## Table `registration`

### Columns

| Name | Type | Nullability / default |
|---|---|---|
| `registration_id` | `uuid` | NOT NULL; DEFAULT `gen_random_uuid()` |
| `event_id` | `uuid` | NOT NULL |
| `attendee_id` | `uuid` | NOT NULL |
| `registration_type` | `text` | Nullable |
| `status` | `text` | Nullable |
| `registered_at` | `timestamp with time zone` | Nullable |
| `invited_at` | `timestamp with time zone` | Nullable |
| `updated_at` | `timestamp with time zone` | Nullable |

### Constraints

| Name | Definition | Validated |
|---|---|---|
| `registrations_attendee_id_fkey` | `FOREIGN KEY (attendee_id) REFERENCES profile(user_id)` | true |
| `registrations_event_id_attendee_id_key` | `UNIQUE (event_id, attendee_id)` | true |
| `registrations_event_id_fkey` | `FOREIGN KEY (event_id) REFERENCES event(event_id)` | true |
| `registrations_pkey` | `PRIMARY KEY (registration_id)` | true |
| `registrations_registration_type_check` | `CHECK (registration_type = ANY (ARRAY['normal'::text, 'vip'::text]))` | true |
| `registrations_status_check` | `CHECK (status = ANY (ARRAY['registered'::text, 'waitlisted'::text, 'invited'::text, 'withdrawn'::text, 'cancelled'::text]))` | true |


## Table `notification`

### Columns

| Name | Type | Nullability / default |
|---|---|---|
| `notification_id` | `uuid` | NOT NULL; DEFAULT `gen_random_uuid()` |
| `event_id` | `uuid` | Nullable |
| `recipient_id` | `uuid` | NOT NULL |
| `type` | `text` | Nullable |
| `message` | `text` | Nullable |
| `created_at` | `timestamp with time zone` | Nullable |
| `read_at` | `timestamp with time zone` | Nullable |
| `change_request_id` | `uuid` | Nullable |

### Constraints

| Name | Definition | Validated |
|---|---|---|
| `cs_notification_change_request_event_fkey` | `FOREIGN KEY (change_request_id, event_id) REFERENCES event_change_request(change_request_id, event_id)` | true |
| `notifications_event_id_fkey` | `FOREIGN KEY (event_id) REFERENCES event(event_id)` | true |
| `notifications_pkey` | `PRIMARY KEY (notification_id)` | true |
| `notifications_recipient_id_fkey` | `FOREIGN KEY (recipient_id) REFERENCES profile(user_id)` | true |


## Table `equipment_unavailability`

### Columns

| Name | Type | Nullability / default |
|---|---|---|
| `equipment_unavailability_id` | `uuid` | NOT NULL; DEFAULT `gen_random_uuid()` |
| `equipment_id` | `uuid` | NOT NULL |
| `quantity_unavailable` | `integer` | Nullable |
| `start_datetime` | `timestamp with time zone` | Nullable |
| `end_datetime` | `timestamp with time zone` | Nullable |
| `reason` | `text` | Nullable |
| `created_by` | `uuid` | NOT NULL |
| `created_at` | `timestamp with time zone` | Nullable |
| `status` | `text` | Nullable |

### Constraints

| Name | Definition | Validated |
|---|---|---|
| `equipment_unavailability_created_by_fkey` | `FOREIGN KEY (created_by) REFERENCES profile(user_id)` | true |
| `equipment_unavailability_equipment_id_fkey` | `FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)` | true |
| `equipment_unavailability_pkey` | `PRIMARY KEY (equipment_unavailability_id)` | true |
| `equipment_unavailability_status_check` | `CHECK (status = ANY (ARRAY['active'::text, 'cancelled'::text]))` | true |


## Table `venue_buffer_operation`

### Columns

| Name | Type | Nullability / default |
|---|---|---|
| `operation_id` | `uuid` | NOT NULL |
| `actor_id` | `uuid` | NOT NULL |
| `venue_id` | `uuid` | NOT NULL |
| `expected_revision` | `bigint` | NOT NULL |
| `setup_minutes` | `integer` | NOT NULL |
| `turnaround_minutes` | `integer` | NOT NULL |
| `result_revision` | `bigint` | NOT NULL |
| `recorded_at` | `timestamp with time zone` | NOT NULL |
| `outcome` | `jsonb` | NOT NULL |

### Constraints

| Name | Definition | Validated |
|---|---|---|
| `venue_buffer_operation_expected_revision_check` | `CHECK (expected_revision >= 0)` | true |
| `venue_buffer_operation_outcome_check` | `CHECK (jsonb_typeof(outcome) = 'object'::text)` | true |
| `venue_buffer_operation_pkey` | `PRIMARY KEY (operation_id)` | true |
| `venue_buffer_operation_result_revision_check` | `CHECK (result_revision >= 0)` | true |
| `venue_buffer_operation_setup_minutes_check` | `CHECK (setup_minutes >= 0)` | true |
| `venue_buffer_operation_turnaround_minutes_check` | `CHECK (turnaround_minutes >= 0)` | true |

B1 stores immutable operation receipts here for revision checking, safe retries
and notification-routing outcomes. The snapshot defines no foreign keys on
this table; do not infer them from UUID column names. RLS is enabled and forced.

## RLS Policies

The following is the complete supplied `public` policy set. SQL whitespace is
normalized for readability. Every policy is permissive in this snapshot, so
applicable policies combine with OR, not AND. Table/column grants and function
checks also apply; the existence of an RLS policy alone is not an EXECUTE grant.
`—` means that USING/WITH CHECK is absent, not automatically denied.

### `equipment`

| Policy | Command | Roles | USING | WITH CHECK |
|---|---|---|---|---|
| `Coordinators can view equipment` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text))))` | — |
| `Organisers can view offered equipment` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM (equipment_reservation r JOIN event e ON ((e.event_id = r.event_id))) WHERE ((r.equipment_id = equipment.equipment_id) AND (e.organiser_id = auth.uid()))))` | — |
| `Technical support can view equipment` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text))))` | — |

### `equipment_reservation`

| Policy | Command | Roles | USING | WITH CHECK |
|---|---|---|---|---|
| `Coordinators can create own event equipment reservations` | `INSERT` | `authenticated` | — | `((requested_by = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))) AND (EXISTS ( SELECT 1 FROM event WHERE ((event.event_id = equipment_reservation.event_id) AND (event.coordinator_id = auth.uid())))))` |
| `Coordinators can view own event equipment reservations` | `SELECT` | `authenticated` | `((EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))) AND (EXISTS ( SELECT 1 FROM event WHERE ((event.event_id = equipment_reservation.event_id) AND (event.coordinator_id = auth.uid())))))` | — |
| `Organisers can agree own equipment proposals` | `UPDATE` | `authenticated` | `((status = 'requested'::text) AND (EXISTS ( SELECT 1 FROM event e WHERE ((e.event_id = equipment_reservation.event_id) AND (e.organiser_id = auth.uid())))))` | `((status = 'requested'::text) AND (EXISTS ( SELECT 1 FROM event e WHERE ((e.event_id = equipment_reservation.event_id) AND (e.organiser_id = auth.uid())))))` |
| `Organisers can view own equipment proposals` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM event e WHERE ((e.event_id = equipment_reservation.event_id) AND (e.organiser_id = auth.uid()))))` | — |
| `Technical support can create equipment reservations` | `INSERT` | `authenticated` | — | `((requested_by = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text)))))` |
| `Technical support can update equipment reservations` | `UPDATE` | `authenticated` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text))))` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text))))` |
| `Technical support can view equipment reservations` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text))))` | — |

### `equipment_unavailability`

| Policy | Command | Roles | USING | WITH CHECK |
|---|---|---|---|---|
| `Technical support can create equipment unavailability` | `INSERT` | `authenticated` | — | `((created_by = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text)))))` |
| `Technical support can update equipment unavailability` | `UPDATE` | `authenticated` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text))))` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text))))` |
| `Technical support can view equipment unavailability` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text))))` | — |

### `event`

| Policy | Command | Roles | USING | WITH CHECK |
|---|---|---|---|---|
| `Attendees can view confirmed events` | `SELECT` | `authenticated` | `((status = 'confirmed'::text) AND (registration_enabled = true) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'attendee'::text)))))` | — |
| `Coordinator leads can assign requested events` | `UPDATE` | `authenticated` | `((status = 'requested'::text) AND (coordinator_id IS NULL) AND is_event_coordinator_lead())` | `((status = 'requested'::text) AND (coordinator_id IS NOT NULL) AND is_event_coordinator_lead() AND (EXISTS ( SELECT 1 FROM user_role coordinator_role WHERE ((coordinator_role.user_id = event.coordinator_id) AND (coordinator_role.role = 'event_coordinator'::text)))))` |
| `Coordinator leads can reassign events` | `UPDATE` | `authenticated` | `((coordinator_id IS NOT NULL) AND is_event_coordinator_lead())` | `((coordinator_id IS NOT NULL) AND is_event_coordinator_lead() AND (EXISTS ( SELECT 1 FROM user_role coordinator_role WHERE ((coordinator_role.user_id = event.coordinator_id) AND (coordinator_role.role = 'event_coordinator'::text)))))` |
| `Coordinator leads can view active events` | `SELECT` | `authenticated` | `((status = ANY (ARRAY['requested'::text, 'changes_requested'::text, 'planning'::text, 'confirmed'::text])) AND is_event_coordinator_lead())` | — |
| `Coordinator leads can view assigned events` | `SELECT` | `authenticated` | `((coordinator_id IS NOT NULL) AND is_event_coordinator_lead())` | — |
| `Coordinator leads can view requested events` | `SELECT` | `authenticated` | `((status = 'requested'::text) AND is_event_coordinator_lead())` | — |
| `Coordinators can update assigned events` | `UPDATE` | `authenticated` | `((coordinator_id = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))))` | `((coordinator_id = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))))` |
| `Coordinators can view all events` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text))))` | — |
| `Organisers can create own events` | `INSERT` | `authenticated` | — | `((organiser_id = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_organiser'::text)))))` |
| `Organisers can update editable own events` | `UPDATE` | `authenticated` | `((organiser_id = auth.uid()) AND (status = ANY (ARRAY['draft'::text, 'requested'::text, 'changes_requested'::text])) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_organiser'::text)))))` | `((organiser_id = auth.uid()) AND (status = ANY (ARRAY['draft'::text, 'requested'::text, 'changes_requested'::text])) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_organiser'::text)))))` |
| `Organisers can view own events` | `SELECT` | `authenticated` | `(organiser_id = auth.uid())` | — |
| `Technical support can review equipment requirements` | `SELECT` | `authenticated` | `((status = ANY (ARRAY['approved'::text, 'confirmed'::text])) AND ((technical_support_required IS TRUE) OR (NULLIF(btrim(technical_requirements), ''::text) IS NOT NULL)) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text)))))` | — |
| `Technical support can view events with equipment reservations` | `SELECT` | `authenticated` | `cs_technical_support_can_view_event(event_id)` | — |
| `b1_executor_event_lock` | `UPDATE` | `b1_venue_buffer_executor` | `true` | `false` |
| `b1_executor_event_read` | `SELECT` | `b1_venue_buffer_executor` | `true` | — |

### `event_action_log`

| Policy | Command | Roles | USING | WITH CHECK |
|---|---|---|---|---|
| `Assigned coordinators can create review action logs` | `INSERT` | `authenticated` | — | `((actor_id = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))) AND (EXISTS ( SELECT 1 FROM event WHERE ((event.event_id = event_action_log.event_id) AND (event.coordinator_id = auth.uid()) AND (((event_action_log.action_type = 'clarification_requested'::text) AND (event_action_log.old_status = ANY (ARRAY['requested'::text, 'changes_requested'::text, 'planning'::text])) AND (event_action_log.new_status = 'changes_requested'::text) AND (event.status = 'changes_requested'::text)) OR ((event_action_log.action_type = 'event_approved'::text) AND (event_action_log.old_status = ANY (ARRAY['requested'::text, 'changes_requested'::text, 'planning'::text])) AND (event_action_log.new_status = 'approved'::text) AND (event.status = 'approved'::text)) OR ((event_action_log.action_type = 'event_rejected'::text) AND (event_action_log.old_status = ANY (ARRAY['requested'::text, 'changes_requested'::text, 'planning'::text])) AND (event_action_log.new_status = 'rejected'::text) AND (event.status = 'rejected'::text)))))))` |
| `Event participants can record review actions` | `INSERT` | `authenticated` | — | `((actor_id = auth.uid()) AND (((action_type = 'clarification_requested'::text) AND (old_status = ANY (ARRAY['requested'::text, 'changes_requested'::text])) AND (new_status = 'changes_requested'::text) AND (EXISTS ( SELECT 1 FROM event e WHERE ((e.event_id = event_action_log.event_id) AND (e.coordinator_id = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role ur WHERE ((ur.user_id = auth.uid()) AND (ur.role = 'event_coordinator'::text)))))))) OR ((action_type = 'review_completed'::text) AND (old_status = ANY (ARRAY['requested'::text, 'changes_requested'::text])) AND (new_status = 'planning'::text) AND (EXISTS ( SELECT 1 FROM event e WHERE ((e.event_id = event_action_log.event_id) AND (e.coordinator_id = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role ur WHERE ((ur.user_id = auth.uid()) AND (ur.role = 'event_coordinator'::text)))))))) OR ((action_type = 'clarification_provided'::text) AND (old_status = 'changes_requested'::text) AND (new_status = 'changes_requested'::text) AND (EXISTS ( SELECT 1 FROM event e WHERE ((e.event_id = event_action_log.event_id) AND (e.organiser_id = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role ur WHERE ((ur.user_id = auth.uid()) AND (ur.role = 'event_organiser'::text))))))))))` |
| `Event participants can view event action logs` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM event WHERE ((event.event_id = event_action_log.event_id) AND ((event.coordinator_id = auth.uid()) OR (event.organiser_id = auth.uid())))))` | — |
| `Event participants can view review action logs` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM event e WHERE ((e.event_id = event_action_log.event_id) AND ((e.coordinator_id = auth.uid()) OR (e.organiser_id = auth.uid())))))` | — |
| `Organisers can create clarification response logs` | `INSERT` | `authenticated` | — | `((actor_id = auth.uid()) AND (action_type = 'clarification_provided'::text) AND (old_status = 'changes_requested'::text) AND (new_status = 'changes_requested'::text) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_organiser'::text)))) AND (EXISTS ( SELECT 1 FROM event WHERE ((event.event_id = event_action_log.event_id) AND (event.organiser_id = auth.uid()) AND (event.status = 'changes_requested'::text)))))` |

### `event_change_request`

| Policy | Command | Roles | USING | WITH CHECK |
|---|---|---|---|---|
| `Coordinators can view assigned event change requests` | `SELECT` | `authenticated` | `((EXISTS ( SELECT 1 FROM event WHERE ((event.event_id = event_change_request.event_id) AND (event.coordinator_id = auth.uid())))) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))))` | — |
| `Organisers can create own event change requests` | `INSERT` | `authenticated` | — | `((requested_by = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_organiser'::text)))) AND (EXISTS ( SELECT 1 FROM event WHERE ((event.event_id = event_change_request.event_id) AND (event.organiser_id = auth.uid())))))` |
| `Organisers can view own event change requests` | `SELECT` | `authenticated` | `((requested_by = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_organiser'::text)))))` | — |

### `event_coordinator_reassignment`

| Policy | Command | Roles | USING | WITH CHECK |
|---|---|---|---|---|
| `Current coordinators can create reassignments` | `INSERT` | `authenticated` | — | `((from_coordinator_id = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))) AND (EXISTS ( SELECT 1 FROM event WHERE ((event.event_id = event_coordinator_reassignment.event_id) AND (event.coordinator_id = auth.uid())))))` |
| `Current coordinators can view outgoing reassignments` | `SELECT` | `authenticated` | `((from_coordinator_id = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))))` | — |
| `Proposed coordinators can respond to reassignments` | `UPDATE` | `authenticated` | `((to_coordinator_id = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))))` | `((to_coordinator_id = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))))` |
| `Proposed coordinators can view incoming reassignments` | `SELECT` | `authenticated` | `((to_coordinator_id = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))))` | — |

### `notification`

| Policy | Command | Roles | USING | WITH CHECK |
|---|---|---|---|---|
| `Assigned coordinators can notify event organisers` | `INSERT` | `authenticated` | — | `((EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))) AND (EXISTS ( SELECT 1 FROM event WHERE ((event.event_id = notification.event_id) AND (event.coordinator_id = auth.uid()) AND (event.organiser_id = notification.recipient_id) AND (((notification.type = 'clarification_requested'::text) AND (event.status = 'changes_requested'::text)) OR ((notification.type = 'event_approved'::text) AND (event.status = 'approved'::text)) OR ((notification.type = 'event_rejected'::text) AND (event.status = 'rejected'::text)))))))` |
| `Coordinator leads can create assignment notifications` | `INSERT` | `authenticated` | — | `((type = 'coordinator_assigned'::text) AND is_event_coordinator_lead() AND (EXISTS ( SELECT 1 FROM event assigned_event WHERE ((assigned_event.event_id = notification.event_id) AND (assigned_event.status = 'requested'::text) AND ((notification.recipient_id = assigned_event.organiser_id) OR (notification.recipient_id = assigned_event.coordinator_id))))))` |
| `Coordinator leads can create reassignment notifications` | `INSERT` | `authenticated` | — | `((type = 'coordinator_reassigned'::text) AND is_event_coordinator_lead() AND (EXISTS ( SELECT 1 FROM event reassigned_event WHERE ((reassigned_event.event_id = notification.event_id) AND ((notification.recipient_id = reassigned_event.organiser_id) OR (EXISTS ( SELECT 1 FROM user_role coordinator_role WHERE ((coordinator_role.user_id = notification.recipient_id) AND (coordinator_role.role = 'event_coordinator'::text)))))))))` |
| `Event participants can create review notifications` | `INSERT` | `authenticated` | — | `(((type = 'clarification_requested'::text) AND (EXISTS ( SELECT 1 FROM event e WHERE ((e.event_id = notification.event_id) AND (e.coordinator_id = auth.uid()) AND (e.organiser_id = notification.recipient_id) AND (EXISTS ( SELECT 1 FROM user_role ur WHERE ((ur.user_id = auth.uid()) AND (ur.role = 'event_coordinator'::text)))))))) OR ((type = 'clarification_provided'::text) AND (EXISTS ( SELECT 1 FROM event e WHERE ((e.event_id = notification.event_id) AND (e.organiser_id = auth.uid()) AND (e.coordinator_id = notification.recipient_id) AND (EXISTS ( SELECT 1 FROM user_role ur WHERE ((ur.user_id = auth.uid()) AND (ur.role = 'event_organiser'::text)))))))))` |
| `Organisers can notify coordinators of clarification` | `INSERT` | `authenticated` | — | `((type = 'clarification_provided'::text) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_organiser'::text)))) AND (EXISTS ( SELECT 1 FROM event WHERE ((event.event_id = notification.event_id) AND (event.organiser_id = auth.uid()) AND (event.coordinator_id = notification.recipient_id) AND (event.status = 'changes_requested'::text)))))` |
| `Review notification senders can view sent notifications` | `SELECT` | `authenticated` | `(((type = ANY (ARRAY['clarification_requested'::text, 'event_approved'::text, 'event_rejected'::text])) AND (EXISTS ( SELECT 1 FROM event e WHERE ((e.event_id = notification.event_id) AND (e.coordinator_id = auth.uid()) AND (e.organiser_id = notification.recipient_id))))) OR ((type = 'clarification_provided'::text) AND (EXISTS ( SELECT 1 FROM event e WHERE ((e.event_id = notification.event_id) AND (e.organiser_id = auth.uid()) AND (e.coordinator_id = notification.recipient_id))))))` | — |
| `Users can update own notifications` | `UPDATE` | `authenticated` | `(recipient_id = auth.uid())` | `(recipient_id = auth.uid())` |
| `Users can view own notifications` | `SELECT` | `authenticated` | `(recipient_id = auth.uid())` | — |
| `b1_executor_notice_insert` | `INSERT` | `b1_venue_buffer_executor` | — | `((type = 'venue_buffer_conflict'::text) AND (event_id IS NOT NULL) AND (recipient_id IS NOT NULL) AND (read_at IS NULL))` |

### `profile`

| Policy | Command | Roles | USING | WITH CHECK |
|---|---|---|---|---|
| `Coordinator leads can view coordinator profiles` | `SELECT` | `authenticated` | `(is_event_coordinator_lead() AND (EXISTS ( SELECT 1 FROM user_role coordinator_role WHERE ((coordinator_role.user_id = profile.user_id) AND (coordinator_role.role = 'event_coordinator'::text)))))` | — |
| `Organisers can view assigned coordinator profiles` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM event WHERE ((event.coordinator_id = profile.user_id) AND (event.organiser_id = auth.uid()))))` | — |
| `Users can view own profile` | `SELECT` | `authenticated` | `(user_id = auth.uid())` | — |

### `registration`

| Policy | Command | Roles | USING | WITH CHECK |
|---|---|---|---|---|
| `Attendees can view own registrations` | `SELECT` | `authenticated` | `(attendee_id = auth.uid())` | — |
| `Coordinators can view registrations for assigned events` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM event WHERE ((event.event_id = registration.event_id) AND (event.coordinator_id = auth.uid()))))` | — |
| `Organisers can view registrations for own events` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM event WHERE ((event.event_id = registration.event_id) AND (event.organiser_id = auth.uid()))))` | — |

### `user_role`

| Policy | Command | Roles | USING | WITH CHECK |
|---|---|---|---|---|
| `Coordinator leads can view coordinator roles` | `SELECT` | `authenticated` | `((role = 'event_coordinator'::text) AND is_event_coordinator_lead())` | — |
| `Users can view own roles` | `SELECT` | `authenticated` | `(user_id = auth.uid())` | — |
| `b1_executor_role_read` | `SELECT` | `b1_venue_buffer_executor` | `true` | — |

### `venue`

| Policy | Command | Roles | USING | WITH CHECK |
|---|---|---|---|---|
| `Coordinators can view venues` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text))))` | — |
| `Technical support can view venues for supported events` | `SELECT` | `authenticated` | `((EXISTS ( SELECT 1 FROM user_role ur WHERE ((ur.user_id = auth.uid()) AND (ur.role = 'technical_support'::text)))) AND (EXISTS ( SELECT 1 FROM (venue_booking vb JOIN equipment_reservation er ON ((er.event_id = vb.event_id))) WHERE (vb.venue_id = venue.venue_id))))` | — |
| `Venue staff can update venues` | `UPDATE` | `authenticated` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` |
| `Venue staff can view venues` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` | — |
| `b1_executor_venue_read` | `SELECT` | `b1_venue_buffer_executor` | `true` | — |
| `b1_executor_venue_write` | `UPDATE` | `b1_venue_buffer_executor` | `true` | `true` |

### `venue_block`

| Policy | Command | Roles | USING | WITH CHECK |
|---|---|---|---|---|
| `Coordinators can view venue blocks` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text))))` | — |
| `Venue staff can create venue blocks` | `INSERT` | `authenticated` | — | `((created_by = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text)))))` |
| `Venue staff can update venue blocks` | `UPDATE` | `authenticated` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` |
| `Venue staff can view venue blocks` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` | — |
| `b1_executor_block_read` | `SELECT` | `b1_venue_buffer_executor` | `true` | — |

### `venue_booking`

| Policy | Command | Roles | USING | WITH CHECK |
|---|---|---|---|---|
| `Coordinators can create venue bookings` | `INSERT` | `authenticated` | — | `((requested_by = auth.uid()) AND (EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))) AND (EXISTS ( SELECT 1 FROM event WHERE ((event.event_id = venue_booking.event_id) AND (event.coordinator_id = auth.uid())))))` |
| `Coordinators can view venue bookings` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text))))` | — |
| `Technical support can view bookings for supported events` | `SELECT` | `authenticated` | `((EXISTS ( SELECT 1 FROM user_role ur WHERE ((ur.user_id = auth.uid()) AND (ur.role = 'technical_support'::text)))) AND (EXISTS ( SELECT 1 FROM equipment_reservation er WHERE (er.event_id = venue_booking.event_id))))` | — |
| `Venue staff can update venue bookings` | `UPDATE` | `authenticated` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` |
| `Venue staff can view venue bookings` | `SELECT` | `authenticated` | `(EXISTS ( SELECT 1 FROM user_role WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` | — |
| `b1_executor_booking_read` | `SELECT` | `b1_venue_buffer_executor` | `true` | — |

### `venue_buffer_operation`

| Policy | Command | Roles | USING | WITH CHECK |
|---|---|---|---|---|
| `b1_executor_receipt_insert` | `INSERT` | `b1_venue_buffer_executor` | — | `true` |
| `b1_executor_receipt_read` | `SELECT` | `b1_venue_buffer_executor` | `true` | — |

## Indexes

Includes primary/unique indexes and partial indexes. All 20 are valid in the
supplied snapshot. A partial unique index is not listed as a CHECK constraint.

| Table | Index | Definition |
|---|---|---|
| `equipment` | `equipment_pkey` | `CREATE UNIQUE INDEX equipment_pkey ON public.equipment USING btree (equipment_id)` |
| `equipment_reservation` | `equipment_reservations_pkey` | `CREATE UNIQUE INDEX equipment_reservations_pkey ON public.equipment_reservation USING btree (reservation_id)` |
| `equipment_unavailability` | `equipment_unavailability_pkey` | `CREATE UNIQUE INDEX equipment_unavailability_pkey ON public.equipment_unavailability USING btree (equipment_unavailability_id)` |
| `event` | `events_pkey` | `CREATE UNIQUE INDEX events_pkey ON public.event USING btree (event_id)` |
| `event_action_log` | `event_action_logs_pkey` | `CREATE UNIQUE INDEX event_action_logs_pkey ON public.event_action_log USING btree (action_id)` |
| `event_change_request` | `cs_change_request_event_pair_key` | `CREATE UNIQUE INDEX cs_change_request_event_pair_key ON public.event_change_request USING btree (change_request_id, event_id)` |
| `event_change_request` | `event_change_requests_pkey` | `CREATE UNIQUE INDEX event_change_requests_pkey ON public.event_change_request USING btree (change_request_id)` |
| `event_coordinator_reassignment` | `coordinator_reassignments_pkey` | `CREATE UNIQUE INDEX coordinator_reassignments_pkey ON public.event_coordinator_reassignment USING btree (reassignment_id)` |
| `notification` | `cs_notification_change_request_type_key` | `CREATE UNIQUE INDEX cs_notification_change_request_type_key ON public.notification USING btree (change_request_id, type) WHERE (change_request_id IS NOT NULL)` |
| `notification` | `notifications_pkey` | `CREATE UNIQUE INDEX notifications_pkey ON public.notification USING btree (notification_id)` |
| `profile` | `profiles_pkey` | `CREATE UNIQUE INDEX profiles_pkey ON public.profile USING btree (user_id)` |
| `registration` | `registrations_event_id_attendee_id_key` | `CREATE UNIQUE INDEX registrations_event_id_attendee_id_key ON public.registration USING btree (event_id, attendee_id)` |
| `registration` | `registrations_pkey` | `CREATE UNIQUE INDEX registrations_pkey ON public.registration USING btree (registration_id)` |
| `user_role` | `user_roles_pkey` | `CREATE UNIQUE INDEX user_roles_pkey ON public.user_role USING btree (user_id, role)` |
| `venue` | `venues_pkey` | `CREATE UNIQUE INDEX venues_pkey ON public.venue USING btree (venue_id)` |
| `venue_block` | `venue_blocks_pkey` | `CREATE UNIQUE INDEX venue_blocks_pkey ON public.venue_block USING btree (venue_block_id)` |
| `venue_booking` | `cs_venue_one_confirmed_per_event` | `CREATE UNIQUE INDEX cs_venue_one_confirmed_per_event ON public.venue_booking USING btree (event_id) WHERE (status = 'confirmed'::text)` |
| `venue_booking` | `venue_bookings_pkey` | `CREATE UNIQUE INDEX venue_bookings_pkey ON public.venue_booking USING btree (booking_id)` |
| `venue_buffer_operation` | `b1_venue_buffer_operation_venue_time_idx` | `CREATE INDEX b1_venue_buffer_operation_venue_time_idx ON public.venue_buffer_operation USING btree (venue_id, recorded_at, operation_id)` |
| `venue_buffer_operation` | `venue_buffer_operation_pkey` | `CREATE UNIQUE INDEX venue_buffer_operation_pkey ON public.venue_buffer_operation USING btree (operation_id)` |

## Triggers

All 22 non-internal triggers were enabled for normal/origin sessions (`O`).
Definitions below show timing, events, row/statement scope and WHEN conditions.

| Table | Trigger | Definition |
|---|---|---|
| `equipment` | `cs_equipment_catalogue_capacity` | `CREATE TRIGGER cs_equipment_catalogue_capacity AFTER INSERT OR UPDATE ON equipment FOR EACH ROW EXECUTE FUNCTION cs_equipment_capacity_guard()` |
| `equipment` | `cs_equipment_catalogue_lock` | `CREATE TRIGGER cs_equipment_catalogue_lock BEFORE INSERT OR DELETE OR UPDATE ON equipment FOR EACH STATEMENT EXECUTE FUNCTION cs_equipment_write_lock()` |
| `equipment_reservation` | `cs_equipment_acceptance_check` | `CREATE TRIGGER cs_equipment_acceptance_check BEFORE INSERT OR UPDATE ON equipment_reservation FOR EACH ROW EXECUTE FUNCTION cs_equipment_acceptance_guard()` |
| `equipment_reservation` | `cs_equipment_operational_status_guard` | `CREATE TRIGGER cs_equipment_operational_status_guard BEFORE INSERT OR UPDATE OF equipment_id, status, quantity_suggested, start_datetime, end_datetime ON equipment_reservation FOR EACH ROW EXECUTE FUNCTION cs_equipment_operational_status_guard()` |
| `equipment_reservation` | `cs_equipment_proposal_check` | `CREATE TRIGGER cs_equipment_proposal_check BEFORE INSERT OR UPDATE ON equipment_reservation FOR EACH ROW EXECUTE FUNCTION cs_equipment_proposal_guard()` |
| `equipment_reservation` | `cs_equipment_reservation_capacity` | `CREATE TRIGGER cs_equipment_reservation_capacity AFTER INSERT OR UPDATE ON equipment_reservation FOR EACH ROW EXECUTE FUNCTION cs_equipment_capacity_guard()` |
| `equipment_reservation` | `cs_equipment_reservation_lock` | `CREATE TRIGGER cs_equipment_reservation_lock BEFORE INSERT OR DELETE OR UPDATE ON equipment_reservation FOR EACH STATEMENT EXECUTE FUNCTION cs_equipment_write_lock()` |
| `equipment_unavailability` | `cs_equipment_unavailability_capacity` | `CREATE TRIGGER cs_equipment_unavailability_capacity AFTER INSERT OR UPDATE ON equipment_unavailability FOR EACH ROW EXECUTE FUNCTION cs_equipment_capacity_guard()` |
| `equipment_unavailability` | `cs_equipment_unavailability_lock` | `CREATE TRIGGER cs_equipment_unavailability_lock BEFORE INSERT OR DELETE OR UPDATE ON equipment_unavailability FOR EACH STATEMENT EXECUTE FUNCTION cs_equipment_write_lock()` |
| `event` | `cs_equipment_event_check` | `CREATE TRIGGER cs_equipment_event_check AFTER INSERT OR DELETE OR UPDATE ON event FOR EACH ROW EXECUTE FUNCTION cs_equipment_arrangement_guard()` |
| `event` | `cs_equipment_event_lock` | `CREATE TRIGGER cs_equipment_event_lock BEFORE INSERT OR DELETE OR UPDATE ON event FOR EACH STATEMENT EXECUTE FUNCTION cs_equipment_write_lock()` |
| `event` | `trg_event_auto_assign_coordinator` | `CREATE TRIGGER trg_event_auto_assign_coordinator AFTER INSERT OR UPDATE OF status ON event FOR EACH ROW WHEN (new.status = 'requested'::text AND new.coordinator_id IS NULL) EXECUTE FUNCTION auto_assign_event_coordinator()` |
| `venue` | `b1_guard_venue_buffer_rows` | `CREATE TRIGGER b1_guard_venue_buffer_rows AFTER INSERT OR UPDATE ON venue FOR EACH ROW EXECUTE FUNCTION b1_guard_venue_buffers()` |
| `venue` | `cs_equipment_venue_check` | `CREATE TRIGGER cs_equipment_venue_check AFTER INSERT OR DELETE OR UPDATE ON venue FOR EACH ROW EXECUTE FUNCTION cs_equipment_arrangement_guard()` |
| `venue` | `cs_equipment_venue_lock` | `CREATE TRIGGER cs_equipment_venue_lock BEFORE INSERT OR DELETE OR UPDATE ON venue FOR EACH STATEMENT EXECUTE FUNCTION cs_equipment_write_lock()` |
| `venue_block` | `cs_equipment_venue_block_check` | `CREATE TRIGGER cs_equipment_venue_block_check AFTER INSERT OR DELETE OR UPDATE ON venue_block FOR EACH ROW EXECUTE FUNCTION cs_equipment_arrangement_guard()` |
| `venue_block` | `cs_equipment_venue_block_lock` | `CREATE TRIGGER cs_equipment_venue_block_lock BEFORE INSERT OR DELETE OR UPDATE ON venue_block FOR EACH STATEMENT EXECUTE FUNCTION cs_equipment_write_lock()` |
| `venue_block` | `cs_venue_block_validate` | `CREATE TRIGGER cs_venue_block_validate BEFORE INSERT OR UPDATE ON venue_block FOR EACH ROW EXECUTE FUNCTION cs_venue_block_guard()` |
| `venue_booking` | `cs_equipment_booking_check` | `CREATE TRIGGER cs_equipment_booking_check AFTER INSERT OR DELETE OR UPDATE ON venue_booking FOR EACH ROW EXECUTE FUNCTION cs_equipment_arrangement_guard()` |
| `venue_booking` | `cs_equipment_booking_lock` | `CREATE TRIGGER cs_equipment_booking_lock BEFORE INSERT OR DELETE OR UPDATE ON venue_booking FOR EACH STATEMENT EXECUTE FUNCTION cs_equipment_write_lock()` |
| `venue_booking` | `cs_venue_booking_cancel` | `CREATE TRIGGER cs_venue_booking_cancel AFTER INSERT OR UPDATE OF status ON venue_booking FOR EACH ROW EXECUTE FUNCTION cs_venue_cancel_alternatives()` |
| `venue_booking` | `cs_venue_booking_validate` | `CREATE TRIGGER cs_venue_booking_validate BEFORE INSERT OR UPDATE ON venue_booking FOR EACH ROW EXECUTE FUNCTION cs_venue_booking_guard()` |

## Routine Signatures, Ownership and Execution

These are deployed routines, including trigger helpers; this list does not make
every function a supported UI API. `DEFINER` executes with the owner privileges;
`INVOKER` uses the caller. Internal role/ownership checks still matter. Function
ACL `X` means EXECUTE; the grantor appears after `/`. No function body is copied
into this document as executable migration code.

| Signature | Owner | Security | Settings | ACL |
|---|---|---|---|---|
| `accept_equipment_request(uuid)` | `postgres` | INVOKER | `search_path=pg_catalog, public` | `{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `agree_equipment_proposal(uuid,bigint)` | `postgres` | INVOKER | `search_path=pg_catalog, public` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `auto_assign_event_coordinator()` | `postgres` | DEFINER | `search_path=public` | `{postgres=X/postgres,service_role=X/postgres}` |
| `b1_buffer_conflicts(uuid,integer,integer)` | `b1_venue_buffer_executor` | INVOKER | `search_path=pg_catalog, pg_temp; TimeZone=UTC` | `{b1_venue_buffer_executor=X/b1_venue_buffer_executor,postgres=X/b1_venue_buffer_executor}` |
| `b1_get_venue_buffer_operation(uuid,uuid)` | `b1_venue_buffer_executor` | DEFINER | `search_path=pg_catalog, pg_temp; TimeZone=UTC` | `{b1_venue_buffer_executor=X/b1_venue_buffer_executor}` |
| `b1_guard_venue_buffers()` | `b1_venue_buffer_executor` | INVOKER | `search_path=pg_catalog, pg_temp` | `{b1_venue_buffer_executor=X/b1_venue_buffer_executor}` |
| `b1_list_venue_buffer_routing_exceptions(uuid)` | `b1_venue_buffer_executor` | DEFINER | `search_path=pg_catalog, pg_temp; TimeZone=UTC` | `{b1_venue_buffer_executor=X/b1_venue_buffer_executor}` |
| `b1_occupied_period(timestamp with time zone,timestamp with time zone,integer,integer)` | `b1_venue_buffer_executor` | INVOKER | `search_path=pg_catalog, pg_temp; TimeZone=UTC` | `{b1_venue_buffer_executor=X/b1_venue_buffer_executor,postgres=X/b1_venue_buffer_executor}` |
| `b1_save_venue_buffers(uuid,integer,integer,bigint,uuid)` | `b1_venue_buffer_executor` | DEFINER | `search_path=pg_catalog, pg_temp; TimeZone=UTC` | `{b1_venue_buffer_executor=X/b1_venue_buffer_executor}` |
| `confirm_venue_booking(uuid)` | `postgres` | INVOKER | `search_path=pg_catalog, public` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `cs_equipment_acceptance_guard()` | `postgres` | INVOKER | `search_path=pg_catalog, public` | `{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `cs_equipment_arrangement_guard()` | `postgres` | DEFINER | `search_path=pg_catalog, public` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `cs_equipment_capacity_guard()` | `postgres` | INVOKER | `search_path=pg_catalog, public` | `{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `cs_equipment_fit_tasks(jsonb,integer,jsonb,integer)` | `postgres` | INVOKER | `search_path=pg_catalog, public` | `{postgres=X/postgres,service_role=X/postgres}` |
| `cs_equipment_free_quantity(uuid,timestamp with time zone,timestamp with time zone,jsonb)` | `postgres` | INVOKER | `search_path=pg_catalog, public` | `{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `cs_equipment_operational_status_guard()` | `postgres` | DEFINER | `search_path=pg_catalog, public` | `{postgres=X/postgres,service_role=X/postgres}` |
| `cs_equipment_proposal_guard()` | `postgres` | INVOKER | `search_path=pg_catalog, public` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `cs_equipment_request_available(uuid)` | `postgres` | INVOKER | `search_path=pg_catalog, public` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `cs_equipment_schedule_fits(uuid,jsonb)` | `postgres` | DEFINER | `search_path=pg_catalog, public` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `cs_equipment_write_lock()` | `postgres` | INVOKER | `search_path=pg_catalog, public` | `{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `cs_technical_support_can_view_event(uuid)` | `postgres` | DEFINER | `search_path=""; row_security=off` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `cs_venue_block_guard()` | `postgres` | DEFINER | `search_path=pg_catalog, public` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `cs_venue_booking_guard()` | `postgres` | INVOKER | `search_path=pg_catalog, public` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `cs_venue_cancel_alternatives()` | `postgres` | INVOKER | `search_path=pg_catalog, public` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `cs_venue_period_available(uuid,timestamp with time zone,timestamp with time zone,uuid)` | `postgres` | DEFINER | `search_path=pg_catalog, public` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `decide_event_change_request(uuid,text,text)` | `postgres` | DEFINER | `search_path=""; row_security=off` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `get_event_change_request_catalog()` | `postgres` | DEFINER | `search_path=""; row_security=off` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `get_event_change_request_decision(uuid)` | `postgres` | DEFINER | `search_path=""; row_security=off` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `is_event_coordinator_lead()` | `postgres` | DEFINER | `search_path=""` | `{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `notify_event_change_request_decision(uuid)` | `postgres` | DEFINER | `search_path=""; row_security=off` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `propose_equipment_quantity(uuid,uuid,integer,timestamp with time zone,timestamp with time zone,uuid,bigint)` | `postgres` | INVOKER | `search_path=pg_catalog, public` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `update_equipment_operational_status(uuid,text)` | `postgres` | DEFINER | `search_path=pg_catalog, public` | `{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |

Some equipment functions, including `accept_equipment_request`, have an `anon`
EXECUTE grant in this snapshot. Their internal authentication/role checks still
reject anonymous acceptance; do not describe their ACL as authenticated-only.
`confirm_venue_booking` has no anonymous EXECUTE grant. The B1 save/get/list
functions have owner-only ACLs here; Venue Staff role membership alone does not
give the browser direct EXECUTE access. Existing controlled deployment/maintenance
steps are distinct from an authenticated application RPC.

## Table, Column and Schema Grants

All listed tables are postgres-owned with RLS enabled. Forced RLS applies to
`venue_buffer_operation`; the other 14 tables do not force RLS. Owner and
BYPASSRLS execution must not be confused with authenticated-user policy tests.
ACL codes: `a` INSERT, `r` SELECT, `w` UPDATE, `d` DELETE, `D` TRUNCATE,
`x` REFERENCES, `t` TRIGGER, `m` MAINTAIN; schema `U` USAGE, `C` CREATE.
An empty grantee before `=` represents PUBLIC. Broad grants do not themselves
bypass RLS, but must be considered alongside policies and function ownership.

| Table | ACL |
|---|---|
| `equipment` | `{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}` |
| `equipment_reservation` | `{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}` |
| `equipment_unavailability` | `{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}` |
| `event` | `{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}` |
| `event_action_log` | `{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}` |
| `event_change_request` | `{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}` |
| `event_coordinator_reassignment` | `{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}` |
| `notification` | `{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}` |
| `profile` | `{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}` |
| `registration` | `{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}` |
| `user_role` | `{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}` |
| `venue` | `{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}` |
| `venue_block` | `{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}` |
| `venue_booking` | `{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}` |
| `venue_buffer_operation` | `{postgres=arwdDxtm/postgres,b1_venue_buffer_executor=ar/postgres}` |

### Explicit column grants

| Table | Column | ACL |
|---|---|---|
| `event` | `event_id` | `{b1_venue_buffer_executor=r/postgres}` |
| `event` | `coordinator_id` | `{b1_venue_buffer_executor=rw/postgres}` |
| `notification` | `notification_id` | `{b1_venue_buffer_executor=a/postgres}` |
| `notification` | `event_id` | `{b1_venue_buffer_executor=a/postgres}` |
| `notification` | `recipient_id` | `{b1_venue_buffer_executor=a/postgres}` |
| `notification` | `type` | `{b1_venue_buffer_executor=a/postgres}` |
| `notification` | `message` | `{b1_venue_buffer_executor=a/postgres}` |
| `notification` | `created_at` | `{b1_venue_buffer_executor=a/postgres}` |
| `notification` | `read_at` | `{b1_venue_buffer_executor=a/postgres}` |
| `user_role` | `user_id` | `{b1_venue_buffer_executor=r/postgres}` |
| `user_role` | `role` | `{b1_venue_buffer_executor=r/postgres}` |
| `venue` | `venue_id` | `{b1_venue_buffer_executor=r/postgres}` |
| `venue` | `setup_minutes` | `{b1_venue_buffer_executor=rw/postgres}` |
| `venue` | `turnaround_minutes` | `{b1_venue_buffer_executor=rw/postgres}` |
| `venue` | `buffer_config_revision` | `{b1_venue_buffer_executor=rw/postgres}` |
| `venue_block` | `venue_block_id` | `{b1_venue_buffer_executor=r/postgres}` |
| `venue_block` | `venue_id` | `{b1_venue_buffer_executor=r/postgres}` |
| `venue_block` | `start_datetime` | `{b1_venue_buffer_executor=r/postgres}` |
| `venue_block` | `end_datetime` | `{b1_venue_buffer_executor=r/postgres}` |
| `venue_block` | `status` | `{b1_venue_buffer_executor=r/postgres}` |
| `venue_booking` | `booking_id` | `{b1_venue_buffer_executor=r/postgres}` |
| `venue_booking` | `venue_id` | `{b1_venue_buffer_executor=r/postgres}` |
| `venue_booking` | `event_id` | `{b1_venue_buffer_executor=r/postgres}` |
| `venue_booking` | `requested_start` | `{b1_venue_buffer_executor=r/postgres}` |
| `venue_booking` | `requested_end` | `{b1_venue_buffer_executor=r/postgres}` |
| `venue_booking` | `status` | `{b1_venue_buffer_executor=r/postgres}` |

Public-schema ACL: `{pg_database_owner=UC/pg_database_owner,=U/pg_database_owner,postgres=U/pg_database_owner,anon=U/pg_database_owner,authenticated=U/pg_database_owner,service_role=U/pg_database_owner,b1_venue_buffer_executor=U/pg_database_owner}`.

### Default privileges

These affect future objects created by the named owner, not only objects in this
snapshot. `r` means relations, `f` routines and `S` sequences in this table.

| Owner | Schema | Object type | ACL |
|---|---|---|---|
| `supabase_admin` | `public` | `S` | `{postgres=rwU/supabase_admin,anon=rwU/supabase_admin,authenticated=rwU/supabase_admin,service_role=rwU/supabase_admin}` |
| `supabase_admin` | `public` | `f` | `{postgres=X/supabase_admin,anon=X/supabase_admin,authenticated=X/supabase_admin,service_role=X/supabase_admin}` |
| `supabase_admin` | `public` | `r` | `{postgres=arwdDxtm/supabase_admin,anon=arwdDxtm/supabase_admin,authenticated=arwdDxtm/supabase_admin,service_role=arwdDxtm/supabase_admin}` |
| `postgres` | `public` | `S` | `{postgres=rwU/postgres,anon=rwU/postgres,authenticated=rwU/postgres,service_role=rwU/postgres}` |
| `postgres` | `public` | `f` | `{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}` |
| `postgres` | `public` | `r` | `{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}` |

## Relevant Database Roles and Memberships

Database roles below are separate from business-role values stored in
`public.user_role`. Membership rows are as exported, including multiple grants
for the same role/member; they must not be collapsed into an assumed INHERIT/SET
result. The inspection query does not export grantor identity.

| Database role | Inherits | BYPASSRLS | Can log in |
|---|---|---|---|
| `anon` | true | false | false |
| `authenticated` | true | false | false |
| `b1_venue_buffer_executor` | false | false | false |
| `postgres` | true | true | true |
| `service_role` | true | true | false |

| Role | Member | Admin option | Inherit option | SET option |
|---|---|---|---|---|
| `pg_monitor` | `postgres` | true | true | true |
| `pg_signal_backend` | `postgres` | true | true | true |
| `pg_read_all_data` | `postgres` | true | true | true |
| `pg_create_subscription` | `postgres` | true | true | true |
| `anon` | `postgres` | true | true | true |
| `anon` | `authenticator` | false | false | true |
| `anon` | `supabase_realtime_admin` | false | false | true |
| `authenticated` | `postgres` | true | true | true |
| `authenticated` | `authenticator` | false | false | true |
| `authenticated` | `supabase_realtime_admin` | false | false | true |
| `service_role` | `postgres` | true | true | true |
| `service_role` | `authenticator` | false | false | true |
| `service_role` | `supabase_realtime_admin` | false | false | true |
| `authenticator` | `postgres` | true | true | true |
| `supabase_privileged_role` | `postgres` | false | true | true |
| `b1_venue_buffer_executor` | `postgres` | true | false | false |
| `b1_venue_buffer_executor` | `postgres` | false | false | true |

## Refresh and Team Review

1. Run the read-only [inspection](../database/current-schema-inspection.sql) in the
   shared Supabase project after a deployment and export the full JSON result.
2. Review function/default literals for secrets before sharing. Do not commit
   credentials, JWTs, application records or local attachments.
3. Update this canonical reference from the actual snapshot; document intended
   requirements and deployment differences explicitly rather than changing
   statuses or policies to hide an inconsistency.
4. Coordinate workflow differences with the affected story owners. Keep runtime
   changes and shared-schema/RLS changes within their approval boundaries.
5. Validate documentation and open a reviewed PR. Merging documentation into
   GitHub does not deploy database SQL or demonstrate live browser acceptance.

## Verified Workflow Alignment and Other Environments

The [Coordinator review audit patch](../database/coordinator-review-planning-patch.sql)
and [equipment priority patch](../database/equipment-pending-venue-priority-patch.sql)
are verified deployed in the 29 October 2026 08:24:13 UTC export. The first adds
planning to permitted old review states in one existing audit INSERT policy,
retaining actor, assignment and target-state checks. The second skips earlier
venue-less pending proposals without altering the candidate's requirements.

No further schema/status change or event backfill is required for this alignment.
Keep these SQL artifacts with the code for reproducibility and other databases.
Teammates connected to this same shared database do not need to reapply them;
other environments need inspection and the matching scoped patches. Do not rerun
the full historical equipment migration or replace venue/B1 logic. Future database
changes need another snapshot and a scoped documentation update. The supplied
catalogue and reported workflow success do not prove all live stock-exhaustion,
overlap/transfer or concurrent-request cases.
