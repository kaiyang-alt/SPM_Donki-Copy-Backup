from flask import Flask
from app1.routes.events import events_bp

app = Flask(__name__)

# Register the blueprint on 'app', not 'app1'
app.register_blueprint(events_bp)

if __name__ == "__main__":
    app.run(debug=True)