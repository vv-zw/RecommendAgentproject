# api/routes.py
import datetime
from flask import Blueprint, request, jsonify
import jwt
from functools import wraps
from movie_recommendation.db.user_repository import UserRepository
from movie_recommendation.db.content_repository import ContentRepository
from movie_recommendation.db.feedback_repository import FeedbackRepository

# Initialize Repositories
user_repository = UserRepository()
content_repository = ContentRepository()
feedback_repository = FeedbackRepository()

# Token decorator for securing routes
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Look for the token in the x-access-token header
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        
        if not token:
            return jsonify({'message' : 'Token is missing!'}), 401

        try:
            # Decode the token using the secret key
            # Note: The secret key should be loaded from a secure config, not hardcoded
            data = jwt.decode(token, 'your-secret-key-here', algorithms=["HS256"])
            # Fetch the user from the database based on the token data
            # This part might need adjustment based on what data is in the token
            # Assuming user_id is in the token
            current_user = user_repository.find_user_by_id(data['user_id']) 
            if not current_user:
                return jsonify({'message' : 'User not found!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message' : 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message' : 'Token is invalid!'}), 401
        
        # Pass the user object to the decorated route
        return f(current_user, *args, **kwargs)
    return decorated

# Import the validator
from api.validator import validate_recommend_request

# Import the core logic from Phase 1
from agent.recommendation_agent import AgentManager

# Create a Blueprint
api_bp = Blueprint('api', __name__)

# Instantiate the agent
agent = AgentManager()

@api_bp.route("/health", methods=["GET"])
def health_check():
    """A simple health check endpoint."""
    return jsonify({"status": "ok", "timestamp": datetime.datetime.utcnow().isoformat()})

@api_bp.route("/api/agent/chat", methods=["POST"])
@token_required
def chat(current_user):
    data = request.get_json()
    user_id = current_user['id']
    message = data.get('message')

    if not message:
        return jsonify({"error": "Message is required"}), 400

    try:
        nl_response, structured_results = agent.process_user_request(user_id, message)
        return jsonify({"nl_response": nl_response, "structured_results": structured_results})
    except Exception as e:
        print(f"[{datetime.datetime.now()}] Error during agent execution: {e}")
        return jsonify({"error": "Internal server error during agent execution."}), 500

# User Authentication Routes
@api_bp.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not all([username, email, password]):
        return jsonify({"error": "Missing username, email, or password"}), 400

    if user_repository.find_user_by_username(username):
        return jsonify({"error": "Username already exists"}), 409

    user_id = user_repository.create_user(username, email, password)
    return jsonify({"message": "User registered successfully", "user_id": user_id}), 201

@api_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not all([username, password]):
        return jsonify({"error": "Missing username or password"}), 400

    user = user_repository.find_user_by_username(username)
    if not user or not user_repository.check_password(user, password):
        return jsonify({"error": "Invalid username or password"}), 401

    # Generate JWT token
    token = jwt.encode(
        {'user_id': user['id'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)},
        # This should be a secret key from your app config
        'your-secret-key-here',
        algorithm="HS256"
    )

    return jsonify({"access_token": token, "token_type": "bearer", "user_id": user['id']})

# Media Content Routes
@api_bp.route("/api/movies", methods=["GET"])
def get_movies():
    args = request.args
    page = args.get('page', 1, type=int)
    limit = args.get('limit', 20, type=int)
    genre = args.get('genre', type=str)
    year = args.get('year', type=int)
    sort_by = args.get('sort_by', 'popularity.desc', type=str)

    results, total = content_repository.get_media_list(
        'movie', page, limit, genre, year, sort_by
    )
    return jsonify({"total": total, "page": page, "limit": limit, "results": results})

# Watchlist and History Routes
@api_bp.route("/api/users/<user_id>/watchlist", methods=["GET"])
@token_required
def get_watchlist(current_user, user_id):
    if current_user['id'] != user_id:
        return jsonify({"error": "Unauthorized"}), 403
    watchlist = feedback_repository.get_watchlist(user_id)
    return jsonify({"watchlist": watchlist})

@api_bp.route("/api/users/<user_id>/watchlist", methods=["POST"])
@token_required
def add_to_watchlist(current_user, user_id):
    if current_user['id'] != user_id:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json()
    media_id = data.get('media_id')
    if not media_id:
        return jsonify({"error": "media_id is required"}), 400
    if feedback_repository.add_to_watchlist(user_id, media_id):
        return jsonify({"message": "Item added to watchlist"}), 201
    return jsonify({"error": "Failed to add item"}), 500

@api_bp.route("/api/users/<user_id>/watchlist/<media_id>", methods=["DELETE"])
@token_required
def remove_from_watchlist(current_user, user_id, media_id):
    if current_user['id'] != user_id:
        return jsonify({"error": "Unauthorized"}), 403
    if feedback_repository.remove_from_watchlist(user_id, media_id):
        return jsonify({"message": "Item removed from watchlist"})
    return jsonify({"error": "Failed to remove item or item not found"}), 404

@api_bp.route("/api/users/<user_id>/history", methods=["GET"])
@token_required
def get_watch_history(current_user, user_id):
    if current_user['id'] != user_id:
        return jsonify({"error": "Unauthorized"}), 403
    history = feedback_repository.get_watch_history(user_id)
    return jsonify({"history": history})

@api_bp.route("/api/users/<user_id>/history", methods=["POST"])
@token_required
def add_to_history(current_user, user_id):
    if current_user['id'] != user_id:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json()
    media_id = data.get('media_id')
    if not media_id:
        return jsonify({"error": "media_id is required"}), 400
    if feedback_repository.add_to_watch_history(user_id, media_id):
        return jsonify({"message": "Watch history updated"}), 201
    return jsonify({"error": "Failed to update history"}), 500


@api_bp.route("/api/series", methods=["GET"])
def get_series():
    args = request.args
    page = args.get('page', 1, type=int)
    limit = args.get('limit', 20, type=int)
    genre = args.get('genre', type=str)
    year = args.get('year', type=int)
    sort_by = args.get('sort_by', 'popularity.desc', type=str)

    results, total = content_repository.get_media_list(
        'series', page, limit, genre, year, sort_by
    )
    return jsonify({"total": total, "page": page, "limit": limit, "results": results})

@api_bp.route("/api/movies/<media_id>", methods=["GET"])
def get_movie_details(media_id):
    movie = content_repository.get_media_by_id(media_id)
    if movie and movie['media_type'] == 'movie':
        return jsonify(movie)
    return jsonify({"error": "Movie not found"}), 404

@api_bp.route("/api/series/<media_id>", methods=["GET"])
def get_series_details(media_id):
    series = content_repository.get_media_by_id(media_id)
    if series and series['media_type'] == 'series':
        # Here you would also fetch and attach series_details and episodes
        return jsonify(series)
    return jsonify({"error": "Series not found"}), 404

@api_bp.route("/api/search", methods=["GET"])
def search():
    args = request.args
    query = args.get('query', type=str)
    media_type = args.get('media_type', type=str)
    page = args.get('page', 1, type=int)
    limit = args.get('limit', 20, type=int)

    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    results, total = content_repository.search_media(query, media_type, page, limit)
    return jsonify({"total": total, "page": page, "limit": limit, "results": results})


