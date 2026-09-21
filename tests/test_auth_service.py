from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app1.services.auth_service import AuthorisationError, login_event_organiser


def _signed_in_response():
    return SimpleNamespace(
        user=SimpleNamespace(id="user-1", email="organiser@example.test"),
        session=SimpleNamespace(
            access_token="access-token", refresh_token="refresh-token"
        ),
    )


@patch("app.services.auth_service.create_supabase_client")
def test_login_verifies_profile_and_event_organiser_role(mock_create_client):
    client = MagicMock()
    client.auth.sign_in_with_password.return_value = _signed_in_response()
    profile_query = MagicMock()
    role_query = MagicMock()
    profile_query.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
        SimpleNamespace(data=[{"user_id": "user-1"}])
    )
    role_query.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = (
        SimpleNamespace(data=[{"role": "event_organiser"}])
    )
    client.table.side_effect = lambda table: {
        "profile": profile_query,
        "user_role": role_query,
    }[table]
    mock_create_client.return_value = client

    session = login_event_organiser("organiser@example.test", "valid-password")

    assert session["user_id"] == "user-1"
    assert session["access_token"] == "access-token"
    client.table.assert_any_call("profile")
    client.table.assert_any_call("user_role")
    role_query.select.return_value.eq.return_value.eq.assert_called_once_with(
        "role", "event_organiser"
    )


@patch("app.services.auth_service.create_supabase_client")
def test_login_rejects_account_without_event_organiser_role(mock_create_client):
    client = MagicMock()
    client.auth.sign_in_with_password.return_value = _signed_in_response()
    profile_query = MagicMock()
    role_query = MagicMock()
    profile_query.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
        SimpleNamespace(data=[{"user_id": "user-1"}])
    )
    role_query.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = (
        SimpleNamespace(data=[])
    )
    client.table.side_effect = lambda table: {
        "profile": profile_query,
        "user_role": role_query,
    }[table]
    mock_create_client.return_value = client

    with pytest.raises(AuthorisationError):
        login_event_organiser("attendee@example.test", "valid-password")

    client.auth.sign_out.assert_called_once()
