# Test Cases — Search and Filter Suitable Venues

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | Enter all criteria and display only venues matching the requested period, guest count, layout, and facilities. |
| TC-002 | Boundary | Exclude confirmed bookings that overlap while allowing bookings at exact request boundaries. |
| TC-003 | Boundary | Exclude active maintenance closures that overlap while allowing closures at exact request boundaries. |
| TC-004 | Happy Path | Display the no-results message, allow criteria changes, and search again. |

### TC-001 — Find Venues Matching All Criteria

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that only venues satisfying every entered requirement for the full requested period are displayed. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- The Alcove supports Theatre layout for 180 guests and has Projector and Sound system.<br>- Small Room supports Theatre layout for 120 guests and has both facilities.<br>- Campus Green supports Theatre layout for 300 guests but lacks Projector.<br>- The Alcove has no overlapping confirmed booking or active maintenance closure. |
| **Test Steps** | 1. Open Find Venues.<br>2. Enter the start and end date/time, guest count, layout, and facilities.<br>3. Search.<br>4. Review the results. |
| **Test Data** | `Start`: `20 November 2026, 09:00`<br>`End`: `20 November 2026, 17:00`<br>`Guest Count`: `150`<br>`Layout`: `Theatre`<br>`Facilities`: `Projector, Sound system` |
| **Expected Result** | - The Alcove is displayed.<br>- Small Room is excluded because its capacity is insufficient.<br>- Campus Green is excluded because it lacks a required facility.<br>- The result shows The Alcove's name, Theatre capacity, facilities, and availability for the full period. |

### TC-002 — Apply Confirmed-Booking Boundaries

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Boundary |
| **Test Scenario** | Verify confirmed-booking overlap and exact-boundary behavior. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- All three venues match the capacity, layout, and facilities.<br>- The Alcove has a `confirmed` booking ending exactly at 09:00.<br>- Auditorium A has a `confirmed` booking from 16:59 to 18:00.<br>- Seminar Room 3.2 has a `confirmed` booking beginning exactly at 17:00.<br>- None has an overlapping active maintenance closure. |
| **Test Steps** | 1. Open Find Venues.<br>2. Enter the search criteria.<br>3. Search.<br>4. Review the results. |
| **Test Data** | `Start`: `20 November 2026, 09:00`<br>`End`: `20 November 2026, 17:00`<br>`Guest Count`: `100`<br>`Layout`: `Theatre`<br>`Facilities`: `Projector` |
| **Expected Result** | - The Alcove is displayed because its booking ends at the requested start.<br>- Auditorium A is excluded because its confirmed booking overlaps the request.<br>- Seminar Room 3.2 is displayed because its booking starts at the requested end. |

### TC-003 — Apply Maintenance-Closure Boundaries

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Boundary |
| **Test Scenario** | Verify active maintenance-closure overlap and exact-boundary behavior. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- All three venues match the capacity, layout, and facilities.<br>- The Alcove has an active closure ending exactly at 09:00.<br>- Auditorium A has an active closure from 12:00 to 13:00.<br>- Seminar Room 3.2 has an active closure beginning exactly at 17:00.<br>- None has an overlapping confirmed booking. |
| **Test Steps** | 1. Open Find Venues.<br>2. Enter the search criteria.<br>3. Search.<br>4. Review the results. |
| **Test Data** | `Start`: `20 November 2026, 09:00`<br>`End`: `20 November 2026, 17:00`<br>`Guest Count`: `100`<br>`Layout`: `Theatre`<br>`Facilities`: `Projector` |
| **Expected Result** | - The Alcove is displayed because its closure ends at the requested start.<br>- Auditorium A is excluded because its closure overlaps the request.<br>- Seminar Room 3.2 is displayed because its closure starts at the requested end. |

### TC-004 — Search Again After No Results

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Happy Path |
| **Test Scenario** | Verify the no-results message and a revised search. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- No venue meets the initial criteria.<br>- The Alcove meets the revised criteria and is available for the requested period. |
| **Test Steps** | 1. Enter the initial criteria and search.<br>2. Review the no-results state.<br>3. Change the guest count, layout, and facilities.<br>4. Search again.<br>5. Review the new results. |
| **Test Data** | `Start`: `20 November 2026, 09:00`<br>`End`: `20 November 2026, 17:00`<br>`Initial Guest Count`: `500`<br>`Initial Layout`: `Banquet`<br>`Initial Facilities`: `Video conferencing, Sound system`<br>`Revised Guest Count`: `150`<br>`Revised Layout`: `Theatre`<br>`Revised Facilities`: `Projector, Sound system` |
| **Expected Result** | - The initial search displays exactly “No suitable venues found.”<br>- The criteria remain editable.<br>- The revised search replaces the no-results state with matching results.<br>- The Alcove displays its name, Theatre capacity, facilities, and full-period availability. |

## Implementation Decisions

- `venue.capacity` applies to supported layouts unless `supported_layouts` contains a numeric or nested layout-specific capacity.
- `facilities` and `supported_layouts` may use JSON arrays or JSON objects, consistent with the existing JSONB columns.
