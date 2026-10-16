from app.app import app


def test_home_page():
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"ConnectSphere" in response.data
    assert b"Plan events." in response.data
    assert b"ConnectSphere login" in response.data
    assert b'id="loginForm"' in response.data
    assert b'id="loginRole"' not in response.data
    assert b'id="roleSelect"' in response.data
    assert b'Event Coordinator' in response.data
    assert b'Venue Staff' in response.data
    assert b'Technical Staff (Demo)' in response.data
    assert b'Attendee (Demo)' in response.data
    assert b"js/venue-search.js" in response.data
    assert b"js/event-review.js" in response.data


def _production_method_path_registrations():
    registrations = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            registrations.append((method, rule.rule))
    return registrations


def test_production_blueprints_are_registered():
    expected_blueprints = {
        "auth",
        "events",
        "event_change_requests",
        "venue_booking",
        "event_requests",
        "venue_search",
        "event_reviews",
        "event_assignment",
        "track_readiness_actions",
        "venue_availability_api",
        "venue_staff_api",
    }

    assert expected_blueprints <= set(app.blueprints)


def test_critical_production_route_contracts_exist():
    expected_routes = {
        ("POST", "/auth/login"),
        ("GET", "/api/events"),
        ("PATCH", "/api/events/<event_id>"),
        ("POST", "/api/event-change-requests"),
        ("POST", "/api/venue-bookings"),
        ("GET", "/api/venue-bookings"),
        ("POST", "/api/event-requests/submit"),
        ("POST", "/api/venues/search"),
        ("GET", "/api/event-reviews"),
        ("GET", "/api/event-assignment/assigned-events"),
        ("GET", "/api/track-readiness-actions/events"),
        ("GET", "/api/venue/availability"),
        ("GET", "/api/venue/availability/blocks"),
        ("POST", "/api/venue/availability/blocks"),
        ("GET", "/api/venue/requests"),
        ("PATCH", "/api/venue/requests/<request_id>/status"),
    }

    assert expected_routes <= set(_production_method_path_registrations())


def test_production_routes_have_no_duplicate_method_path_registrations():
    registrations = _production_method_path_registrations()
    duplicates = {
        registration
        for registration in registrations
        if registrations.count(registration) > 1
    }

    assert duplicates == set()
