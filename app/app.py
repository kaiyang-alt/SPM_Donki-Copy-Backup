from flask import Flask, render_template

from app.routes.auth import auth_blueprint
from app.routes.event_change_requests import event_change_requests_blueprint
from app.routes.events import events_blueprint
from app.routes.venue_booking import venue_booking_bp
from app.routes.submit_event_request_routes import event_request_bp
from app.routes.venue_search import venue_search_blueprint
from app.routes.event_reviews import event_reviews_blueprint
from app.routes.event_assignment_routes import event_assignment_bp
from app.routes.track_readiness_actions_routes import track_readiness_actions_bp
from app.routes.coordinator_lead_assignment import coordinator_lead_assignment_blueprint
from app.routes.notifications import notifications_blueprint


app = Flask(__name__)
app.register_blueprint(auth_blueprint)
app.register_blueprint(events_blueprint)
app.register_blueprint(event_change_requests_blueprint)
app.register_blueprint(venue_booking_bp)
app.register_blueprint(event_request_bp)
app.register_blueprint(venue_search_blueprint)
app.register_blueprint(event_reviews_blueprint)
app.register_blueprint(event_assignment_bp)
app.register_blueprint(track_readiness_actions_bp)
app.register_blueprint(coordinator_lead_assignment_blueprint)
app.register_blueprint(notifications_blueprint)


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
