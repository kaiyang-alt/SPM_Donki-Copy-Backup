from app.app import app


def test_home_page():
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"ConnectSphere" in response.data
    assert b"Plan events." in response.data
