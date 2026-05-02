# api/routes.py
import datetime
from flask import Blueprint, request, jsonify

# Import the validator
from api.validator import validate_recommend_request

# Import the core logic from Phase 1
from agent.recommendation_agent import RecommendationAgent

# Create a Blueprint
api_bp = Blueprint('api', __name__)

# Instantiate the agent (it will be a singleton for the service)
agent = RecommendationAgent()

@api_bp.route("/health", methods=["GET"])
def health_check():
    """A simple health check endpoint."""
    return jsonify({"status": "ok", "timestamp": datetime.datetime.utcnow().isoformat()})

@api_bp.route("/api/agent/recommend", methods=["POST"])
def recommend():
    """
    The main endpoint to get a recommendation strategy from the agent.
    """
    # 1. Get and log the request data
    data = request.get_json()
    print(f"[{datetime.datetime.now()}] Received request: {data}")

    # 2. Validate the request
    is_valid, error_message = validate_recommend_request(data)
    if not is_valid:
        print(f"[{datetime.datetime.now()}] Invalid request: {error_message}")
        return jsonify({"error": error_message}), 400

    # 3. Call the Recommendation Agent from Phase 1
    try:
        decision = agent.decide(data)
        print(f"[{datetime.datetime.now()}] Agent returned decision: {decision}")
        return jsonify(decision)
    except Exception as e:
        print(f"[{datetime.datetime.now()}] Error during agent execution: {e}")
        return jsonify({"error": "Internal server error during agent execution."}), 500
