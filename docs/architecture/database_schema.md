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
| `setup_minutes` | `int4` | Nullable; nonnegative when set |
| `turnaround_minutes` | `int4` | Nullable; nonnegative when set |
| `buffer_config_revision` | `bigint` | NOT NULL DEFAULT 0; nonnegative |

The supplied live B1 inspection confirms setup/turnaround must be both null or
both populated. The controlled save currently requires positive durations;
zero/null configurations are not silently treated as zero buffers. Occupied
periods are `[requested_start - setup, requested_end + turnaround)`.
`b1_save_venue_buffers` remains owned by `b1_venue_buffer_executor`; the approved
integration acquires the shared equipment/booking advisory lock before venue
locks and reads the existing request identity without requiring Auth-schema
access. Its receipt, revision and notification behavior remains in B1's scope.

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

### Venue alternatives deployment — supplied verification, 28 October 2026

| Added column | Type | Contract |
|---|---|---|
| `setup_layout` | `text`, nullable for legacy rows | New alternatives require a nonblank, supported per-booking layout. Historical layouts are not inferred or backfilled. |

The developer supplied the [migration verification](../database/venue-booking-alternatives-verification.sql)
result confirming this column, the `cs_venue_one_confirmed_per_event` partial
unique index on `event_id WHERE status='confirmed'`, and the following enabled
triggers: `cs_equipment_booking_lock`, `cs_equipment_venue_block_lock`,
`cs_venue_booking_validate`, `cs_venue_booking_cancel`, `cs_venue_block_validate`.
The verified duplicate confirmed-event count is zero; confirmed occupied-period
validation passed. This is supplied database evidence, not a real-account
browser or production-load test.

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
| `status` | `text` |  Nullable; CHECK permits `requested`, `reserved`, `rejected`, `cancelled` |
| `requested_by` | `uuid` |  |
| `requested_at` | `timestamptz` |  Nullable |
| `decided_by` | `uuid` |  Nullable |
| `decided_at` | `timestamptz` |  Nullable |
| `decision_reason` | `text` |  Nullable |

### Equipment proposal deployment — supplied live inspection

The [proposal migration](../database/equipment-proposals-migration.sql) adds the
following columns to `equipment_reservation`. The supplied live preflight
confirmed these columns and the proposal functions. The later supplied venue
verification confirms the venue-aware equipment checker is installed. Real-account
proposal/consent execution remains a separate integration check.

| Name | Type | Purpose |
|------|------|---------|
| `quantity_suggested` | `integer`, nullable, positive when set | Staff offer; reserved stock uses this quantity, falling back to original quantity for legacy rows |
| `suggested_by` | `uuid`, nullable, FK `profile.user_id` | Proposing staff |
| `suggested_at` | `timestamptz`, nullable | Proposal audit time |
| `proposal_version` | `bigint NOT NULL DEFAULT 0` | Increments for an offer revision |
| `organiser_agreed_version` | `bigint`, nullable | Must match current positive proposal version |
| `organiser_agreed_by` | `uuid`, nullable, FK `profile.user_id` | Event owner giving consent |
| `organiser_agreed_at` | `timestamptz`, nullable | Consent audit time |

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

The migration adds Technical Support event SELECT for equipment-related events
in `planning` or `confirmed` after Coordinator approval, independent of
reservation existence. Organisers may read their own offers and update only
guarded agreement fields. Catalogue SELECT is limited to offered items. Existing
Technical Support catalogue/request policies remain dependencies.

For inbox visibility alone, the separate
[inbox SELECT patch](../database/equipment-organiser-inbox-access.sql) updates
only that event SELECT policy and adds no columns or write permissions.

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


