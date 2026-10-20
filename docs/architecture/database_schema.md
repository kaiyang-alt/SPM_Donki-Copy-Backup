## B1 installation and activation status

**B1 schema/capability is INSTALLED but NOT application-enabled.** Successful
installation and post-install verification were confirmed by the database
operator. This records that verified state against the approved external design
`C:\Users\aiwei\Documents\SMU\y3\SPM\b1-migration-design.md`; it does not claim a
new database inspection or execution by this documentation change.

The three B1 application RPCs remain **ungranted to `authenticated`**. No venue
setup/turnaround population or customer duration backfill occurred: existing
venues remain unconfigured (`NULL`/`NULL`, initial revision `0`) unless separately
authorised and configured later. Runtime/UI, calendar, search, booking and hold
integration is pending. No consumer path may claim full B1 behaviour yet, and
the B2 authoritative hold-validity dependency remains unresolved. Installation
does not authorise capability enablement or population.

## Table `profile`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `user_id` | `uuid` | Primary |
| `name` | `text` |  |
| `active` | `bool` |  |
| `created_at` | `timestamptz` |  |

## Table `user_role`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `user_id` | `uuid` | Primary |
| `role` | `text` | Primary |

## Table `event`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `event_id` | `uuid` | Primary |
| `organiser_id` | `uuid` |  |
| `coordinator_id` | `uuid` |  Nullable |
| `name` | `text` |  Nullable |
| `purpose` | `text` |  Nullable |
| `description` | `text` |  Nullable |
| `preferred_start_datetime` | `timestamptz` |  Nullable |
| `preferred_end_datetime` | `timestamptz` |  Nullable |
| `start_datetime` | `timestamptz` |  Nullable |
| `end_datetime` | `timestamptz` |  Nullable |
| `expected_attendance` | `int4` |  Nullable |
| `registration_limit` | `int4` |  Nullable |
| `venue_requirements` | `text` |  Nullable |
| `accessibility_needs` | `text` |  Nullable |
| `layout_requirements` | `text` |  Nullable |
| `technical_support_required` | `bool` |  Nullable |
| `technical_requirements` | `text` |  Nullable |
| `registration_enabled` | `bool` |  Nullable |
| `registration_open_at` | `timestamptz` |  Nullable |
| `registration_close_at` | `timestamptz` |  Nullable |
| `status` | `text` |  Nullable |
| `created_at` | `timestamptz` |  Nullable |
| `updated_at` | `timestamptz` |  Nullable |

## Table `event_action_log`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `action_id` | `uuid` | Primary |
| `event_id` | `uuid` |  |
| `actor_id` | `uuid` |  Nullable |
| `action_type` | `text` |  Nullable |
| `details` | `text` |  Nullable |
| `old_status` | `text` |  Nullable |
| `new_status` | `text` |  Nullable |
| `created_at` | `timestamptz` |  Nullable |

## Table `event_change_request`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `change_request_id` | `uuid` | Primary |
| `event_id` | `uuid` |  |
| `requested_by` | `uuid` |  |
| `proposed_changes` | `jsonb` |  Nullable |
| `reason` | `text` |  Nullable |
| `status` | `text` |  Nullable |
| `created_at` | `timestamptz` |  Nullable |
| `processed_by` | `uuid` |  Nullable |
| `processed_at` | `timestamptz` |  Nullable |

## Table `event_coordinator_reassignment`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `reassignment_id` | `uuid` | Primary |
| `event_id` | `uuid` |  |
| `from_coordinator_id` | `uuid` |  |
| `to_coordinator_id` | `uuid` |  |
| `status` | `text` |  Nullable |
| `requested_at` | `timestamptz` |  Nullable |
| `responded_at` | `timestamptz` |  Nullable |

## Table `venue`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `venue_id` | `uuid` | Primary |
| `name` | `text` |  Nullable |
| `location` | `text` |  Nullable |
| `capacity` | `int4` |  Nullable |
| `facilities` | `jsonb` |  Nullable |
| `accessibility` | `text` |  Nullable |
| `supported_layouts` | `jsonb` |  Nullable |
| `operating_hours` | `text` |  Nullable |
| `active` | `bool` |  Nullable |
| `setup_minutes` | `integer` | Nullable; no default; whole setup minutes |
| `turnaround_minutes` | `integer` | Nullable; no default; whole turnaround minutes |
| `buffer_config_revision` | `bigint` | NOT NULL; DEFAULT `0`; technical configuration revision |

### B1 constraints and unconfigured state

| CHECK constraint | Expression |
| --- | --- |
| `b1_venue_setup_nonnegative` | `setup_minutes IS NULL OR setup_minutes >= 0` |
| `b1_venue_turnaround_nonnegative` | `turnaround_minutes IS NULL OR turnaround_minutes >= 0` |
| `b1_venue_buffer_pair` | `(setup_minutes IS NULL) = (turnaround_minutes IS NULL)` |
| `b1_venue_buffer_revision_nonnegative` | `buffer_config_revision >= 0` |

`NULL`/`NULL` means unconfigured, never implicit zero; a partial pair is prohibited.
Revision `0` is technical initial state, not a customer duration default.
Negative durations are invalid. The nonnegative representation CHECKs do not
settle zero's business validity: zero remains decision-required in the installed
save RPC and occupancy helper. No customer duration values were backfilled.

## Table `venue_buffer_operation`

### Columns

| Name | Type | Constraints |
| --- | --- | --- |
| `operation_id` | `uuid` | Primary key; NOT NULL; caller retry token |
| `actor_id` | `uuid` | NOT NULL; derived authenticated actor |
| `venue_id` | `uuid` | NOT NULL; historical venue identifier; no FK |
| `expected_revision` | `bigint` | NOT NULL; CHECK `expected_revision >= 0` |
| `setup_minutes` | `integer` | NOT NULL; CHECK `setup_minutes >= 0` |
| `turnaround_minutes` | `integer` | NOT NULL; CHECK `turnaround_minutes >= 0` |
| `result_revision` | `bigint` | NOT NULL; CHECK `result_revision >= 0` |
| `recorded_at` | `timestamptz` | NOT NULL; explicitly supplied transaction timestamp |
| `outcome` | `jsonb` | NOT NULL; CHECK `pg_catalog.jsonb_typeof(outcome) = 'object'` |

No column has a default. The non-unique B-tree index
`b1_venue_buffer_operation_venue_time_idx` covers
`(venue_id, recorded_at, operation_id)`. There are no foreign keys, including no
venue FK: historical receipts neither add venue DELETE/TRUNCATE restrictions
nor disappear through a new cascade.

The `postgres`-owned table stores immutable request/result receipts for
actor-bound idempotency and historical impact replay. `outcome` contains saved
values/revision, conflicts, assessment limitations, persisted notice identities
and durable `routing_exceptions`. The executor has restricted `SELECT`/`INSERT`
access only; no receipt UPDATE/DELETE capability or automatic repair is provided.
RLS is enabled and forced. Direct table privileges were revoked from `PUBLIC`,
`anon`, `authenticated` and `service_role`. Application access through the receipt
RPCs is also currently disabled. Retention is indefinite for this release;
cleanup, archival or exception-resolution mutation requires separate approval.

## Table `venue_booking`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `booking_id` | `uuid` | Primary |
| `venue_id` | `uuid` |  |
| `event_id` | `uuid` |  |
| `requested_start` | `timestamptz` |  Nullable |
| `requested_end` | `timestamptz` |  Nullable |
| `status` | `text` |  Nullable; CHECK permits `requested`, `tentative`, `confirmed`, `rejected`, `cancelled` |
| `requested_by` | `uuid` |  |
| `requested_at` | `timestamptz` |  Nullable |
| `decided_by` | `uuid` |  Nullable |
| `decided_at` | `timestamptz` |  Nullable |
| `decision_reason` | `text` |  Nullable |

## Table `venue_block`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `venue_block_id` | `uuid` | Primary |
| `venue_id` | `uuid` |  |
| `start_datetime` | `timestamptz` |  Nullable |
| `end_datetime` | `timestamptz` |  Nullable |
| `reason` | `text` |  Nullable |
| `created_by` | `uuid` |  |
| `created_at` | `timestamptz` |  Nullable |
| `status` | `text` |  Nullable; CHECK permits `active`, `cancelled` |

## Table `equipment`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `equipment_id` | `uuid` | Primary |
| `name` | `text` |  Nullable |
| `type` | `text` |  Nullable |
| `description` | `text` |  Nullable |
| `total_quantity` | `int4` |  Nullable |
| `location` | `text` |  Nullable |
| `active` | `bool` |  Nullable |

## Table `equipment_reservation`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `reservation_id` | `uuid` | Primary |
| `event_id` | `uuid` |  |
| `equipment_id` | `uuid` |  |
| `quantity_requested` | `int4` |  Nullable |
| `start_datetime` | `timestamptz` |  Nullable |
| `end_datetime` | `timestamptz` |  Nullable |
| `technical_requirements` | `text` |  Nullable |
| `status` | `text` |  Nullable |
| `requested_by` | `uuid` |  |
| `requested_at` | `timestamptz` |  Nullable |
| `decided_by` | `uuid` |  Nullable |
| `decided_at` | `timestamptz` |  Nullable |
| `decision_reason` | `text` |  Nullable |

## Table `registration`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `registration_id` | `uuid` | Primary |
| `event_id` | `uuid` |  |
| `attendee_id` | `uuid` |  |
| `registration_type` | `text` |  Nullable |
| `status` | `text` |  Nullable |
| `registered_at` | `timestamptz` |  Nullable |
| `invited_at` | `timestamptz` |  Nullable |
| `updated_at` | `timestamptz` |  Nullable |

## Table `notification`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `notification_id` | `uuid` | Primary |
| `event_id` | `uuid` |  Nullable |
| `recipient_id` | `uuid` |  |
| `type` | `text` |  Nullable |
| `message` | `text` |  Nullable |
| `created_at` | `timestamptz` |  Nullable |
| `read_at` | `timestamptz` |  Nullable |

## Table `equipment_unavailability`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `equipment_unavailability_id` | `uuid` | Primary |
| `equipment_id` | `uuid` |  |
| `quantity_unavailable` | `int4` |  Nullable |
| `start_datetime` | `timestamptz` |  Nullable |
| `end_datetime` | `timestamptz` |  Nullable |
| `reason` | `text` |  Nullable |
| `created_by` | `uuid` |  |
| `created_at` | `timestamptz` |  Nullable |
| `status` | `text` |  Nullable |

## RLS Policies

### `equipment`

| Policy | Command | Roles | Action | USING | WITH CHECK |
|--------|---------|-------|--------|-------|------------|
| `Coordinators can view equipment` | SELECT | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text))))` | — |
| `Technical support can view equipment` | SELECT | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text))))` | — |

### `equipment_unavailability`

| Policy | Command | Roles | Action | USING | WITH CHECK |
|--------|---------|-------|--------|-------|------------|
| `Technical support can create equipment unavailability` | INSERT | authenticated | PERMISSIVE | — | `((created_by = auth.uid()) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text)))))` |
| `Technical support can update equipment unavailability` | UPDATE | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text))))` | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text))))` |
| `Technical support can view equipment unavailability` | SELECT | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text))))` | — |

### `event_change_request`

| Policy | Command | Roles | Action | USING | WITH CHECK |
|--------|---------|-------|--------|-------|------------|
| `Coordinators can update assigned event change requests` | UPDATE | authenticated | PERMISSIVE | `((EXISTS ( SELECT 1    FROM event   WHERE ((event.event_id = event_change_request.event_id) AND (event.coordinator_id = auth.uid())))) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))))` | `((EXISTS ( SELECT 1    FROM event   WHERE ((event.event_id = event_change_request.event_id) AND (event.coordinator_id = auth.uid())))) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))))` |
| `Coordinators can view assigned event change requests` | SELECT | authenticated | PERMISSIVE | `((EXISTS ( SELECT 1    FROM event   WHERE ((event.event_id = event_change_request.event_id) AND (event.coordinator_id = auth.uid())))) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))))` | — |
| `Organisers can create own event change requests` | INSERT | authenticated | PERMISSIVE | — | `((requested_by = auth.uid()) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_organiser'::text)))) AND (EXISTS ( SELECT 1    FROM event   WHERE ((event.event_id = event_change_request.event_id) AND (event.organiser_id = auth.uid())))))` |
| `Organisers can view own event change requests` | SELECT | authenticated | PERMISSIVE | `((requested_by = auth.uid()) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_organiser'::text)))))` | — |

### `event_coordinator_reassignment`

| Policy | Command | Roles | Action | USING | WITH CHECK |
|--------|---------|-------|--------|-------|------------|
| `Current coordinators can create reassignments` | INSERT | authenticated | PERMISSIVE | — | `((from_coordinator_id = auth.uid()) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))) AND (EXISTS ( SELECT 1    FROM event   WHERE ((event.event_id = event_coordinator_reassignment.event_id) AND (event.coordinator_id = auth.uid())))))` |
| `Current coordinators can view outgoing reassignments` | SELECT | authenticated | PERMISSIVE | `((from_coordinator_id = auth.uid()) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))))` | — |
| `Proposed coordinators can respond to reassignments` | UPDATE | authenticated | PERMISSIVE | `((to_coordinator_id = auth.uid()) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))))` | `((to_coordinator_id = auth.uid()) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))))` |
| `Proposed coordinators can view incoming reassignments` | SELECT | authenticated | PERMISSIVE | `((to_coordinator_id = auth.uid()) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))))` | — |

### `venue_block`

| Policy | Command | Roles | Action | USING | WITH CHECK |
|--------|---------|-------|--------|-------|------------|
| `Coordinators can view venue blocks` | SELECT | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text))))` | — |
| `Venue staff can create venue blocks` | INSERT | authenticated | PERMISSIVE | — | `((created_by = auth.uid()) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text)))))` |
| `Venue staff can update venue blocks` | UPDATE | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` |
| `Venue staff can view venue blocks` | SELECT | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` | — |

### `profile`

| Policy | Command | Roles | Action | USING | WITH CHECK |
|--------|---------|-------|--------|-------|------------|
| `Users can view own profile` | SELECT | authenticated | PERMISSIVE | `(user_id = auth.uid())` | — |

### `equipment_reservation`

| Policy | Command | Roles | Action | USING | WITH CHECK |
|--------|---------|-------|--------|-------|------------|
| `Coordinators can create own event equipment reservations` | INSERT | authenticated | PERMISSIVE | — | `((requested_by = auth.uid()) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))) AND (EXISTS ( SELECT 1    FROM event   WHERE ((event.event_id = equipment_reservation.event_id) AND (event.coordinator_id = auth.uid())))))` |
| `Coordinators can view own event equipment reservations` | SELECT | authenticated | PERMISSIVE | `((EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))) AND (EXISTS ( SELECT 1    FROM event   WHERE ((event.event_id = equipment_reservation.event_id) AND (event.coordinator_id = auth.uid())))))` | — |
| `Technical support can update equipment reservations` | UPDATE | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text))))` | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text))))` |
| `Technical support can view equipment reservations` | SELECT | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'technical_support'::text))))` | — |

### `event`

| Policy | Command | Roles | Action | USING | WITH CHECK |
|--------|---------|-------|--------|-------|------------|
| `Attendees can view confirmed events` | SELECT | authenticated | PERMISSIVE | `((status = 'confirmed'::text) AND (registration_enabled = true) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'attendee'::text)))))` | — |
| `Coordinators can update assigned events` | UPDATE | authenticated | PERMISSIVE | `((coordinator_id = auth.uid()) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))))` | `((coordinator_id = auth.uid()) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))))` |
| `Coordinators can view all events` | SELECT | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text))))` | — |
| `Organisers can create own events` | INSERT | authenticated | PERMISSIVE | — | `((organiser_id = auth.uid()) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_organiser'::text)))))` |
| `Organisers can update editable own events` | UPDATE | authenticated | PERMISSIVE | `((organiser_id = auth.uid()) AND (status = ANY (ARRAY['draft'::text, 'requested'::text, 'changes_requested'::text])) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_organiser'::text)))))` | `((organiser_id = auth.uid()) AND (status = ANY (ARRAY['draft'::text, 'requested'::text, 'changes_requested'::text])) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_organiser'::text)))))` |
| `Organisers can view own events` | SELECT | authenticated | PERMISSIVE | `(organiser_id = auth.uid())` | — |

### `venue_booking`

| Policy | Command | Roles | Action | USING | WITH CHECK |
|--------|---------|-------|--------|-------|------------|
| `Coordinators can create venue bookings` | INSERT | authenticated | PERMISSIVE | — | `((requested_by = auth.uid()) AND (EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))) AND (EXISTS ( SELECT 1    FROM event   WHERE ((event.event_id = venue_booking.event_id) AND (event.coordinator_id = auth.uid())))))` |
| `Coordinators can view venue bookings` | SELECT | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text))))` | — |
| `Venue staff can update venue bookings` | UPDATE | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` |
| `Venue staff can view venue bookings` | SELECT | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` | — |

### `registration`

| Policy | Command | Roles | Action | USING | WITH CHECK |
|--------|---------|-------|--------|-------|------------|
| `Attendees can view own registrations` | SELECT | authenticated | PERMISSIVE | `(attendee_id = auth.uid())` | — |
| `Coordinators can view registrations for assigned events` | SELECT | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM event   WHERE ((event.event_id = registration.event_id) AND (event.coordinator_id = auth.uid()))))` | — |
| `Organisers can view registrations for own events` | SELECT | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM event   WHERE ((event.event_id = registration.event_id) AND (event.organiser_id = auth.uid()))))` | — |

### `venue`

| Policy | Command | Roles | Action | USING | WITH CHECK |
|--------|---------|-------|--------|-------|------------|
| `Coordinators can view venues` | SELECT | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text))))` | — |
| `Venue staff can update venues` | UPDATE | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` |
| `Venue staff can view venues` | SELECT | authenticated | PERMISSIVE | `(EXISTS ( SELECT 1    FROM user_role   WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'venue_staff'::text))))` | — |

### `user_role`

| Policy | Command | Roles | Action | USING | WITH CHECK |
|--------|---------|-------|--------|-------|------------|
| `Users can view own roles` | SELECT | authenticated | PERMISSIVE | `(user_id = auth.uid())` | — |

### `notification`

| Policy | Command | Roles | Action | USING | WITH CHECK |
|--------|---------|-------|--------|-------|------------|
| `Users can update own notifications` | UPDATE | authenticated | PERMISSIVE | `(recipient_id = auth.uid())` | `(recipient_id = auth.uid())` |
| `Users can view own notifications` | SELECT | authenticated | PERMISSIVE | `(recipient_id = auth.uid())` | — |

### B1 executor-specific additions

All policies below are PERMISSIVE and apply only to
`b1_venue_buffer_executor`. Pre-existing application policies above remain in
place; no broad Staff event-access or arbitrary notification-insert policy was
added.

| Table | Policy | Command | USING | WITH CHECK |
| --- | --- | --- | --- | --- |
| `venue` | `b1_executor_venue_read` | SELECT | `true` | — |
| `venue` | `b1_executor_venue_write` | UPDATE | `true` | `true` |
| `venue_booking` | `b1_executor_booking_read` | SELECT | `true` | — |
| `venue_block` | `b1_executor_block_read` | SELECT | `true` | — |
| `user_role` | `b1_executor_role_read` | SELECT | `true` | — |
| `event` | `b1_executor_event_read` | SELECT | `true` | — |
| `event` | `b1_executor_event_lock` | UPDATE | `true` | `false` |
| `notification` | `b1_executor_notice_insert` | INSERT | — | `type = 'venue_buffer_conflict' AND event_id IS NOT NULL AND recipient_id IS NOT NULL AND read_at IS NULL` |
| `venue_buffer_operation` | `b1_executor_receipt_read` | SELECT | `true` | — |
| `venue_buffer_operation` | `b1_executor_receipt_insert` | INSERT | — | `true` |

## B1 executor role and controlled writes

`b1_venue_buffer_executor` has `NOLOGIN`, `NOINHERIT`, `NOSUPERUSER`,
`NOCREATEROLE`, `NOCREATEDB`, `NOREPLICATION` and `NOBYPASSRLS`. It owns the six
B1 functions below, not the receipt table, and has no schema CREATE privilege
after installation. Its role flags alone are not the security test: the verified
postflight checks effective role relationships as well.

There is no application-role MEMBER/SET/USAGE/ADMIN path to the executor. Checks
cover `authenticated`, `anon`, `authenticator`, `service_role` and custom
non-administrative login/group roles, including indirect relationships and
administrative escalation paths. The executor has no parent-role membership,
assumption, inheritance or administration privilege path. No application actor
receives executor credentials or a new BYPASSRLS capability.

Administrative relationships involving `postgres`/`supabase_admin` are
platform/admin scope, not application access. An administrator being a member
of the executor is not the executor inheriting that administrator's role.
The installation's explicit `GRANT b1_venue_buffer_executor TO postgres` was
paired with `REVOKE b1_venue_buffer_executor FROM postgres` after function
ownership transfer. Safety is established by the effective application and
executor relationship checks, not a requirement for zero `pg_auth_members`
rows. No non-superuser internal role gains an exemption merely by its name.

### Executor object privileges

| Object | Executor privilege |
| --- | --- |
| Schema `public` | USAGE; temporary CREATE revoked after ownership transfer |
| Schema `auth`; function `auth.uid()` | Schema USAGE; function EXECUTE |
| `venue` | SELECT `(venue_id, setup_minutes, turnaround_minutes, buffer_config_revision)`; UPDATE `(setup_minutes, turnaround_minutes, buffer_config_revision)` |
| `venue_booking` | SELECT `(booking_id, venue_id, event_id, requested_start, requested_end, status)` |
| `venue_block` | SELECT `(venue_block_id, venue_id, start_datetime, end_datetime, status)` |
| `user_role` | SELECT `(user_id, role)` |
| `event` | SELECT `(event_id, coordinator_id)`; UPDATE `(coordinator_id)` for locking reads only |
| `notification` | INSERT `(notification_id, event_id, recipient_id, type, message, created_at, read_at)` |
| `venue_buffer_operation` | SELECT, INSERT |

The minimal event UPDATE column privilege supports `FOR SHARE` locking reads;
the executor-specific UPDATE policy has `WITH CHECK (false)`. B1 performs no
event UPDATE and grants no Staff event-edit capability. The executor uses its
scoped RLS policies rather than global RLS bypass.

### Venue guard and preserved ordinary operations

The row trigger `b1_guard_venue_buffer_rows` runs
`public.b1_guard_venue_buffers()` **AFTER INSERT OR UPDATE** on `public.venue`.
It validates the final row image and uses the genuine `current_user` executor
context, not caller-controlled JWT claims or custom session flags.

- INSERT must start with `NULL` setup, `NULL` turnaround and revision `0`.
- An ordinary caller cannot actually change any of `setup_minutes`,
  `turnaround_minutes` or `buffer_config_revision`. Naming these fields while
  leaving the triple unchanged does not count as a configuration change.
- Actual B1 changes use the controlled executor path, retain a configured
  non-NULL pair, change the values and advance revision by exactly one. A
  revision-only bump or clearing an existing pair is refused.
- Ordinary unrelated venue updates remain under existing grants and RLS.
  Pre-existing venue ACL/RLS behaviour was preserved: authenticated table
  privileges were not removed, including the existing table UPDATE/INSERT
  shape. SQL privileges still permit columns while RLS controls rows; the
  guard enforces the B1 field boundary.
- No B1 DELETE/TRUNCATE restriction or trigger was introduced, and existing
  DELETE/TRUNCATE/TRIGGER privileges were not revoked as security cleanup.

## B1 installed functions

All six functions are `LANGUAGE plpgsql`, owned by
`b1_venue_buffer_executor`, with fixed `search_path = pg_catalog, pg_temp`.
Signatures below use PostgreSQL type aliases `integer` and `timestamptz`.

| Exact signature | Result | Security | Volatility | TimeZone |
| --- | --- | --- | --- | --- |
| `public.b1_guard_venue_buffers()` | `trigger` | INVOKER | VOLATILE (default) | No function-level setting |
| `public.b1_occupied_period(p_start timestamptz, p_end timestamptz, p_setup integer, p_turnaround integer)` | `tstzrange` | INVOKER | IMMUTABLE | UTC |
| `public.b1_buffer_conflicts(p_venue_id uuid, p_setup integer, p_turnaround integer)` | `jsonb` | INVOKER | STABLE | UTC |
| `public.b1_save_venue_buffers(p_venue_id uuid, p_setup_minutes integer, p_turnaround_minutes integer, p_expected_revision bigint, p_operation_id uuid)` | `jsonb` | DEFINER | VOLATILE | UTC |
| `public.b1_get_venue_buffer_operation(p_venue_id uuid, p_operation_id uuid)` | `jsonb` | DEFINER | STABLE | UTC |
| `public.b1_list_venue_buffer_routing_exceptions(p_venue_id uuid)` | `TABLE (operation_id uuid, actor_id uuid, configuration_revision bigint, recorded_at timestamptz, routing_exceptions jsonb)` | DEFINER | STABLE | UTC |

### Purpose and current EXECUTE state

| Function | Installed purpose | Current EXECUTE state |
| --- | --- | --- |
| `b1_guard_venue_buffers` | Enforce the venue B1 field/revision boundary through the row trigger | Function-owner rights; no application grant; trigger enforcement remains active |
| `b1_occupied_period` | Exact B1-OCC-v1 occupied interval arithmetic and technical validation | Function-owner rights and explicit `postgres` administrative EXECUTE; no application grant |
| `b1_buffer_conflicts` | Validate authoritative venue occupancy and derive resulting identified/potential conflicts without lifecycle mutation | Function-owner rights and explicit `postgres` administrative EXECUTE; no application grant |
| `b1_save_venue_buffers` | Atomic authorised save, impact derivation, notice/routing-exception persistence and retry receipt | **Application RPC UNGRANTED to `authenticated`; disabled** |
| `b1_get_venue_buffer_operation` | Read the current Staff actor's own immutable historical receipt | **Application RPC UNGRANTED to `authenticated`; disabled** |
| `b1_list_venue_buffer_routing_exceptions` | Read historical incomplete-routing receipts for one venue for Staff follow-up | **Application RPC UNGRANTED to `authenticated`; disabled** |

Default/explicit EXECUTE grants on these functions were revoked from `PUBLIC`,
`anon`, `authenticated` and `service_role`. Only the two private arithmetic/read
helpers received explicit administrative EXECUTE grants to `postgres`.
Function-owner rights and existing platform administration are not application
enablement. No capability-enablement GRANT has been applied.

Each SECURITY DEFINER RPC independently checks `auth.uid()` and the authoritative
`user_role` entry for `venue_staff`, including receipt reads and retries. The
save derives affected records, assignments, recipients, notification type/content
and timestamps internally; callers cannot supply arbitrary event/recipient lists
or notification payloads. No broad event API or arbitrary notification INSERT
is exposed.

## B1 transaction, concurrency and idempotency contract

This is the installed database contract; authenticated invocation remains
disabled pending separate activation approval.

1. Validate actor and intent. A globally unique `operation_id` UUID binds the
   actor, venue, exact duration pair and `expected_revision`. A committed
   exact retry returns its immutable stored outcome before a fresh assessment;
   different actor/input reuse fails. Historical replay remains available to
   an authorised actor even after later edits or venue deletion and never
   claims to be a current occupancy assessment.
2. For a new intent, lock the venue `FOR UPDATE`, then acquire the transaction
   advisory lock derived from the retry token and recheck the receipt. Compare
   expected revision under the venue lock; stale edits fail without effects.
3. Lock relevant event rows `FOR SHARE` in stable event UUID order, protecting
   Coordinator assignment while deriving impacts and recipients. All relevant
   writers must follow venue-first, event-second ordering. Multi-venue writers
   take venue locks in UUID order; reassignment may lock an event alone but
   must not subsequently acquire a venue lock in that transaction. Discovered
   record sets must be revalidated under the participating writers' locks.
4. Validate authoritative occupancy and derive old/new conflicts. Genuine
   business conflicts do not reject a valid configuration save. Authoritative
   assessment failure does reject it. Initial old NULL configuration is
   disclosed as unknown, never calculated as zero.
5. Changed values advance configuration revision once. A new-token identical
   value request with the current expected revision still assesses the venue
   and records a no-op receipt, without a venue update, revision increment or
   notices. A stale identical-value request fails; a committed replay does not
   repeat assessment or effects.
6. For new/changed identified conflict periods, persist at most one internally
   templated `venue_buffer_conflict` notice per affected event/recipient for
   the operation. Return all resulting conflicts. Preserve original bookings,
   requested times and event/block/hold lifecycle; no cancellation, replacement,
   reassignment or event status change is performed.
7. Commit the venue configuration, notices, durable routing exceptions and
   immutable receipt together. An assessment error or unexpected database,
   notification-insert or receipt-write error rolls everything back. A failed
   attempt leaves no success receipt; retrying a committed operation returns
   its saved result without duplicate effects.

Missing assigned Coordinators do not erase an otherwise valid save. All
derivable notices persist; `outcome.routing_exceptions` durably records the
affected event/booking identifiers, configuration revision and reason
(`missing_event`, `missing_assigned_coordinator` or
`assigned_coordinator_role_missing`). No fallback recipient is invented.
`notification_status = incomplete_routing` visibly distinguishes this outcome
from full notice persistence. Staff follow-up uses the restricted receipt APIs
once separately enabled. A later assignment does not reroute a replay; no
automatic repair delivery is installed. Persisted notices do not prove external
email/push delivery or reading.

The lock protocol is an integration obligation for other writers, not evidence
that existing runtime paths already participate. Contract A owns operational
block effects; B2 owns hold validity; C1/C2 own replacement and readiness/
reconfirmation. Their runtime integration and coordinated activation remain
pending.

## B1-OCC-v1 occupancy and assessment boundaries

The installed common occupancy semantics are:

```text
occupied_start = requested_start - setup_minutes
occupied_end   = requested_end + turnaround_minutes
occupied interval = [occupied_start, occupied_end)
```

Durations are whole elapsed minutes on timezone-aware instants; the database
helpers use UTC. Two occupied intervals conflict only if they have positive
overlap; exact endpoint touch does not conflict. The common technical datetime
domain is UTC years 1 through 9999; unrepresentable arithmetic fails explicitly.
`requested_start`/`requested_end` remain scheduled times and are not overwritten
with expanded occupancy. There is no per-booking override and no extra
maintenance-block-side buffer expansion: recorded bounded active blocks are
compared directly with buffered booking occupancy.

`NULL != zero`: absent configuration is unconfigured/unavailable to assess.
Negative durations are invalid; zero business validity remains unresolved.
The save RPC and occupied-period helper return `B1_ZERO_DECISION_REQUIRED` for
zero, rather than declaring it valid or invalid or substituting another value.
The nonnegative persistence CHECKs are representation safeguards, not customer
approval of zero. No numerical customer default or backfill was introduced.

Confirmed-booking pairs and confirmed-booking/active-block overlaps are
identified conflicts. Requested/tentative participants remain potential impacts:
B2 has not supplied authoritative active/expired hold validity. They are
preserved without lifecycle invention; a malformed hold schedule is explicitly
reported as `hold_schedule_unassessable_pending_owner`. Such uncertainty keeps
`assessment_complete = false` and prevents unrestricted hold-aware activation.

Malformed authoritative confirmed data blocks assessment, even for a lone
booking with no otherwise identifiable overlap. Missing/nonfinite/reversed or
unsupported-range confirmed times, unknown/NULL booking or block lifecycle
status, and unassessable active blocks raise
`B1_AUTHORITATIVE_OCCUPANCY_UNASSESSABLE` with record-specific details; arithmetic
overflow also fails. The save rolls back rather than omitting those records and
reporting success. An active block with missing bounds, including an unresolved
open-ended block, is a bounded-scope blocker: no end time is invented and B1
does not declare that customer input invalid. The owning workflow must resolve
classification/data/scope before that venue can enter unrestricted activation.

A newly committed outcome has `authoritative_assessment_complete = true`;
authoritative blockers never become successful receipts with a warning.
`assessment_complete` additionally requires complete hold assessment. Initial
`old_configuration_unconfigured` disclosure alone does not make the proposed
current occupancy incomplete. Routing completeness is separate: occupancy can
be assessable while notification routing remains incomplete. None of these
database contracts claims that pending application consumers are B1-enabled.


