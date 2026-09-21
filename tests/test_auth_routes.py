from unittest.mock import patch

import pytest

from app1.app import app
from app1.services.auth_service import AuthenticationError, AuthorisationError


@pytest.fixture
def client():
    return app.test_client()


def test_login_requires_email_and_password(client):
    response = client.post("/auth/login", json={"email": "organiser@example.test"})

    assert response.status_code == 400
    assert response.get_json() == {"error": "Email and password are required."}


@patch("app.routes.auth.login_event_organiser")
def test_event_organiser_can_log_in_with_valid_credentials(mock_login, client):
    mock_login.return_value = {
        "user_id": "user-1",
        "email": "organiser@example.test",
        "access_token": "access-token",
        "refresh_token": "refresh-token",
    }

    response = client.post(
        "/auth/login",
        json={"email": " organiser@example.test ", "password": "valid-password"},
    )

    assert response.status_code == 200
    assert response.get_json()["access_token"] == "access-token"
    mock_login.assert_called_once_with("organiser@example.test", "valid-password")


@patch("app.routes.auth.login_event_organiser")
def test_invalid_credentials_are_rejected(mock_login, client):
    mock_login.side_effect = AuthenticationError("Invalid email or password.")

    response = client.post(
        "/auth/login",
        json={"email": "organiser@example.test", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid email or password."}


@patch("app.routes.auth.login_event_organiser")
def test_account_without_event_organiser_access_is_rejected(mock_login, client):
    mock_login.side_effect = AuthorisationError(
        "This account does not have Event Organiser access."
    )

    response = client.post(
        "/auth/login",
        json={"email": "attendee@example.test", "password": "valid-password"},
    )

    assert response.status_code == 403
    assert response.get_json() == {
        "error": "This account does not have Event Organiser access."
    }


@patch("app.routes.auth.logout_event_organiser")
def test_authenticated_event_organiser_can_log_out(mock_logout, client):
    response = client.post(
        "/auth/logout",
        json={"access_token": "access-token", "refresh_token": "refresh-token"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"message": "Logout successful."}
    mock_logout.assert_called_once_with("access-token", "refresh-token")
