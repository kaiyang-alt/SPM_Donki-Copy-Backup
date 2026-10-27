from app.supabase_client import create_authenticated_supabase_client


LEAD_ROLE = "event_coordinator_lead"
COORDINATOR_ROLE = "event_coordinator"


class CoordinatorLeadAssignmentError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def get_assignment_context(access_token):
    client, _ = _lead_session(access_token)
    try:
        events = (
            client.table("event")
            .select(
                "event_id,name,status,organiser_id,preferred_start_datetime,"
                "preferred_end_datetime,expected_attendance,coordinator_id"
            )
            .eq("status", "requested")
            .is_("coordinator_id", "null")
            .order("created_at")
            .execute()
            .data
            or []
        )
        role_rows = (
            client.table("user_role")
            .select("user_id")
            .eq("role", COORDINATOR_ROLE)
            .execute()
            .data
            or []
        )
        coordinator_ids = {
            row.get("user_id") for row in role_rows if row.get("user_id")
        }
        profiles = (
            client.table("profile")
            .select("user_id,name")
            .eq("active", True)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise CoordinatorLeadAssignmentError(
            "Unable to load coordinator assignment information.", 502
        ) from exc

    coordinators = [
        {"user_id": row.get("user_id"), "name": row.get("name") or "Unnamed coordinator"}
        for row in profiles
        if row.get("user_id") in coordinator_ids
    ]
    coordinators.sort(key=lambda row: row["name"].casefold())
    return {"events": events, "coordinators": coordinators}


def get_reassignment_context(access_token):
    client, _ = _lead_session(access_token)
    try:
        events = (
            client.table("event")
            .select(
                "event_id,name,status,organiser_id,preferred_start_datetime,"
                "preferred_end_datetime,coordinator_id"
            )
            .not_.is_("coordinator_id", "null")
            .order("preferred_start_datetime")
            .execute()
            .data
            or []
        )
        coordinators = _coordinators(client)
    except Exception as exc:
        raise CoordinatorLeadAssignmentError(
            "Unable to load coordinator reassignment information.", 502
        ) from exc

    coordinator_names = {
        coordinator["user_id"]: coordinator["name"] for coordinator in coordinators
    }
    for event in events:
        event["coordinator_name"] = coordinator_names.get(event.get("coordinator_id"))
    return {"events": events, "coordinators": coordinators}


def assign_event(access_token, event_id, coordinator_id):
    client, lead_id = _lead_session(access_token)
    coordinator_id = str(coordinator_id or "").strip()
    if not coordinator_id:
        raise CoordinatorLeadAssignmentError("An Event Coordinator is required.")

    try:
        coordinator_roles = (
            client.table("user_role")
            .select("role")
            .eq("user_id", coordinator_id)
            .eq("role", COORDINATOR_ROLE)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not coordinator_roles:
            raise CoordinatorLeadAssignmentError(
                "The selected user is not an Event Coordinator."
            )

        profile_rows = (
            client.table("profile")
            .select("name")
            .eq("user_id", coordinator_id)
            .eq("active", True)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not profile_rows:
            raise CoordinatorLeadAssignmentError(
                "The selected Event Coordinator is not active."
            )

        event_rows = (
            client.table("event")
            .select("event_id,name,status,organiser_id,coordinator_id")
            .eq("event_id", event_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not event_rows:
            raise CoordinatorLeadAssignmentError("Event request not found.", 404)
        event = event_rows[0]
        if event.get("status") != "requested":
            raise CoordinatorLeadAssignmentError(
                "Only requested events can be assigned.", 409
            )
        if event.get("coordinator_id"):
            raise CoordinatorLeadAssignmentError(
                "This event request is already assigned.", 409
            )

        assigned = (
            client.rpc(
                "assign_unassigned_event",
                {
                    "p_event_id": event_id,
                    "p_coordinator_id": coordinator_id,
                },
            )
            .execute()
            .data
        )
        if not assigned:
            raise CoordinatorLeadAssignmentError(
                "The request changed or was assigned by another Lead. Reload it before retrying.",
                409,
            )
    except CoordinatorLeadAssignmentError:
        raise
    except Exception as exc:
        message = str(exc).lower()
        if "no longer available for assignment" in message:
            raise CoordinatorLeadAssignmentError(
                "The request changed or was assigned by another Lead. Reload it before retrying.",
                409,
            ) from exc
        if "not an active event coordinator" in message:
            raise CoordinatorLeadAssignmentError(
                "The selected Event Coordinator is not active."
            ) from exc
        raise CoordinatorLeadAssignmentError(
            "Unable to assign the event request.", 502
        ) from exc

    if isinstance(assigned, list):
        assigned = assigned[0]
    assigned["coordinator_name"] = assigned.get("coordinator_name") or profile_rows[
        0
    ].get("name")
    assigned["assigned_by"] = assigned.get("assigned_by") or lead_id
    return assigned


def reassign_event(access_token, event_id, coordinator_id):
    client, lead_id = _lead_session(access_token)
    coordinator_id = str(coordinator_id or "").strip()
    if not coordinator_id:
        raise CoordinatorLeadAssignmentError("A replacement Event Coordinator is required.")

    try:
        coordinator_roles = (
            client.table("user_role")
            .select("role")
            .eq("user_id", coordinator_id)
            .eq("role", COORDINATOR_ROLE)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not coordinator_roles:
            raise CoordinatorLeadAssignmentError(
                "The selected user is not an Event Coordinator."
            )

        event_rows = (
            client.table("event")
            .select("event_id,name,status,organiser_id,coordinator_id")
            .eq("event_id", event_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not event_rows:
            raise CoordinatorLeadAssignmentError("Event not found.", 404)
        event = event_rows[0]
        previous_coordinator_id = event.get("coordinator_id")
        if not previous_coordinator_id:
            raise CoordinatorLeadAssignmentError(
                "This event is unassigned. Use the assignment workflow instead.", 409
            )
        if previous_coordinator_id == coordinator_id:
            raise CoordinatorLeadAssignmentError(
                "Select a different Event Coordinator for reassignment."
            )

        now = datetime.now(timezone.utc).isoformat()
        update = (
            client.table("event")
            .update({"coordinator_id": coordinator_id, "updated_at": now})
            .eq("event_id", event_id)
            .eq("coordinator_id", previous_coordinator_id)
            .execute()
            .data
            or []
        )
        if not update:
            raise CoordinatorLeadAssignmentError(
                "The assignment changed before reassignment completed. Reload it before retrying.",
                409,
            )

        event_name = event.get("name") or "Untitled event"
        notifications = [
            {
                "event_id": event_id,
                "recipient_id": previous_coordinator_id,
                "type": "coordinator_reassigned",
                "message": f"You are no longer assigned to {event_name}.",
                "created_at": now,
            },
            {
                "event_id": event_id,
                "recipient_id": coordinator_id,
                "type": "coordinator_reassigned",
                "message": f"You have been assigned to {event_name}.",
                "created_at": now,
            },
            {
                "event_id": event_id,
                "recipient_id": event.get("organiser_id"),
                "type": "coordinator_reassigned",
                "message": f"The Event Coordinator for {event_name} has changed.",
                "created_at": now,
            },
        ]
        saved = client.table("notification").insert(notifications).execute().data
        if not saved:
            raise CoordinatorLeadAssignmentError(
                "The event was reassigned, but notifications could not be created.", 502
            )

        profile_rows = (
            client.table("profile")
            .select("name")
            .eq("user_id", coordinator_id)
            .limit(1)
            .execute()
            .data
            or []
        )
    except CoordinatorLeadAssignmentError:
        raise
    except Exception as exc:
        raise CoordinatorLeadAssignmentError("Unable to reassign the event.", 502) from exc

    reassigned = update[0]
    reassigned["coordinator_name"] = (
        profile_rows[0].get("name") if profile_rows else None
    )
    reassigned["previous_coordinator_id"] = previous_coordinator_id
    reassigned["assigned_by"] = lead_id
    return reassigned


def _coordinators(client):
    role_rows = (
        client.table("user_role")
        .select("user_id")
        .eq("role", COORDINATOR_ROLE)
        .execute()
        .data
        or []
    )
    coordinator_ids = {row.get("user_id") for row in role_rows if row.get("user_id")}
    profiles = client.table("profile").select("user_id,name").execute().data or []
    coordinators = [
        {"user_id": row.get("user_id"), "name": row.get("name") or "Unnamed coordinator"}
        for row in profiles
        if row.get("user_id") in coordinator_ids
    ]
    coordinators.sort(key=lambda row: row["name"].casefold())
    return coordinators


def _lead_session(access_token):
    try:
        client = create_authenticated_supabase_client(access_token)
        user = client.auth.get_user(access_token).user
        if not user:
            raise ValueError("No authenticated user")
        roles = (
            client.table("user_role")
            .select("role")
            .eq("user_id", user.id)
            .eq("role", LEAD_ROLE)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise CoordinatorLeadAssignmentError("Authentication is required.", 401) from exc
    if not roles:
        raise CoordinatorLeadAssignmentError(
            "Event Coordinator Lead access is required.", 403
        )
    return client, user.id
