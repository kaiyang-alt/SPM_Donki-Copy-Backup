from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.app import app
from app.services.notification_service import list_user_notifications


@patch("app.services.notification_service.create_authenticated_supabase_client")
def test_notifications_are_limited_to_the_authenticated_recipient(create_client):
    client = MagicMock()
    create_client.return_value = client
    client.auth.get_user.return_value = SimpleNamespace(
        user=SimpleNamespace(id="recipient-1")
    )
    query = client.table.return_value.select.return_value
    query.eq.return_value.order.return_value.execute.return_value.data = [
        {
            "notification_id": "notice-1",
            "type": "coordinator_reassigned",
            "message": "You have been assigned.",
        }
    ]

    result = list_user_notifications("token")

    assert result[0]["notification_id"] == "notice-1"
    client.table.assert_called_once_with("notification")
    query.eq.assert_called_once_with("recipient_id", "recipient-1")
    query.eq.return_value.order.assert_called_once_with("created_at", desc=True)


def test_notification_route_requires_authentication():
    response = app.test_client().get("/api/notifications")

    assert response.status_code == 401


@patch("app.routes.notifications.list_user_notifications")
def test_notification_route_returns_authenticated_notifications(list_notifications):
    list_notifications.return_value = [
        {
            "notification_id": "notice-1",
            "type": "coordinator_reassigned",
            "message": "You are no longer assigned.",
        }
    ]

    response = app.test_client().get(
        "/api/notifications", headers={"Authorization": "Bearer token"}
    )

    assert response.status_code == 200
    assert response.get_json()["notifications"][0]["notification_id"] == "notice-1"
    list_notifications.assert_called_once_with("token")
