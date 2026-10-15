from flask import Flask, render_template

from app.routes.auth import auth_blueprint
from app.routes.event_change_requests import event_change_requests_blueprint
from app.routes.events import events_bp as events_blueprint
from app.routes.equipment_reservations import equipment_reservations_bp
from app.routes.venue_booking import venue_booking_bp
from app.routes.venue_availability_routes import venue_availability_bp
from app.routes.venue_staff_routes import venue_staff_bp
from app.routes.submit_event_request_routes import event_request_bp
from app.routes.venue_search import venue_search_blueprint
from app.routes.event_reviews import event_reviews_blueprint
from app.routes.event_assignment_routes import event_assignment_bp
from app.routes.track_readiness_actions_routes import track_readiness_actions_bp


app = Flask(__name__)
app.register_blueprint(auth_blueprint)
app.register_blueprint(events_blueprint)
app.register_blueprint(event_change_requests_blueprint)
app.register_blueprint(equipment_reservations_bp)
app.register_blueprint(venue_booking_bp)
app.register_blueprint(venue_availability_bp, url_prefix="/api/venue")
app.register_blueprint(venue_staff_bp, url_prefix="/api/venue")
app.register_blueprint(event_request_bp)
app.register_blueprint(venue_search_blueprint)
app.register_blueprint(event_reviews_blueprint)
app.register_blueprint(event_assignment_bp)
app.register_blueprint(track_readiness_actions_bp)


@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
