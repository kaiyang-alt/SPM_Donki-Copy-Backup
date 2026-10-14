# Submit Event Request

## User Story

As an Event Organiser, I want to submit my event requirements to ConnectSphere so that I can start the planning process for my event.

## Acceptance Criteria

The Event Organiser can:

- Enter the event name, description, purpose, category, preferred date and time, expected number of attendees, venue and room layout, accessibility and facility requirements, equipment and technical support requirements, registration requirements, and any special arrangements.
- Save an incomplete event request as a draft before submission.
- Review and modify a draft before submitting it.
- Submit an event request when the mandatory information is complete: event name, preferred date and time, and expected number of attendees.
- Be prevented from submitting an event request when any mandatory information is missing and be shown which required fields need to be completed.
- Receive confirmation that the request was successfully submitted and see its status as `requested`.

## Preconditions / Dependencies

- The Event Organiser is authenticated using the existing Supabase Authentication setup and has the `event_organiser` role.
- The existing event schema and Row Level Security policies must support an organiser creating, viewing, and updating their own event request, including saving an incomplete request with status `draft`. This support has not yet been confirmed.

## Test Case Reference

`docs/test-cases/submit-event-request.md`

## Implementation Notes

- Save incomplete event requests using the existing `draft` status.
- Use the existing `requested` status after submission; do not introduce a separate `Submitted` event status.
