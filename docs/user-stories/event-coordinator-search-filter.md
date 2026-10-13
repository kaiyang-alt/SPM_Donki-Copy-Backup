# Search and Filter Suitable Venues

## User Story

As an Event Coordinator, I want to search and filter ConnectSphere venues using the complete setup, event, and turnaround period so that I can identify a suitable venue or venue combination for an event request.

## Acceptance Criteria

- AC1: The coordinator can configure setup time before the requested event start time.
- AC2: The coordinator can configure turnaround time after the requested event end time.
- AC3: Setup, event, and turnaround time form the complete occupied period used for conflict detection.
- AC4: A search can specify that an event requires multiple venues.
- AC5: Every venue in a returned combination satisfies its relevant capacity, layout, facility, and availability requirements.
- AC6: A venue is excluded when any part of its occupied period overlaps a confirmed booking.
- AC7: A venue is excluded when any part of its occupied period overlaps active temporary unavailability.
- AC8: An existing occupied period ending exactly when the requested occupied period starts, or starting exactly when it ends, is non-overlapping.
- AC9: Results show the applicable setup time, event period, turnaround time, and temporary-unavailability information.
- AC10: The application displays “No suitable venues found” when no individual venue or required combination satisfies all requirements.
- AC11: Existing capacity, layout, facility, editable-search, and repeat-search behaviour remains available.

## Relevant Customer Clarifications

- Venue suitability must include setup time, turnaround time, multi-venue events, and temporary venue unavailability.
- Existing search and filtering behaviour remains unchanged unless affected by these additions.
- Confirmed bookings are the only booking status that excludes a venue in this search.
- Active `venue_block` records represent temporary venue unavailability.
- Availability uses half-open interval overlap: an existing interval overlaps only when its start is before the requested occupied end and its end is after the requested occupied start.

## Preconditions / Dependencies

- The Event Coordinator is authenticated.
- Active venues and their capacities, supported layouts, and facilities exist in Supabase.
- Confirmed bookings use `venue_booking` and temporary unavailability uses `venue_block`.

## Test Case Reference

`docs/test-cases/event-coordinator-search-filter.md`

## Relevant UML Reference

- Not required.

## Implementation Notes

- Setup and turnaround durations are search criteria and do not require new database columns.
- Multi-venue requirements are supplied per venue during the search and do not alter the event or booking schema.
- The existing `venue.capacity` is used for layouts represented as a list or an enabled object value in `supported_layouts`.
- If an existing `supported_layouts` object supplies a numeric capacity or nested `capacity`, that layout-specific value is used.
- `facilities` supports the existing JSONB column as either a list of facility names or an object whose enabled keys are facility names.
