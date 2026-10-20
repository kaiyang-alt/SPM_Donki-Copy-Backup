from copy import deepcopy
from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.services.venue_occupancy import (
    VenueOccupancyError, assess_candidate, assess_schedule, configuration,
    occupied_period, overlaps,
)


VENUE = {"venue_id": "A", "setup_minutes": 30, "turnaround_minutes": 45, "buffer_config_revision": 1}


def booking(identifier="first", start="10:00", end="12:00", status="confirmed"):
    return {"booking_id": identifier, "event_id": identifier, "venue_id": "A", "status": status,
            "requested_start": f"2027-03-10T{start}:00+08:00", "requested_end": f"2027-03-10T{end}:00+08:00"}


def test_occ_example_and_cross_date():
    start, end = occupied_period("2027-03-10T10:00:00+08:00", "2027-03-10T12:00:00+08:00", 30, 45)
    assert (start.isoformat(), end.isoformat()) == ("2027-03-10T01:30:00+00:00", "2027-03-10T04:45:00+00:00")
    start, end = occupied_period("2027-03-10T00:15:00+08:00", "2027-03-10T01:00:00+08:00", 30, 45)
    sg = timezone(timedelta(hours=8))
    assert start.astimezone(sg).isoformat() == "2027-03-09T23:45:00+08:00"
    assert end.astimezone(sg).isoformat() == "2027-03-10T01:45:00+08:00"


@pytest.mark.parametrize("start,end,overlap", [("09:00", "09:15", "2027-03-10T01:30:00+00:00"), ("13:00", "13:30", "2027-03-10T04:30:00+00:00")])
def test_setup_only_and_turnaround_only_conflicts(start, end, overlap):
    assessment = assess_candidate(VENUE, [booking()], [], booking(start=start, end=end)["requested_start"], booking(start=start, end=end)["requested_end"])
    assert assessment["available"] is False
    assert assessment["candidate_conflicts"][0]["overlap_start"] == overlap


def test_occ_touch_and_positive_overlap():
    a = ("2027-03-10T09:00:00+08:00", "2027-03-10T10:00:00+08:00")
    b = ("2027-03-10T02:00:00Z", "2027-03-10T03:00:00Z")
    assert not overlaps(a, b)
    assert overlaps((a[0], "2027-03-10T10:01:00+08:00"), b)


@pytest.mark.parametrize("value,code", [(None, "B1_CONFIGURATION_REQUIRED"), (0, "B1_ZERO_DECISION_REQUIRED"), (-1, "B1_INVALID_DURATION"), (True, "B1_INVALID_DURATION"), (1.5, "B1_INVALID_DURATION"), ("30", "B1_INVALID_DURATION"), (2147483648, "B1_INVALID_DURATION")])
def test_duration_domain(value, code):
    with pytest.raises(VenueOccupancyError) as error:
        occupied_period("2027-03-10T10:00:00Z", "2027-03-10T12:00:00Z", value, 45)
    assert error.value.code == code
    assert configuration({})["configuration_state"] == "UNCONFIGURED"
    assert configuration({"setup_minutes": 0, "turnaround_minutes": 45})["configuration_state"] == "DECISION_REQUIRED"


@pytest.mark.parametrize("start,end", [("2027-03-10T10:00:00", "2027-03-10T12:00:00"), ("2027-03-10T12:00:00Z", "2027-03-10T12:00:00Z"), ("2027-03-10T13:00:00Z", "2027-03-10T12:00:00Z")])
def test_invalid_schedules(start, end):
    with pytest.raises(VenueOccupancyError, match="timezone|after"):
        occupied_period(start, end, 30, 45)


def test_datetime_bounds_fail_explicitly():
    with pytest.raises(VenueOccupancyError) as error:
        occupied_period(datetime.min.replace(tzinfo=UTC), datetime(1, 1, 2, tzinfo=UTC), 30, 45)
    assert error.value.code == "B1_DATETIME_OUTSIDE_COMMON_SUPPORTED_RANGE"


def test_edit_impact_preserves_records_and_independent_venue():
    rows = [booking(), booking("second", "13:00", "14:00")]
    original = deepcopy(rows)
    previous = {**VENUE, "setup_minutes": 15, "turnaround_minutes": 15}
    assert not assess_schedule(previous, rows, [])["conflicts"]
    changed = assess_schedule(VENUE, rows, [])
    assert changed["conflicts"][0]["overlap_start"] == "2027-03-10T04:30:00+00:00"
    assert changed["conflicts"][0]["overlap_end"] == "2027-03-10T04:45:00+00:00"
    assert rows == original
    assert not assess_schedule(previous, rows, [])["conflicts"]


@pytest.mark.parametrize("status", ["requested", "tentative"])
def test_hold_validity_is_potential_not_active_or_expired(status):
    rows = [booking(), booking("hold", "13:00", "14:00", status)]
    before = deepcopy(rows)
    result = assess_schedule(VENUE, rows, [])
    assert result["authoritative_assessment_complete"] is True
    assert result["assessment_complete"] is False
    assert result["conflicts"][0]["assessment"] == "potential_hold_validity_unavailable"
    assert rows == before
    rows[1]["requested_start"] = None
    incomplete = assess_schedule(VENUE, rows, [])
    assert incomplete["assessment_complete"] is False
    assert any(item["reason"] == "hold_schedule_unassessable_pending_owner" for item in incomplete["assessment_limitations"])


@pytest.mark.parametrize("bad", [{"requested_start": None}, {"status": None}, {"status": "unknown"}])
def test_authoritative_data_cannot_be_omitted_as_free(bad):
    row = {**booking(), **bad}
    result = assess_candidate(VENUE, [row], [], "2027-03-10T20:00:00Z", "2027-03-10T21:00:00Z")
    assert result["assessment_blockers"]
    assert not result["available"]
    assert result["bookings_and_holds"][0]["requested_start"] == row["requested_start"]


def test_blocks_are_bounded_without_extra_buffers():
    block = {"venue_block_id": "block", "status": "active", "start_datetime": "2027-03-10T09:00:00+08:00", "end_datetime": "2027-03-10T09:45:00+08:00"}
    result = assess_schedule(VENUE, [booking()], [block])
    assert result["conflicts"][0]["overlap_start"] == "2027-03-10T01:30:00+00:00"
    assert result["maintenance_blocks"][0]["occupied_start"] == "2027-03-10T01:00:00+00:00"
    assert assess_schedule(VENUE, [], [{**block, "end_datetime": None}])["assessment_blockers"]
    assert assess_schedule(VENUE, [], [{**block, "status": None}])["assessment_blockers"]


def test_empty_rls_filtered_rows_are_not_proof_of_availability():
    result = assess_candidate(VENUE, [], [], "2027-03-10T10:00:00Z", "2027-03-10T12:00:00Z", source_complete=False)
    assert not result["available"]
    assert result["assessment_limitations"] == [{"reason": "authoritative_booking_visibility_unavailable"}]


@pytest.mark.parametrize("start,available", [("13:15", True), ("13:14", False)])
def test_fully_buffered_exact_touch(start, available):
    row = booking(start=start, end="14:00")
    assessment = assess_candidate(VENUE, [booking()], [], row["requested_start"], row["requested_end"])
    assert assessment["available"] is available


def test_elapsed_minutes_across_offset_change():
    start, end = occupied_period("2027-03-14T01:45:00-05:00", "2027-03-14T03:15:00-04:00", 30, 45)
    assert (start.isoformat(), end.isoformat()) == ("2027-03-14T06:15:00+00:00", "2027-03-14T08:00:00+00:00")


def test_occ_independent_duration_directions():
    start, end = occupied_period("2027-03-10T10:00:00+08:00", "2027-03-10T12:00:00+08:00", 45, 30)
    assert (start.isoformat(), end.isoformat()) == ("2027-03-10T01:15:00+00:00", "2027-03-10T04:30:00+00:00")


def test_turnaround_can_cross_into_next_date():
    _, end = occupied_period("2027-03-10T23:30:00+08:00", "2027-03-10T23:45:00+08:00", 30, 45)
    assert end.astimezone(timezone(timedelta(hours=8))).isoformat() == "2027-03-11T00:30:00+08:00"
