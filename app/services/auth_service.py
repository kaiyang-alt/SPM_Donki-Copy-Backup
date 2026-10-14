from app.supabase_client import create_supabase_client


class AuthenticationError(Exception):
    """Raised when supplied credentials or session details are invalid."""


class AuthorisationError(Exception):
    """Raised when an authenticated account lacks Event Organiser access."""

SUPPORTED_LOGIN_ROLES = {
    "event_organiser",
    "event_coordinator",
    "venue_staff",
}


def login_user(email: str, password: str) -> dict:
    """Authenticate a user and return their supported application roles."""
    client = create_supabase_client()
    try:
        response = client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception as exc:
        raise AuthenticationError("Invalid email or password.") from exc

    if not response.user or not response.session:
        raise AuthenticationError("Invalid email or password.")

    try:
        client.postgrest.auth(response.session.access_token)
        profile_response = (
            client.table("profile")
            .select("user_id")
            .eq("user_id", response.user.id)
            .limit(1)
            .execute()
        )
        role_response = (
            client.table("user_role")
            .select("role")
            .eq("user_id", response.user.id)
            .execute()
        )
    except Exception as exc:
        client.auth.sign_out()
        raise AuthorisationError("Unable to verify application access.") from exc

    assigned_roles = {
        row.get("role") for row in (role_response.data or []) if isinstance(row, dict)
    }
    roles = sorted(assigned_roles & SUPPORTED_LOGIN_ROLES)
    if not profile_response.data or not roles:
        client.auth.sign_out()
        raise AuthorisationError(
            "This account does not have supported application access."
        )

    return {
        "user_id": response.user.id,
        "email": response.user.email,
        "roles": roles,
        "access_token": response.session.access_token,
        "refresh_token": response.session.refresh_token,
    }


def login_for_role(email: str, password: str, role: str) -> dict:
    """Authenticate a user and verify one supported application role."""
    if role not in SUPPORTED_LOGIN_ROLES:
        raise AuthorisationError("The requested application role is not supported.")

    client = create_supabase_client()
    try:
        response = client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception as exc:
        raise AuthenticationError("Invalid email or password.") from exc

    if not response.user or not response.session:
        raise AuthenticationError("Invalid email or password.")

    try:
        client.postgrest.auth(response.session.access_token)
        profile_response = (
            client.table("profile")
            .select("user_id")
            .eq("user_id", response.user.id)
            .limit(1)
            .execute()
        )
        role_response = (
            client.table("user_role")
            .select("role")
            .eq("user_id", response.user.id)
            .eq("role", role)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        client.auth.sign_out()
        raise AuthorisationError("Unable to verify application access.") from exc

    if not profile_response.data or not role_response.data:
        client.auth.sign_out()
        raise AuthorisationError("This account does not have access to the selected role.")

    return {
        "user_id": response.user.id,
        "email": response.user.email,
        "role": role,
        "access_token": response.session.access_token,
        "refresh_token": response.session.refresh_token,
    }


def login_event_organiser(email: str, password: str) -> dict:
    try:
        result = login_for_role(email, password, "event_organiser")
    except AuthorisationError as exc:
        if str(exc) == "This account does not have access to the selected role.":
            raise AuthorisationError(
                "This account does not have Event Organiser access."
            ) from exc
        raise
    result.pop("role", None)
    return result


def logout_event_organiser(access_token: str, refresh_token: str) -> None:
    try:
        client = create_supabase_client()
        client.auth.set_session(access_token, refresh_token)
        client.auth.sign_out()
    except Exception as exc:
        raise AuthenticationError("The authenticated session is invalid.") from exc
