Title
Search and Filter Suitable Venues 
User Story

“As an Event Coordinator, I want to search and filter ConnectSphere venues by the requested date and time, guest count, room layout, and required facilities so I can identify suitable venues for an event request.”
Acceptance Criteria
Ensure that the Event Coordinator can:
Allow the coordinator to enter a start date and time, end date and time, guest count, required room layout, and required facilities.
Show only venues matching all entered requirements, with capacity sufficient for the guest count in the requested layout.
Exclude venues with a confirmed booking or maintenance closure overlapping any part of the requested period. An existing booking ending exactly at the requested start time, or starting exactly at the requested end time, does not overlap.
Show each matching venue’s name, capacity for the requested layout, facilities, and availability for the full requested period.
If no venue matches, display “No suitable venues found.”
Allow the coordinator to change the search criteria and search again.

## Implementation Notes

- The existing `venue.capacity` is used for layouts represented as a list or an enabled object value in `supported_layouts`.
- If an existing `supported_layouts` object supplies a numeric capacity or a nested `capacity`, that layout-specific value is used.
- `facilities` supports the existing JSONB column as either a list of facility names or an object whose enabled keys are facility names.
- Availability uses half-open interval overlap: an existing interval overlaps only when its start is before the requested end and its end is after the requested start.

## Test Case Reference

`docs/test-cases/event-coordinator-search-filter.md`

