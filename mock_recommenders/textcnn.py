# mock_recommenders/textcnn.py (Mock)
from typing import List, Dict, Any

def get_textcnn_recommendations(query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Mocks the output of a TextCNN model based on query keywords.
    """
    print(f"[Mock TextCNN] Getting recommendations for query: '{query}'")
    if "地球" in query or "太空" in query:
        return [
            {"movie_id": 12, "title": "星际穿越", "score": 0.92},
            {"movie_id": 8, "title": "火星救援", "score": 0.88},
            {"movie_id": 22, "title": "银翼杀手2049", "score": 0.85},
        ][:top_k]
    if "喜剧" in query:
        return [
            {"movie_id": 15, "title": "疯狂动物城", "score": 0.93},
        ][:top_k]
    return []
