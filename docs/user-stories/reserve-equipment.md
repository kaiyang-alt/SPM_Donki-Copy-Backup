# Reserve Equipment

## User Story

As a Technical Support Staff, I want to reserve equipment for specific events so that I can prevent equipment from being double-booked.

## Acceptance Criteria

The criteria below retain AC1–AC6 and incorporate the confirmed Technical Support review workflow. Submitting a Coordinator request and accepting it as a reservation are distinct actions.

- **AC1:** Can view the equipment required by an existing Coordinator request for an event, including equipment type and required quantity.
- **AC2:** Can view the required equipment's available quantity for the request's specified start and end date/time, accounting for overlapping reserved quantities and maintenance/unavailability quantities.
- **AC3:** Can review and accept an existing `planning` equipment request for an event in `planning` or `confirmed` status when sufficient stock is available for the entire requested period.
- **AC4:** On successful acceptance, the system updates the existing request to `reserved` and displays confirmation showing the event, equipment, date, and time. Reopening the request shows the saved reservation.
- **AC5:** When sufficient equipment is unavailable for the specified period, the system prevents final reservation acceptance and displays a clear equipment unavailability message. The previously submitted Coordinator request is retained; submission of that pending request is not the stock-committing action.
- **AC6:** The system prevents overlapping accepted reservations from allocating more units than available stock. Overlapping reservations may share an equipment pool when sufficient units remain. When competing requests cannot both be fulfilled, the earliest request has priority; simultaneous Technical Support acceptance attempts must not double-book stock.

## Relevant Customer Clarifications / Confirmed Project Rules

### Review Workflow and Data Sources

- Technical Support Staff is the reviewing team. It reviews and accepts existing Coordinator-created requests; no separate approval group or approval step is required.
- Coordinator requests may be submitted before review. A request awaiting review has `equipment_reservation.status = planning` and does not itself commit stock. Technical Support acceptance changes that same row to `reserved`; this story does not insert a new reservation row.
- Eligible event statuses are `planning` and `confirmed`. The initially mentioned event status `pending` was clarified as `planning`; do not add a new event status.
- `equipment.type` and `equipment.total_quantity` supply equipment type and total stock. The linked Coordinator request supplies `equipment_id`, `quantity_requested`, `start_datetime`, and `end_datetime`. Total stock is not the event's required quantity.
- Do not infer quantities from free-text `event.technical_requirements` or invent missing requirements. Coordinator requirement clarification and request creation are dependencies.
- Display dates and times in `Asia/Singapore`; compare `timestamptz` values as instants, respecting their offsets.

### Availability, Overlap, and Priority

- `reserved` quantities consume stock only during their recorded reservation period. `equipment_unavailability.status = active` subtracts `quantity_unavailable` during its recorded period; `cancelled` records are ignored. A NULL status is ambiguous and must produce an error rather than being treated as available or unavailable.
- At every point in the requested period, the requested quantity plus concurrent reserved and unavailable quantities must not exceed `equipment.total_quantity`. Do not sum records as concurrent merely because each overlaps a different part of the request.
- Two periods overlap when `A.start_datetime < B.end_datetime` and `B.start_datetime < A.end_datetime`. Periods are half-open: `[start_datetime, end_datetime)`.
- Adjacent periods are allowed. A reservation ending exactly when another begins does not reduce stock for the later period.
- The team-approved acceptance SQL gives priority to earlier feasible `planning` requests using `requested_at`, provisionally allocating their quantities without changing their stored statuses. An earlier request that cannot be fulfilled does not consume a provisional allocation. Equal or missing timestamps requiring a priority decision produce an error rather than a guessed tie-break. Technical Support still reviews each request.
- Equipment becomes available for subsequent periods after its reservation ends, subject to other reservations and maintenance. The user described available equipment as `available`; the existing `equipment` table has no status column, so availability for this story is calculated from quantities and periods. An automatic stored status change after return is not defined by the current schema documentation; see Open Questions.

### Shared Project Constraints

- Use existing Supabase Authentication and the `technical_support` role. A user may hold multiple roles; the prototype role switcher is not proof of access.
- Equipment arrangements belong to the Equipment service.
- If an event explicitly requires no equipment, do not create unnecessary reservations. Missing requests alone do not prove that no equipment is required.
- Saving an equipment reservation does not automatically confirm the event. Venue and technical/equipment arrangements must both be complete before event confirmation.

Sources: user clarifications supplied during story review, [shared project context](../architecture/project_context.md), [database schema and RLS](../architecture/database_schema.md), and [authentication story](event-organiser-login.md). The confirmed clarification `planning` → `reserved` applies to equipment requests; venue-booking status rules do not determine equipment status values.

## Preconditions / Dependencies

- Technical Support has a registered Supabase Auth account, a `profile`, and the `technical_support` role in `user_role`.
- Role-verified Technical Support login uses the existing Supabase application-login flow. `technical_support` is now a supported role; no additional authentication method is introduced.
- An eligible event and a linked Coordinator-created `equipment_reservation` request exist. Required quantity, start/end timestamps, equipment reference, and request timestamp are populated and unambiguous.
- The equipment catalogue and all relevant reservations and maintenance records are accessible under the caller's RLS context, including commitments for other events. Hidden commitments must not make stock appear available.
- RLS permits Technical Support to read the required event details and update the request. The user reports applying Supabase policy changes; their live definitions have not been verified against the local schema documentation.
- The existing unavailability constraint permits `active` and `cancelled`, as confirmed by the user. NULL statuses must fail validation. The acceptance operation and its stock helper must be deployed with the approved definitions before live use.
- The team-approved [acceptance SQL](../database/equipment-acceptance-draft.sql) defines `public.accept_equipment_request(p_reservation_id)` and its stock/priority guards. The application must use this RPC, not separate availability checks followed by a table update. Deployment and live RLS/concurrency verification remain dependencies; this implementation does not apply or modify the SQL.
- The functional specification must be reviewed before it is treated as approved. It defines acceptance targets, not executed test results.

## Test Case Reference

[Functional test specification](../test-cases/reserve-equipment.md), TC-001–TC-006.

Implementation: `app/routes/equipment_reservations.py`, `app/services/equipment_reservation_service.py`, and `app/static/js/equipment-reservations.js`. Automated coverage: `tests/test_equipment_reservations.py` and `tests/equipment-reservations.test.js`. These tests verify RPC delegation, returned-row confirmation, access checks, and UI behavior with simulated responses; they do not establish live RLS or database concurrency guarantees.

## Relevant UML Reference

No equipment-reservation UML currently exists under `docs/uml/`.

The [authentication sequence](../uml/event-organiser-login.puml) illustrates the Supabase session/RLS pattern for organiser access. The [event-change sequence](../uml/Request_Event_Changes.md) describes a separate workflow; neither defines equipment acceptance or Technical Support permissions.

## Implementation Notes

- Follow frontend → Flask route → Equipment service/business logic → Supabase. Put routes in `app/routes/` and business logic in `app/services/`.
- Reuse `create_supabase_client()` / `create_authenticated_supabase_client()` from `app/supabase_client.py` and preserve the caller's authenticated RLS context.
- Extend the existing Technical Support interface with isolated changes. Preserve the shared layout, navigation, forms, styling, and modal patterns.
- Use only the existing `equipment`, `equipment_reservation`, `equipment_unavailability`, `event`, and authentication/role data required by this story. Do not add an equipment status column, a request table, or a new approval workflow.
- Update the existing request identified by `reservation_id`; preserve its event, equipment, requested quantity, period, and Coordinator submission history. Use existing `decided_by` and `decided_at` for the accepting Technical Support decision.
- Display current physical stock using the approved `cs_equipment_free_quantity` helper, which validates commitments and computes the minimum free quantity across the period. Final acceptance calls `accept_equipment_request`; the RPC rechecks stock, eligibility, and priority atomically. Use its returned reservation for confirmation and preserve its idempotent retry behavior. Never fall back to a direct update when an RPC is missing or fails. A displayed stock quantity does not guarantee priority.
- Keep AC5's unavailability message visible to the reviewer. A persistent `notification` record or messages to other users are not required by this story.
- Existing readiness service/frontend code maps `reserved` to the display label `Confirmed`. Preserve that integration; do not store `Confirmed` as a new equipment status or clear reservation history merely to display availability.
- Coordinator request creation, explicit rejection/cancellation workflows, event confirmation, catalogue management, maintenance entry, event changes, and scheduled return processing remain outside this story. Their records may supply preconditions.
- Do not change schema, constraints, status values, RLS, or authentication architecture without team agreement.

## Open Questions

- **Return status:** If automatic removal of stored `reserved` after return is still required, which existing status and return workflow should be used? The availability calculation already releases the quantity for non-overlapping later periods; it does not require deleting history or writing an unsupported `available` status.

## Outstanding Integration Verification

- Verify the reported live policy changes. Local `equipment_reservation` policies already permit Technical Support SELECT/UPDATE, which matches acceptance of existing requests; Technical Support INSERT is not required. Local `event` policies do not document SELECT for a Technical Support-only user. Do not require an extra role or bypass RLS to conceal the gap.
- Verify deployment of the approved RPC, helper functions, and triggers under READ COMMITTED isolation, plus complete caller visibility of affected pools/events under RLS, before claiming live AC6 or TC-004 passed. Manual review or mocked tests do not establish database concurrency safety.
- Preserve the user-confirmed equipment request status `planning` even though some other stories/tests use `requested` for pending equipment. Verify existing live request data and integration callers; do not silently rename statuses or migrate unrelated data.

## Local Verification

- `venv/bin/python -m pytest -q tests/test_equipment_reservations.py tests/test_role_login.py tests/test_auth_service.py tests/test_auth_routes.py`: 40 passed, including 24 equipment tests.
- `node --test tests/equipment-reservations.test.js`: 3 passed (review/confirmation, insufficient stock, and priority/conflict message behavior). JavaScript syntax checks passed.
- Full `venv/bin/python -m pytest -q --tb=no`: 146 passed, 133 failed. The same 133 failures were present after the startup import correction before equipment tests were added; unrelated missing blueprint registrations account for many failures. The original baseline could not collect tests because `app/app.py` imported `events_blueprint`, while `app/routes/events.py` exports `events_bp`. Only that necessary startup import was corrected; unrelated route registrations were not changed.
- No live Supabase test, SQL deployment, or authenticated browser execution was performed. AC6 and TC-004's live concurrency outcome remain unverified.

## Supabase Deployment Recheck — 15 October 2026

- The user reports applying the approved SQL to Supabase. The local SQL definition was not modified or applied by the agent.
- A live call to `accept_equipment_request` using a nonexistent request ID and no user session returned SQLSTATE `42501` with the expected Technical Support authentication requirement. This verifies RPC reachability and rejection of unauthenticated acceptance; no reservation was changed.
- Focused Python tests: 40 passed. JavaScript UI tests: 3 passed. These remain simulated application tests.
- Local configuration supplies the project URL and publishable key, but no Technical Support session or test-account credentials. Successful acceptance, complete RLS visibility, and live concurrent acceptance remain unverified. This recheck updates the earlier deployment-pending notes; it does not establish those authenticated outcomes.
