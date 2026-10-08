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
    assert b"js/event-review.js" in response.data
