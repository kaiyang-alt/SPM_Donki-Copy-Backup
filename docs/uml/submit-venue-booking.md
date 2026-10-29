# Venue Alternatives — Sequence

```mermaid
sequenceDiagram
    actor Coordinator
    actor VenueStaff as Venue Staff
    participant UI as Existing ConnectSphere UI
    participant Flask as Venue routes / service
    participant DB as Authenticated Supabase

    Coordinator->>UI: Select assigned planning event, venue, period and layout
    UI->>Flask: Check availability
    Flask->>DB: cs_venue_period_available (occupied period)
    DB-->>UI: Availability decision or validation error, via Flask
    Coordinator->>UI: Submit alternative
    UI->>Flask: POST /api/venue-bookings
    Flask->>DB: Recheck availability; insert requested booking and its layout
    Note over DB: Write guard revalidates; pending alternatives do not reserve the venue
    DB-->>UI: Saved pending alternative, via Flask
    Note over Coordinator,DB: Repeat for alternatives with independent periods/layouts
    VenueStaff->>UI: Confirm selected alternative
    UI->>Flask: Existing approval endpoint
    Flask->>DB: confirm_venue_booking(booking_id)
    Note over DB: Shared lock; current conflicts and equipment guards checked
    alt Confirmation succeeds
        DB->>DB: Confirm selection; cancel same-event pending siblings atomically
        DB-->>UI: Actual saved row, via Flask
        UI->>Flask: Reload saved bookings
    else Validation or cancellation fails
        DB->>DB: Roll back all changes
        DB-->>UI: Clear error, via Flask; no optimistic confirmation
    end
```

Event status stays unchanged. Equipment review may proceed in parallel; final
equipment commitment requires the confirmed venue period. Notification delivery
remains blocked on the existing venue-staff assignment/permission dependency.
