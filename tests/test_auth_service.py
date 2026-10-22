from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from postgrest.exceptions import APIError

from app.services.auth_service import (
    AuthorisationError, login_event_organiser, login_for_role, login_user,
)


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


@pytest.mark.parametrize("role_login", [False, True])
@pytest.mark.parametrize("table,code,reason", [
    ("profile", "42501", "database permission denied"),
    ("user_role", "42P17", "recursive access policy"),
    ("profile", "PGRST205", "table missing from the API schema"),
    ("user_role", "XX000", "database request failed"),
])
@patch("app.services.auth_service.create_supabase_client")
def test_failed_access_lookup_reports_safe_stage_and_reason(
    mock_create_client, role_login, table, code, reason, caplog,
):
    client = MagicMock()
    client.auth.sign_in_with_password.return_value = _signed_in_response()
    queries = {}
    for name in ("profile", "user_role"):
        query = MagicMock()
        for method in ("select", "eq", "limit"):
            getattr(query, method).return_value = query
        query.execute.return_value = SimpleNamespace(data=[{"role": "technical_support"}])
        queries[name] = query
    queries[table].execute.side_effect = APIError({
        "code": code, "message": "private SQL and sensitive-token must not be exposed",
    })
    client.table.side_effect = lambda name: queries[name]
    mock_create_client.return_value = client

    with pytest.raises(AuthorisationError) as exc:
        if role_login:
            login_for_role("tss@example.test", "test-password", "technical_support")
        else:
            login_user("tss@example.test", "test-password")

    assert f"{table} lookup failed ({reason})" in str(exc.value)
    assert "sensitive-token" not in str(exc.value) + caplog.text
    client.auth.sign_out.assert_called_once()
