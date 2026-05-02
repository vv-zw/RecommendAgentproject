# recommendation/ncf.py (Mock)
from typing import List, Dict, Any

def get_ncf_recommendations(user_id: int, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Mocks the output of a Neural Collaborative Filtering (NCF) model.
    Returns a fixed list of movies with high scores for known users.
    """
    print(f"[Mock NCF] Getting recommendations for user_id: {user_id}")
    if user_id == 1: # Assume user 1 is a known user
        return [
            {"movie_id": 12, "title": "星际穿越", "score": 0.95},
            {"movie_id": 8, "title": "火星救援", "score": 0.91},
            {"movie_id": 1, "title": "流浪地球", "score": 0.88}, # User has seen this
        ][:top_k]
    return [] # Return empty for unknown users
