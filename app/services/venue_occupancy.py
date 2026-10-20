"""B1-OCC-v1: one UTC, whole-minute, half-open occupancy interpretation.

Read assessments preserve source rows. They never decide hold validity or mutate
arrangements. Writers must still adopt the database venue/event lock protocol.
"""

from datetime import UTC, datetime, timedelta


class VenueOccupancyError(Exception):
    def __init__(self, code, message, status_code=409):
        super().__init__(message)
        self.code, self.status_code = code, status_code


def validate_minutes(value):
    if value is None:
        raise VenueOccupancyError("B1_CONFIGURATION_REQUIRED", "Venue durations are unconfigured.")
    if type(value) is not int or not 0 <= value <= 2147483647:
        raise VenueOccupancyError("B1_INVALID_DURATION", "Durations must be nonnegative whole integer minutes.", 400)
    if value == 0:
        raise VenueOccupancyError("B1_ZERO_DECISION_REQUIRED", "Zero duration requires a separate business decision.")
    return value


def instant(value):
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("Timezone required")
        return parsed.astimezone(UTC)
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        raise VenueOccupancyError("B1_INVALID_SCHEDULE", "A valid timezone-aware scheduled period is required.") from exc


def bounded_period(start, end):
    start, end = instant(start), instant(end)
    if start >= end:
        raise VenueOccupancyError("B1_INVALID_SCHEDULE", "Scheduled end must be after start.")
    return start, end


def occupied_period(start, end, setup_minutes, turnaround_minutes):
    setup, turnaround = validate_minutes(setup_minutes), validate_minutes(turnaround_minutes)
    start, end = bounded_period(start, end)
    try:
        return start - timedelta(minutes=setup), end + timedelta(minutes=turnaround)
    except OverflowError as exc:
        raise VenueOccupancyError("B1_DATETIME_OUTSIDE_COMMON_SUPPORTED_RANGE", "Occupied period exceeds the supported datetime range.") from exc


def overlaps(left, right):
    """Compare aware instants, with exact endpoint touching non-conflicting."""
    a, b = bounded_period(*left), bounded_period(*right)
    return a[0] < b[1] and b[0] < a[1]


def configuration(venue):
    setup, turnaround = venue.get("setup_minutes"), venue.get("turnaround_minutes")
    state = "CONFIGURED"
    try:
        validate_minutes(setup)
        validate_minutes(turnaround)
    except VenueOccupancyError as exc:
        state = {"B1_CONFIGURATION_REQUIRED": "UNCONFIGURED", "B1_ZERO_DECISION_REQUIRED": "DECISION_REQUIRED"}.get(exc.code, "UNASSESSABLE")
    if (setup is None) != (turnaround is None):
        state = "UNASSESSABLE"
    return {
        "setup_minutes": setup, "turnaround_minutes": turnaround,
        "buffer_config_revision": venue.get("buffer_config_revision"),
        "configuration_state": state,
    }


def _conflict(left, right, potential=False):
    a, b = (left["occupied_start"], left["occupied_end"]), (right["occupied_start"], right["occupied_end"])
    if not overlaps(a, b):
        return None
    return {
        "booking_id": left.get("booking_id"), "event_id": left.get("event_id"),
        "other_booking_id": right.get("booking_id"), "other_event_id": right.get("event_id"),
        "venue_block_id": right.get("venue_block_id"),
        "overlap_start": max(instant(a[0]), instant(b[0])).isoformat(),
        "overlap_end": min(instant(a[1]), instant(b[1])).isoformat(),
        "assessment": "potential_hold_validity_unavailable" if potential else "identified",
    }


def assess_schedule(venue, bookings, blocks, source_complete=True):
    """Expose current occupancy and blockers without discarding retained rows."""
    config = configuration(venue)
    limitations, blockers, occupied, occupied_blocks = [], [], [], []
    if not source_complete:
        limitations.append({"reason": "authoritative_booking_visibility_unavailable"})
    if config["configuration_state"] != "CONFIGURED":
        limitations.append({"reason": "configuration_required" if config["configuration_state"] == "UNCONFIGURED" else "configuration_decision_or_repair_required"})
    output_bookings, output_blocks = [], []
    for source in bookings:
        row = {**source, "occupied_start": None, "occupied_end": None, "occupancy_assessment": "inactive"}
        output_bookings.append(row)
        status = row.get("status")
        if status in ("rejected", "cancelled"):
            continue
        if status not in ("confirmed", "requested", "tentative"):
            row["occupancy_assessment"] = "unassessable"
            blockers.append({"booking_id": row.get("booking_id"), "reason": "booking_lifecycle_classification_required"})
            continue
        potential = status in ("requested", "tentative")
        row["occupancy_assessment"] = "potential_hold_validity_unavailable" if potential else "identified"
        if potential:
            limitations.append({"booking_id": row.get("booking_id"), "reason": "hold_validity_unavailable"})
        try:
            bounded_period(row.get("requested_start"), row.get("requested_end"))
            if config["configuration_state"] != "CONFIGURED":
                continue
            start, end = occupied_period(row.get("requested_start"), row.get("requested_end"), config["setup_minutes"], config["turnaround_minutes"])
            row.update(occupied_start=start.isoformat(), occupied_end=end.isoformat())
            occupied.append(row)
        except VenueOccupancyError as exc:
            row["occupancy_assessment"] = "unassessable"
            target = limitations if potential and exc.code == "B1_INVALID_SCHEDULE" else blockers
            target.append({"booking_id": row.get("booking_id"), "reason": "hold_schedule_unassessable_pending_owner" if target is limitations else "confirmed_or_expanded_schedule_unassessable"})
    for source in blocks:
        row = {**source, "occupied_start": None, "occupied_end": None}
        output_blocks.append(row)
        if row.get("status") == "cancelled":
            continue
        if row.get("status") != "active":
            blockers.append({"venue_block_id": row.get("venue_block_id"), "reason": "block_lifecycle_classification_required"})
            continue
        try:
            start, end = bounded_period(row.get("start_datetime"), row.get("end_datetime"))
            row.update(occupied_start=start.isoformat(), occupied_end=end.isoformat())
            occupied_blocks.append(row)
        except VenueOccupancyError:
            blockers.append({"venue_block_id": row.get("venue_block_id"), "reason": "active_block_interval_unresolved_under_bounded_scope"})
    conflicts = []
    for index, left in enumerate(occupied):
        for right in occupied[index + 1:] + occupied_blocks:
            conflict = _conflict(left, right, left.get("status") in ("requested", "tentative") or right.get("status") in ("requested", "tentative"))
            if conflict:
                conflicts.append(conflict)
    return {
        "contract_version": "B1-OCC-v1", "configuration": config,
        "bookings_and_holds": output_bookings, "maintenance_blocks": output_blocks,
        "conflicts": conflicts, "assessment_limitations": limitations,
        "assessment_blockers": blockers,
        "authoritative_assessment_complete": source_complete and not blockers and config["configuration_state"] == "CONFIGURED",
        "assessment_complete": not blockers and not limitations,
    }


def assess_candidate(venue, bookings, blocks, start, end, source_complete=True):
    period = occupied_period(start, end, venue.get("setup_minutes"), venue.get("turnaround_minutes"))
    assessment = assess_schedule(venue, bookings, blocks, source_complete)
    candidate = {"occupied_start": period[0].isoformat(), "occupied_end": period[1].isoformat()}
    conflicts = []
    for row in assessment["bookings_and_holds"] + assessment["maintenance_blocks"]:
        if row.get("occupied_start") is None:
            continue
        conflict = _conflict(candidate, row, row.get("status") in ("requested", "tentative"))
        if conflict:
            conflicts.append(conflict)
    return {
        **assessment, "candidate_conflicts": conflicts,
        "available": assessment["assessment_complete"] and not conflicts,
        "occupied_start": candidate["occupied_start"], "occupied_end": candidate["occupied_end"],
    }


def caller_has_complete_venue_reads(client, user_id):
    """Recognise the documented Staff and Coordinator occupancy SELECT policies.

    Role authority must still be combined with complete, exact-count reads;
    an empty RLS-filtered response alone never proves availability.
    """
    roles = client.table("user_role").select("role").eq("user_id", user_id).execute().data or []
    return any(row.get("role") in ("venue_staff", "event_coordinator") for row in roles)


def load_occupancy_rows(client, table, venue_id=None):
    """An API row cap must not turn a partial read into a free-slot claim."""
    query = client.table(table).select("*", count="exact")
    if venue_id is not None:
        query = query.eq("venue_id", venue_id)
    response = query.execute()
    rows = response.data or []
    count = getattr(response, "count", None)
    return rows, type(count) is int and count == len(rows)
