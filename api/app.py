# api/app.py
import os
import sys
from flask import Flask
from flask_cors import CORS

# --- Path Setup ---
# This ensures that the `agent` module can be found by the Python interpreter.
# It adds the project's root directory to the system path.

# The current file is in `d:\...\api\app.py`
# The parent directory is `d:\...\api`
# The project root is the parent of the parent: `d:\...\`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Now we can import from other top-level directories like `agent`
from api.routes import api_bp

# --- Flask App Initialization ---

def create_app():
    """Creates and configures the Flask application."""
    app = Flask(__name__)
    
    # Enable CORS for all routes, allowing frontend access
    CORS(app)
    
    # Register the blueprint that contains our API routes
    app.register_blueprint(api_bp)
    
    return app

app = create_app()

# --- Main Entry Point ---
if __name__ == '__main__':
    # This block runs when you execute `python api/app.py`
    print("--- Starting Recommendation Agent API Service ---")
    print(f"Project Root added to path: {PROJECT_ROOT}")
    print("Flask server starting on http://127.0.0.1:5001")
    print("Available endpoints:")
    print("  - GET /health")
    print("  - POST /api/agent/recommend")
    
    # Run the app on a different port to avoid conflict with the main app
    app.run(host='0.0.0.0', port=5001, debug=False)
