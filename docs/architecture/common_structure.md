# ConnectSphere Common Structure

## Application Flow

Frontend → Flask Route → Service / Business Logic → Supabase

## Shared Frontend

The approved ConnectSphere light prototype is the frontend baseline.

- HTML: `app/templates/index.html`
- CSS: `app/static/css/styles.css`
- JavaScript: `app/static/js/app.js`

All user stories should extend this existing frontend rather than create a separate UI.

## Backend

- Flask routes: `app/routes/`
- Business logic: `app/services/`
- Shared Supabase connection: `app/supabase_client.py`

## Service Ownership

### User / Authentication
- Supabase Authentication
- `profile`
- `user_role`

### Event
- `event`
- `event_action_log`
- `event_change_request`
- `event_coordinator_reassignment`

### Venue
- `venue`
- `venue_booking`
- `venue_block`

### Equipment
- `equipment`
- `equipment_reservation`
- `equipment_unavailability`

### Registration
- `registration`

### Notification
- `notification`

## Rule

A user story should place its route and business logic under the service that owns the functionality.

Do not introduce a new project structure, database table, authentication method or frontend design without team agreement.