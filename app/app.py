from flask import Flask, jsonify, request

from app.supabase_client import create_supabase_client


app = Flask(__name__)


@app.route("/")
def home():
    return "ConnectSphere is running!"


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    try:
        supabase = create_supabase_client()

        response = supabase.auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            }
        )

        return jsonify(
            {
                "message": "Login successful.",
                "user_id": response.user.id,
                "email": response.user.email,
                "access_token": response.session.access_token,
            }
        ), 200

    except Exception:
        return jsonify({"error": "Invalid email or password."}), 401


if __name__ == "__main__":
    app.run(debug=True)