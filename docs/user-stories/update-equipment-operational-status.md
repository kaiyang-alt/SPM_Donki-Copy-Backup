# Update Equipment Operational Status

## User Story

As a Technical Support Staff member, I want to update an equipment item's
operational status so that unavailable equipment is not reserved for events.

## Acceptance Criteria

- **AC1:** Technical Support Staff can view the current operational status of
  each equipment item.
- **AC2:** Technical Support Staff can update an equipment item's operational
  status to `Available`, `Damaged`, `Under Repair`, or `Unavailable`.
- **AC3:** Equipment marked `Available` is included in equipment availability
  results and can be selected for a new reservation.
- **AC4:** Equipment marked `Damaged`, `Under Repair`, or `Unavailable` is
  excluded from equipment availability results and cannot be selected for a
  new reservation.
- **AC5:** When an equipment item's status changes from an unavailable status
  to `Available`, it becomes eligible for new reservations, subject to its
  reservation schedule.
- **AC6:** After a status change is saved, the system displays the updated
  operational status.

## Requirement Source

- The User Story and Acceptance Criteria were supplied by the developer from
  the assigned story's AC checklist on 27 October 2026.

## Confirmed Clarifications

- An "equipment item" means one existing row in the equipment catalogue. If
  that row has `total_quantity = 10`, its operational status applies to all ten
  units represented by the row.
- This story does not introduce serial-number or individual-unit tracking.
- Persist the four display statuses as `available`, `damaged`, `under_repair`,
  and `unavailable`.
- The existing `equipment.active` flag remains the catalogue activation flag
  and is not overloaded to represent the four operational statuses.
- Only `active` equipment with operational status `available` is eligible for
  a new reservation. Existing reservation schedules, maintenance periods,
  available quantity, venue, and transfer rules still apply.
- Changing an item to a non-available operational status blocks new
  reservations but does not automatically cancel or rewrite existing
  reservations.

## Preconditions / Dependencies

- The caller is authenticated through the existing Supabase Authentication
  setup and has the `technical_support` role.
- The equipment catalogue exists and the caller can view its equipment rows.
- Equipment availability and reservation workflows use the saved operational
  status in addition to their existing schedule and quantity rules.

## Cross-Story Impacts

- `reserve-equipment` owns proposal, availability, and reservation behaviour.
  Its owner must consume the operational status so only `available` items are
  offered or accepted. This story does not rewrite that story's canonical
  requirements.
- Existing time-bounded `equipment_unavailability` records continue to model
  unavailable quantities and periods. They do not replace the catalogue-level
  operational status introduced by this story.

## Potential Shared Architecture Dependencies

- The documented `equipment` table currently has no operational-status column.
  Representing all four required values without overloading `active` requires
  an approved schema change.
- The documented RLS catalogue permits Technical Support to view `equipment`
  but does not permit an operational-status update. A narrowly scoped approved
  write mechanism and corresponding RLS permissions are required.
- Existing equipment availability services and Supabase functions currently
  calculate schedule and quantity availability without this field. They must
  exclude non-available catalogue rows after the shared database design is
  approved and deployed.

## Test Case Reference

`docs/test-cases/update-equipment-operational-status.md`

## Relevant UML Reference

- No new UML is required during requirement reconciliation. Revisit this only
  if implementation readiness identifies a non-obvious shared interaction.

## Implementation Notes

- Reuse the existing Technical Support workspace, equipment catalogue, Flask
  routing, service layer, authenticated Supabase client, and visual patterns.
- Do not replace the existing quantity-, maintenance-, venue-, or
  schedule-based availability checks.
- Do not implement automatic cancellation of existing reservations because it
  is not required by the approved Acceptance Criteria.

## Implementation Status

- The approved schema migration was applied to the shared Supabase project and
  verified on 27 October 2026: the column is non-null with default `available`,
  the four-value CHECK constraint exists, the restricted update function
  exists, the reservation guard exists, and no catalogue row has a null status.
- The existing Technical Support Equipment page displays every catalogue
  item's current status and saves changes through the restricted function.
- Catalogue selection, availability checks, service-level acceptance, and the
  database reservation guard exclude inactive or non-available equipment from
  new reservations. Existing saved reservations are not automatically changed.
