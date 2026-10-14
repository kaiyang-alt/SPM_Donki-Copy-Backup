import importlib
from flask import Flask, jsonify, render_template

app = Flask(__name__)


def get_blueprint(module_path):
    """Dynamically fetch the Blueprint instance from a route module."""
    module = importlib.import_module(module_path)
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if hasattr(attr, "__class__") and attr.__class__.__name__ == "Blueprint":
            return attr
    raise ImportError(f"No Blueprint instance found in {module_path}")


# Register blueprints dynamically from route files
auth_bp = get_blueprint("app.routes.auth")
event_change_requests_bp = get_blueprint("app.routes.event_change_requests")
events_bp = get_blueprint("app.routes.events")
venue_staff_bp = get_blueprint("app.routes.venue_staff_routes")
venue_availability_bp = get_blueprint("app.routes.venue_availability_routes")

app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(
    event_change_requests_bp, url_prefix="/api/event-change-requests"
)
app.register_blueprint(events_bp, url_prefix="/api/events")
app.register_blueprint(venue_staff_bp, url_prefix="/api/venue")
app.register_blueprint(venue_availability_bp, url_prefix="/api/venue")


@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)