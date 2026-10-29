# Add New Equipment to the Catalogue

## User Story

As a Technical Support Staff member, I want to register new equipment details into the catalogue so that newly acquired resources are available for event planning and assignment.

## Acceptance Criteria

- AC1: A Technical Support Staff member can add a new equipment item to the catalogue by submitting valid equipment details: name, category, description, location and total quantity.
- AC2: Total quantity must be a whole number greater than 0. A quantity of 1 is accepted.
- AC3: Saving is blocked and an error message is displayed when any mandatory field (name, category, description, location, total quantity) is omitted. A field containing only whitespace is treated as omitted.
- AC4: Saving is blocked and an error message is displayed when total quantity is invalid: 0, negative, or not a whole number. No equipment record is created when saving is blocked.
- AC5: A newly saved equipment item is created as active and appears in the active equipment catalogue immediately, without re-entering the system. It is visible to Technical Support Staff and Event Coordinators for future event selection.
- AC6: Only users with the `technical_support` role can add equipment. Requests from other roles or unauthenticated users are rejected and no equipment record is created.
- AC7: An equipment item whose name matches an existing catalogue item is saved as a separate item. Duplicate names are not blocked.

## Test Case Reference

`docs/test-cases/add-new-equipment.md`

## Relevant Customer Clarifications

- Week 1 Customer Briefing (Equipment Catalogue): the system maintains equipment information including type, description, quantity, location and operational status.
- Week 1 Customer Briefing (Equipment Availability Checking / Reservation): catalogue equipment is the source for availability checks and reservations.
- Team decision (29 Oct 2026): Equipment Catalogue entry is in scope for Release 1 as agreed with the customer/team.
- Team decision (29 Oct 2026): "Category" is stored in the existing `equipment.type` column as free text. All five fields (name, category, description, location, total quantity) are mandatory. Duplicate equipment names are allowed.

## Preconditions / Dependencies

- The user is authenticated through Supabase Authentication and holds the `technical_support` role.
- Uses the existing `equipment` table: `name`, `type` (category), `description`, `total_quantity`, `location`, `active`.
- **Shared RLS dependency (Human Gate 3):** the documented `equipment` table has SELECT policies only (`Coordinators can view equipment`, `Technical support can view equipment`). There is no INSERT policy for `technical_support`. A team-approved INSERT policy restricted to the `technical_support` role is required before AC1 and AC6 can be implemented. Do not bypass RLS or use a service-role key.
- AC5 relies on the existing SELECT policies for Technical Support Staff and Event Coordinators.

## Relevant UML Reference

Not required. This is a single-actor create flow with no multi-actor sequencing.

## Implementation Notes

- Follow `Frontend -> Flask Route -> Service -> Supabase`. Validation rules belong in the equipment service; the route handles request input and response.
- Use `create_authenticated_supabase_client(access_token)` so the insert runs under the caller's RLS.
- Trim text fields before validation. Store trimmed values.
- Set `active = true` on creation. Do not introduce new columns or status values.
- Store category in `equipment.type`; display it as "Category" in the interface.
- Extend the existing Technical Support `equipment` page in `app/static/js/app.js` using shared layout and form patterns; do not redesign the page.
- Unavailability (maintenance/damage) is recorded separately through `equipment_unavailability` and is outside this story.