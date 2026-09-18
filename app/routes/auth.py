from flask import Blueprint, jsonify, request

from app.services.auth_service import (
    AuthenticationError,
    AuthorisationError,
    login_event_organiser,
    logout_event_organiser,
)


auth_blueprint = Blueprint("auth", __name__, url_prefix="/auth")


@auth_blueprint.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    try:
        session = login_event_organiser(email, password)
    except AuthenticationError as exc:
        return jsonify({"error": str(exc)}), 401
    except AuthorisationError as exc:
        return jsonify({"error": str(exc)}), 403

    return jsonify({"message": "Login successful.", **session}), 200


@auth_blueprint.post("/logout")
def logout():
    data = request.get_json(silent=True) or {}
    access_token = data.get("access_token", "")
    refresh_token = data.get("refresh_token", "")

    if not access_token or not refresh_token:
        return jsonify({"error": "An authenticated session is required."}), 401

    try:
        logout_event_organiser(access_token, refresh_token)
    except AuthenticationError as exc:
        return jsonify({"error": str(exc)}), 401

    return jsonify({"message": "Logout successful."}), 200
