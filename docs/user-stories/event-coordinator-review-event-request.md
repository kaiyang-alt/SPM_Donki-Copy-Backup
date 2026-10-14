Title
Review Event Request

User Story
“As an Event Coordinator, I want to review event requests so that I can identify missing or unclear requirements.”
Acceptance Criteria
Ensure that the Event Coordinator:
Can view key event request details, including event name, date/time, venue, expected attendance, event requirements, and requested equipment/resources.
Can identify requirements that are missing, incomplete, or unclear based on the information provided.
Can request clarification or amendments by sending a clarification message to the Event Organiser.
When clarification is requested, can update the event request status to “Clarification Required”.
The Event Organiser receives the clarification message and can provide the requested information or amendments.
After the Event Organiser provides the required clarification/amendments, the Event Coordinator can review the updated request and update its status accordingly. 

## Confirmed Customer Clarifications

- “Clarification Required” is the display label for the existing `changes_requested` event status.
- After satisfactory review, the coordinator moves the event to `planning`. If more clarification is needed, the coordinator requests it using `changes_requested`.
- “Venue” in this story means the organiser's venue requirements.
- Coordinator assignment uses `event.coordinator_id`; organiser ownership uses `event.organiser_id`.
- Clarification messages and organiser responses are recorded in `event_action_log.details`, with workflow actions in `action_type`. No separate clarification or response columns are added.

## Implementation Notes

- The existing Supabase login endpoint supports coordinator role verification as well as organiser login.
- Assigned coordinators review request details, equipment reservations, and clarification history. Organisers open events requiring clarification from My Events and submit responses or amendments to documented event fields.
- Organiser responses leave the event in `changes_requested` until coordinator review.
- Event updates, audit entries, and notifications use separate authenticated Supabase calls under existing RLS. A partial failure is reported explicitly; these writes are not an atomic database transaction.

