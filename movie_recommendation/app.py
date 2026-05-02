import os
import sys
from flask import Flask
from flask_cors import CORS

# This block ensures that top-level packages (agent, api, etc.) can be found.
PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__)) # .../movie_recommendation
PROJECT_ROOT = os.path.dirname(PACKAGE_ROOT) # .../
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Force UTF-8 console output on Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Import the API blueprint from the new API module
from api.routes import api_bp

# Load environment variables for configuration
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Create and configure the Flask app
app = Flask(__name__)

# Use a secret key from environment variables or a default
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# Configure CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Register the API blueprint
app.register_blueprint(api_bp)

@app.route("/")
def index():
    return "Movie AI Assistant Backend is running. Access the API at /api/", 200

if __name__ == '__main__':
    # Get host and port from environment variables or use defaults
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() == "true"

    print(f"[INFO] Starting server at http://{host}:{port}/")
    app.run(host=host, port=port, debug=debug)
