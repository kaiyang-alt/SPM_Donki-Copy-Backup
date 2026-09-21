from app.supabase_client import create_supabase_client


class AuthenticationError(Exception):
    """Raised when supplied credentials or session details are invalid."""


class AuthorisationError(Exception):
    """Raised when an authenticated account lacks Event Organiser access."""

def login_event_organiser(email: str, password: str) -> dict:
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
            .eq("role", "event_organiser")
            .limit(1)
            .execute()
        )
    except Exception as exc:
        client.auth.sign_out()
        raise AuthorisationError("Unable to verify Event Organiser access.") from exc

    if not profile_response.data or not role_response.data:
        client.auth.sign_out()
        raise AuthorisationError(
            "This account does not have Event Organiser access."
        )

    return {
        "user_id": response.user.id,
        "email": response.user.email,
        "access_token": response.session.access_token,
        "refresh_token": response.session.refresh_token,
    }


def logout_event_organiser(access_token: str, refresh_token: str) -> None:
    try:
        client = create_supabase_client()
        client.auth.set_session(access_token, refresh_token)
        client.auth.sign_out()
    except Exception as exc:
        raise AuthenticationError("The authenticated session is invalid.") from exc
