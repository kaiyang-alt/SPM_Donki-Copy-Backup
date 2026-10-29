from flask import Blueprint, jsonify, request

from app.services.notification_service import (
    NotificationAccessError,
    list_user_notifications,
)


notifications_blueprint = Blueprint("notifications", __name__, url_prefix="/api/notifications")


def _bearer_token() -> str | None:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


@notifications_blueprint.get("")
def get_notifications():
    access_token = _bearer_token()
    if not access_token:
        return jsonify({"error": "Authentication is required."}), 401

    try:
        notifications = list_user_notifications(access_token)
    except NotificationAccessError:
        return jsonify({"error": "Unable to load notifications."}), 502

    return jsonify({"notifications": notifications}), 200
