from flask import Flask, render_template

from app.routes.auth import auth_blueprint
from app.routes.event_change_requests import event_change_requests_blueprint
from app.routes.events import events_blueprint
from app.routes.venue_booking import venue_booking_bp


app = Flask(__name__)
app.register_blueprint(auth_blueprint)
app.register_blueprint(events_blueprint)
app.register_blueprint(event_change_requests_blueprint)
app.register_blueprint(venue_booking_bp)


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
