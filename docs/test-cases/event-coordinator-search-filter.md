# Test Cases — Search and Filter Suitable Venues

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | Search for one suitable venue using setup, event, and turnaround periods and display the applicable timing and availability information. |
| TC-002 | Boundary | Exclude confirmed bookings that overlap the complete occupied period while treating exact occupied-period boundaries as non-overlapping. |
| TC-003 | Boundary | Exclude temporary venue unavailability that overlaps the complete occupied period while treating exact boundaries as non-overlapping. |
| TC-004 | Happy Path | Find a combination of multiple venues in which every venue satisfies its relevant capacity, layout, facility, and availability requirements. |
| TC-005 | Happy Path | Display the no-results message when no venue or required multi-venue combination is suitable, then allow the criteria to be changed and searched again. |

### TC-001 — Find a Venue for the Complete Occupied Period

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that setup and turnaround time are included in the availability search and displayed with the event period. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- The Alcove supports Theatre layout for 180 guests and has Projector and Sound system.<br>- Small Room supports Theatre layout for 120 guests and has the required facilities.<br>- Campus Green supports Theatre layout for 300 guests but lacks Projector.<br>- The Alcove has no confirmed booking or temporary unavailability overlapping the required occupied period. |
| **Test Steps** | 1. Open Find Venues.<br>2. Enter the event start and end date/time.<br>3. Enter the setup and turnaround duration.<br>4. Enter the guest count, layout, and required facilities.<br>5. Search.<br>6. Review the results and displayed timing information. |
| **Test Data** | `Event Start`: `20 November 2026, 09:00`<br>`Event End`: `20 November 2026, 17:00`<br>`Setup Time`: `60 minutes`<br>`Turnaround Time`: `30 minutes`<br>`Complete Occupied Period`: `20 November 2026, 08:00–17:30`<br>`Guest Count`: `150`<br>`Layout`: `Theatre`<br>`Facilities`: `Projector, Sound system` |
| **Expected Result** | - The Alcove is displayed as suitable.<br>- Small Room is excluded because its capacity is insufficient.<br>- Campus Green is excluded because it lacks a required facility.<br>- The result displays The Alcove’s name, Theatre capacity, and facilities.<br>- The result displays the 60-minute setup period, the 09:00–17:00 event period, and the 30-minute turnaround period.<br>- The result indicates that The Alcove has no temporary unavailability conflicting with the complete 08:00–17:30 occupied period. |

### TC-002 — Apply Confirmed-Booking Boundaries to the Occupied Period

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Boundary |
| **Test Scenario** | Verify confirmed-booking overlap and exact-boundary behaviour against the setup, event, and turnaround periods combined. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- The Alcove, Auditorium A, and Seminar Room 3.2 satisfy the entered capacity, layout, and facility requirements.<br>- The Alcove has a confirmed booking ending exactly at 08:00.<br>- Auditorium A has a confirmed booking from 07:30 to 08:01.<br>- Seminar Room 3.2 has a confirmed booking beginning exactly at 17:30.<br>- None of the venues has overlapping temporary unavailability. |
| **Test Steps** | 1. Open Find Venues.<br>2. Enter the event period, setup time, turnaround time, and venue requirements.<br>3. Search.<br>4. Review the results. |
| **Test Data** | `Event Start`: `20 November 2026, 09:00`<br>`Event End`: `20 November 2026, 17:00`<br>`Setup Time`: `60 minutes`<br>`Turnaround Time`: `30 minutes`<br>`Complete Occupied Period`: `20 November 2026, 08:00–17:30`<br>`Guest Count`: `100`<br>`Layout`: `Theatre`<br>`Facilities`: `Projector` |
| **Expected Result** | - The Alcove is displayed because its confirmed booking ends exactly when the required occupied period starts.<br>- Auditorium A is excluded because its confirmed booking overlaps one minute of the setup period.<br>- Seminar Room 3.2 is displayed because its confirmed booking begins exactly when the required occupied period ends.<br>- Availability is evaluated against 08:00–17:30 rather than only the 09:00–17:00 event period. |

### TC-003 — Apply Temporary-Unavailability Boundaries to the Occupied Period

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Boundary |
| **Test Scenario** | Verify temporary-unavailability overlap and exact-boundary behaviour against the complete occupied period. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- The Alcove, Auditorium A, and Seminar Room 3.2 satisfy the entered capacity, layout, and facility requirements.<br>- The Alcove has temporary unavailability ending exactly at 08:00.<br>- Auditorium A has temporary unavailability from 17:00 to 17:01.<br>- Seminar Room 3.2 has temporary unavailability beginning exactly at 17:30.<br>- None of the venues has an overlapping confirmed booking. |
| **Test Steps** | 1. Open Find Venues.<br>2. Enter the event period, setup time, turnaround time, and venue requirements.<br>3. Search.<br>4. Review the results and temporary-unavailability information. |
| **Test Data** | `Event Start`: `20 November 2026, 09:00`<br>`Event End`: `20 November 2026, 17:00`<br>`Setup Time`: `60 minutes`<br>`Turnaround Time`: `30 minutes`<br>`Complete Occupied Period`: `20 November 2026, 08:00–17:30`<br>`Guest Count`: `100`<br>`Layout`: `Theatre`<br>`Facilities`: `Projector` |
| **Expected Result** | - The Alcove is displayed because its temporary unavailability ends exactly when the occupied period starts.<br>- Auditorium A is excluded because its temporary unavailability overlaps the turnaround period.<br>- Seminar Room 3.2 is displayed because its temporary unavailability begins exactly when the occupied period ends.<br>- Each displayed result shows the applicable temporary-unavailability information for the requested occupied period. |

### TC-004 — Find a Suitable Multi-Venue Combination

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that an event requiring multiple venues returns only combinations in which every venue satisfies its relevant requirements for the complete occupied period. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- The event requires two venues.<br>- The Alcove supports Theatre layout for 180 guests, has Projector and Sound system, and is available for the complete occupied period.<br>- Workshop Room B supports Classroom layout for 60 guests, has Whiteboard and Video conferencing, and is available for the complete occupied period.<br>- Small Room supports Theatre layout for only 120 guests.<br>- Workshop Room C supports Classroom layout for 60 guests but lacks Video conferencing.<br>- Auditorium A satisfies the first venue’s capacity, layout, and facility requirements but has temporary unavailability during setup. |
| **Test Steps** | 1. Open Find Venues.<br>2. Specify that the event requires two venues.<br>3. Enter the event period, setup time, and turnaround time.<br>4. Enter the requirements for each required venue.<br>5. Search.<br>6. Review the returned venue combinations. |
| **Test Data** | `Number of Venues`: `2`<br>`Event Start`: `20 November 2026, 09:00`<br>`Event End`: `20 November 2026, 17:00`<br>`Setup Time`: `60 minutes`<br>`Turnaround Time`: `30 minutes`<br>`Venue 1 Guest Count`: `150`<br>`Venue 1 Layout`: `Theatre`<br>`Venue 1 Facilities`: `Projector, Sound system`<br>`Venue 2 Guest Count`: `50`<br>`Venue 2 Layout`: `Classroom`<br>`Venue 2 Facilities`: `Whiteboard, Video conferencing` |
| **Expected Result** | - The combination of The Alcove and Workshop Room B is displayed.<br>- Each venue in the combination satisfies its corresponding capacity, layout, facility, and availability requirements.<br>- Small Room is not used because it cannot satisfy Venue 1’s capacity requirement.<br>- Workshop Room C is not used because it lacks a required Venue 2 facility.<br>- Auditorium A is not used because its temporary unavailability overlaps the complete occupied period.<br>- The result displays the setup period, event period, turnaround period, and applicable temporary-unavailability information for both venues. |

### TC-005 — Show No Results and Search Again

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-005 |
| **Category** | Happy Path |
| **Test Scenario** | Verify the no-results message when no suitable individual venue or required combination exists and verify that the coordinator can revise the search. |
| **Pre-conditions** | - An Event Coordinator is authenticated.<br>- No pair of venues satisfies all initial multi-venue requirements for the complete occupied period.<br>- The Alcove satisfies the revised single-venue requirements and is available for the revised occupied period. |
| **Test Steps** | 1. Enter the initial multi-venue criteria and search.<br>2. Review the no-results state.<br>3. Change the search to the revised single-venue criteria.<br>4. Search again.<br>5. Review the new results. |
| **Test Data** | `Initial Number of Venues`: `2`<br>`Event Start`: `20 November 2026, 09:00`<br>`Event End`: `20 November 2026, 17:00`<br>`Setup Time`: `60 minutes`<br>`Turnaround Time`: `30 minutes`<br>`Initial Venue 1 Guest Count`: `500`<br>`Initial Venue 1 Layout`: `Banquet`<br>`Initial Venue 1 Facilities`: `Video conferencing, Sound system`<br>`Initial Venue 2 Guest Count`: `300`<br>`Initial Venue 2 Layout`: `Theatre`<br>`Initial Venue 2 Facilities`: `Projector`<br>`Revised Number of Venues`: `1`<br>`Revised Guest Count`: `150`<br>`Revised Layout`: `Theatre`<br>`Revised Facilities`: `Projector, Sound system` |
| **Expected Result** | - The initial search displays exactly “No suitable venues found”.<br>- No incomplete or partially suitable venue combination is displayed.<br>- The search criteria remain editable.<br>- The revised search replaces the no-results state with The Alcove.<br>- The revised result displays The Alcove’s venue information and availability across the setup, event, and turnaround periods. |
