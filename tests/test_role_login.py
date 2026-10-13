from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.app import app
from app.services.auth_service import (
    AuthenticationError,
    AuthorisationError,
    login_for_role,
    login_user,
)


@pytest.fixture
def client():
    return app.test_client()


def test_application_login_requires_credentials(client):
    response = client.post("/auth/application-login", json={"email": "user@example.test"})
    assert response.status_code == 400


@patch("app.routes.auth.login_user")
def test_application_login_returns_database_roles(mock_login, client):
    mock_login.return_value = {
        "user_id": "user-1",
        "email": "user@example.test",
        "roles": ["event_coordinator", "venue_staff"],
        "access_token": "access-token",
        "refresh_token": "refresh-token",
    }
    response = client.post(
        "/auth/application-login",
        json={"email": "user@example.test", "password": "password"},
    )
    assert response.status_code == 200
    assert response.get_json()["roles"] == ["event_coordinator", "venue_staff"]


@patch("app.services.auth_service.create_supabase_client")
def test_login_user_loads_supported_database_roles(mock_create_client):
    client = MagicMock()
    client.auth.sign_in_with_password.return_value = SimpleNamespace(
        user=SimpleNamespace(id="user-1", email="user@example.test"),
        session=SimpleNamespace(access_token="access", refresh_token="refresh"),
    )
    profile_query = MagicMock()
    role_query = MagicMock()
    profile_query.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
        SimpleNamespace(data=[{"user_id": "user-1"}])
    )
    role_query.select.return_value.eq.return_value.execute.return_value = SimpleNamespace(
        data=[
            {"role": "venue_staff"},
            {"role": "event_coordinator"},
            {"role": "unsupported_role"},
        ]
    )
    client.table.side_effect = lambda table: {
        "profile": profile_query,
        "user_role": role_query,
    }[table]
    mock_create_client.return_value = client

    session = login_user("user@example.test", "password")

    assert session["roles"] == ["event_coordinator", "venue_staff"]


def test_role_login_requires_role_and_credentials(client):
    response = client.post(
        "/auth/role-login",
        json={"email": "coordinator@example.test", "password": "password"},
    )
    assert response.status_code == 400


@patch("app.routes.auth.login_for_role")
def test_coordinator_can_log_in_with_verified_role(mock_login, client):
    mock_login.return_value = {
        "user_id": "coordinator-1",
        "email": "coordinator@example.test",
        "role": "event_coordinator",
        "access_token": "access-token",
        "refresh_token": "refresh-token",
    }
    response = client.post(
        "/auth/role-login",
        json={
            "email": "coordinator@example.test",
            "password": "password",
            "role": "event_coordinator",
        },
    )
    assert response.status_code == 200
    assert response.get_json()["role"] == "event_coordinator"


@patch("app.routes.auth.login_for_role")
def test_role_login_rejects_invalid_credentials(mock_login, client):
    mock_login.side_effect = AuthenticationError("Invalid email or password.")
    response = client.post(
        "/auth/role-login",
        json={"email": "x@example.test", "password": "wrong", "role": "venue_staff"},
    )
    assert response.status_code == 401


@patch("app.routes.auth.login_for_role")
def test_role_login_rejects_unassigned_role(mock_login, client):
    mock_login.side_effect = AuthorisationError(
        "This account does not have access to the selected role."
    )
    response = client.post(
        "/auth/role-login",
        json={"email": "x@example.test", "password": "password", "role": "venue_staff"},
    )
    assert response.status_code == 403


@patch("app.services.auth_service.create_supabase_client")
def test_login_for_role_verifies_requested_database_role(mock_create_client):
    client = MagicMock()
    client.auth.sign_in_with_password.return_value = SimpleNamespace(
        user=SimpleNamespace(id="staff-1", email="staff@example.test"),
        session=SimpleNamespace(access_token="access", refresh_token="refresh"),
    )
    profile_query = MagicMock()
    role_query = MagicMock()
    profile_query.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
        SimpleNamespace(data=[{"user_id": "staff-1"}])
    )
    role_query.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = (
        SimpleNamespace(data=[{"role": "venue_staff"}])
    )
    client.table.side_effect = lambda table: {
        "profile": profile_query,
        "user_role": role_query,
    }[table]
    mock_create_client.return_value = client

    session = login_for_role("staff@example.test", "password", "venue_staff")

    assert session["role"] == "venue_staff"
    role_query.select.return_value.eq.return_value.eq.assert_called_once_with(
        "role", "venue_staff"
    )


@patch("app.services.auth_service.create_supabase_client")
def test_login_for_role_rejects_unsupported_role_without_authentication(mock_create_client):
    with pytest.raises(AuthorisationError):
        login_for_role("user@example.test", "password", "administrator")
    mock_create_client.assert_not_called()


@patch("app.services.auth_service.create_supabase_client")
def test_login_for_role_supports_distinct_coordinator_lead_role(mock_create_client):
    client = MagicMock()
    client.auth.sign_in_with_password.return_value = SimpleNamespace(
        user=SimpleNamespace(id="lead-1", email="lead@example.test"),
        session=SimpleNamespace(access_token="access", refresh_token="refresh"),
    )
    profile_query = MagicMock()
    role_query = MagicMock()
    profile_query.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
        SimpleNamespace(data=[{"user_id": "lead-1"}])
    )
    role_query.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = (
        SimpleNamespace(data=[{"role": "event_coordinator_lead"}])
    )
    client.table.side_effect = lambda table: {
        "profile": profile_query,
        "user_role": role_query,
    }[table]
    mock_create_client.return_value = client

    session = login_for_role(
        "lead@example.test", "password", "event_coordinator_lead"
    )

    assert session["role"] == "event_coordinator_lead"
