# Configure Venue Setup and Turnaround Time

## User Story

As Venue Staff, I want to configure each venue's setup and turnaround durations
and see the booking conflicts caused by changes, so that venue availability
reflects the full preparation, use and reset period and affected Event
Coordinators can review their arrangements without losing existing bookings.

## Acceptance Criteria

1. **AC1 — Configure per-venue durations:** Authorised Venue Staff can set and
   change a venue's setup duration and turnaround duration as distinct venue
   operating information. The saved values are available when the venue
   information is viewed again. Setting one venue's configuration does not
   overwrite another venue's settings.
2. **AC2 — Full occupied period:** For an event using a venue with configured
   durations, availability and conflict calculations include setup before its
   scheduled start and turnaround after its scheduled end. An event from 10:00
   to 12:00 with 30 minutes setup and 45 minutes turnaround occupies 09:30–12:45.
3. **AC3 — Consistent consumer use, including holds:** Venue availability,
   venue search, booking/request conflict checks and tentative-hold placement
   use the configured durations and the same occupied-period interpretation.
   Conflicts occurring only within setup or turnaround are recognised.
4. **AC4 — Reassess existing bookings:** When configured durations change,
   existing bookings, including already-approved or confirmed bookings, are
   assessed using the changed values. Problematic bookings are identified and
   flagged without removing the original booking information.
5. **AC5 — Save with conflicts and show Staff impacts:** A configuration change
   is not rejected solely because it creates conflicts with existing bookings.
   Venue Staff can save it and see identified conflicts. Saving does not
   automatically resolve, cancel or replace affected arrangements.
6. **AC6 — Calendar conflict visibility:** After a configuration change, relevant
   authorised Staff and Coordinator availability views retain existing bookings
   and flag resulting overlapping occupied periods using the changed values.
7. **AC7 — Notify affected Coordinators:** When a buffer change creates
   identified booking conflicts, relevant affected Event Coordinators receive
   notifications. No fixed channel, exact wording or numerical latency is
   required by this story.
8. **AC8 — Preserve Coordinator assessment and role boundaries:** Venue Staff
   maintain configuration. Relevant Event Coordinators retain final arrangement
   assessment/approval following a flagged conflict. Buffer changes do not
   automatically select or approve replacement venues, and Coordinators do not
   gain Venue Staff configuration-edit authority.

## Relevant Customer Clarifications

Evidence is supplied externally in
`C:\Users\aiwei\Documents\SMU\y3\SPM\customer-requirements`.
Requirement precedence is defined in `docs/requirements/README.md`.
Week 4 Project Instructions defines core Release 1 scope; behavioural precedence
is Week 9, Week 7, Week 4 clarification, Week 2 clarification, then Week 1.

| Source | Relevant support |
| --- | --- |
| Week 1 Customer Briefing.docx, Venue Staff / Setup and Turnaround Time | Staff maintain venue information; preparation before and reset after an event affect availability. |
| G1G2 Week2 Clarification.xlsx, Sheet1 C23:D23 and C43:D43 | Earlier turnaround deferral is superseded by mandatory Week 7 changes and Week 9 confirmation. |
| G1G2 Week2 Clarification.xlsx, Sheet1 C9:D9 and C45:D45 | Notification channel is flexible; Coordinators and Venue Staff can view relevant availability. |
| Week 4 Project Instructions.docx, First Release — Core Functionality | Authorisation, catalogue, calendar, search, booking/conflict detection and notifications form coherent core workflows. |
| G1G2_Answers_week4 v1.0.xlsx, Sheet1 C8:D8 | Operational venue changes inform the Coordinator for re-evaluation; later buffer-specific answers govern this story. |
| Week 7 Customer Changes.pdf, page 1 change 1 | Configurable setup/turnaround per venue is mandatory for Release 1; include full occupancy and identify problematic existing bookings without silently removing them. Example: 10:00–12:00 plus 30/45 minutes occupies 09:30–12:45. |
| G1G2 clarification Answers wk9.xlsx, G1G2 C13:D13 and C39:D39 | Venue operating information includes per-venue values set by Venue Staff; use buffers for availability, conflicts and holds. |
| G1G2 clarification Answers wk9.xlsx, G1G2 C40:D40 and C48:D48 | Assess existing approved bookings under changed values; save rather than reject solely for resulting conflicts; retain information and Coordinator final assessment. |
| G1G2 clarification Answers wk9.xlsx, G1G2 C47:D47 | Staff see conflicts upon setting buffers, the calendar flags overlapping periods and affected Coordinators receive notifications. |
| G1G2 clarification Answers wk9.xlsx, G1G2 C49:D49 | Preparation/reset between uses and holds is supported; extra maintenance-block buffers remain unresolved. |

## B1 Shared Consumer Contract

- B1 provides authoritative per-venue configured setup/turnaround durations and
  one reusable occupied-period interpretation.
- Occupied start = scheduled start minus configured setup duration.
- Occupied end = scheduled end plus configured turnaround duration.
- Event/booking and tentative-hold occupancy use that interpretation. The
  approved 10:00–12:00 / 30-minute / 45-minute example yields 09:30–12:45.
- Availability calendar, venue search, booking/request conflict checks,
  tentative-hold placement, operational-unavailability impact detection and
  later relevant readiness integrations consume the same interpretation.
- Changed values are used to reassess existing bookings and expose resulting
  conflicts; consumers must not silently grandfather those bookings out.
- Consumers do not invent missing-value defaults, alternative formulas or
  per-booking override precedence.
- Contract A consumes full confirmed-booking occupancy to derive operational
  block impacts. This contract does not decide extra buffers on a block itself.
- This is a business/consumer contract, not a persistence, API or database design.

## Ownership Boundaries

- This story owns configuration maintenance, common occupancy semantics,
  buffer-change conflict assessment, save-time Staff feedback, saving despite
  resulting conflicts and affected-Coordinator notices.
- Manage Venue Availability owns its calendar presentation and operational
  block record/lift effects, consuming B1 values and resulting flags. Its
  approved Contract A remains paused pending delivery of the shared contract.
- Search and booking/request/review owners integrate occupancy with their own
  workflows, suitability and duplicate/conflict protections.
- B2 / Manage Tentative Venue Hold Expiry owns validity, expiry, extensions and
  reminders. This story does not change hold lifecycle.
- C1 / multiple-venue and replacement booking owner retains explicit replacement
  request/approval and preservation of independent arrangements.
- C2 / readiness/status owner retains required-arrangement assessment, safety
  review and reconfirmation. A buffer edit does not itself invoke Contract A's
  operational-block status transition.
- Notification/assignment owners support authoritative recipient routing; no
  fallback recipient is invented.
- Shared baseline updates belong to a later dedicated synchronisation task,
  not automatic edits to project_context.md or common_structure.md.

## Preconditions / Dependencies

- Authenticated authorised Venue Staff can maintain the relevant venue
  information; authorised Staff and Coordinators can view relevant availability.
- Venue information, scheduled booking/hold times, original arrangements and
  relevant assigned Coordinators are available to the supported workflows.
- Configuration persistence, authorised shared consumption and notification
  capability must support the approved behaviour. Their technical design and
  readiness are assessed only after functional-test approval.
- Calendar/search/request/hold consumers integrate B1 consistently. B2 supplies
  hold validity; this story must not implement expiry to supply that dependency.
- Missing-value and exception behaviours below remain open, not defaulted by
  implementation convenience.

## Test Case Reference

`docs/test-cases/configure-venue-setup-and-turnaround-time.md`

## Open Questions

1. **Missing/default durations:** What applies before a venue has configured
   values, including existing venues? No zero default or automatic backfill is
   approved.
2. **Duration limits/precision:** Are zero values permitted, and are there
   business minimums, maximums or precision/increment restrictions? Minutes in
   the example do not prescribe an integer-only field or arbitrary bounds.
3. **Per-booking overrides:** Week 9 D39 confirms per-venue settings but does
   not explicitly authorise per-event/booking overrides or precedence.
4. **Existing holds/requests after buffer changes:** What lifecycle effects, if
   any, follow a buffer change that affects an already-existing hold/request?
   Do not invent invalidation, suspension, cancellation or expiry changes.
5. **Maintenance-block buffers:** Week 9 D49 does not conclusively settle extra
   buffers around operational blocks. Mandatory event/hold buffers remain clear.
6. **Exact-touch intervals:** Are fully buffered intervals meeting exactly at
   one instant conflicting? Existing code is not customer authority.
7. **Missing Coordinator:** What happens when a changed buffer affects an event
   with no assigned Coordinator? No fail-closed default, silent omission or
   escalation recipient is approved.

## Implementation Notes

No persistence, SQL, route, RPC, locking, retry mechanism or UI representation
is selected at Gate 1. Do not derive requirements from current schema limits.
No automatic cancellation, replacement or event-status transition is introduced
by saving buffer configuration. Relevant downstream assessment stays with its
owner.

## Requirement Revision

Classification: NEW STORY REQUIRED. Human Gate 1 explicitly approved in the
current session. AC1–AC8 above are the approved baseline; open questions remain
tracked separately. Functional specification is proposed at Human Gate 2;
implementation and shared architecture execution are not authorised.
