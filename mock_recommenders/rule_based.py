# mock_recommenders/rule_based.py (Mock)
from typing import List, Dict, Any

def get_rule_based_recommendations(genres: List[str], top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Mocks a rule-based system that recommends popular movies from given genres.
    """
    print(f"[Mock Rule] Getting recommendations for genres: {genres}")
    recommendations = []
    if "科幻" in genres:
        recommendations.extend([
            {"movie_id": 12, "title": "星际穿越", "score": 0.85}, # High general popularity
            {"movie_id": 22, "title": "银翼杀手2049", "score": 0.82},
        ])
    if "喜剧" in genres:
        recommendations.extend([
            {"movie_id": 15, "title": "疯狂动物城", "score": 0.90}, # High general popularity
            {"movie_id": 2, "title": "我不是药神", "score": 0.88},
        ])
    return recommendations[:top_k]
