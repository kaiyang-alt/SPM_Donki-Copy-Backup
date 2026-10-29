from app.supabase_client import create_authenticated_supabase_client


class NotificationAccessError(Exception):
    """Raised when notifications cannot be loaded for the authenticated user."""


def list_user_notifications(access_token: str) -> list[dict]:
    try:
        client = create_authenticated_supabase_client(access_token)
        user = client.auth.get_user(access_token).user
        if not user:
            raise ValueError("No authenticated user")

        response = (
            client.table("notification")
            .select("notification_id,event_id,type,message,created_at,read_at")
            .eq("recipient_id", user.id)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []
    except Exception as exc:
        raise NotificationAccessError(
            "Unable to load notifications for this account."
        ) from exc
