# orchestrator/filter.py
from typing import List, Dict, Any

def filter_recommendations(
    recommendations: List[Dict[str, Any]], 
    seen_movie_ids: List[int] = None
) -> List[Dict[str, Any]]:
    """
    Filters recommendations by removing duplicates and already seen items.
    :param recommendations: A list of candidate movies.
    :param seen_movie_ids: A list of movie IDs the user has already seen.
    :return: A cleaned list of recommendations.
    """
    if seen_movie_ids is None:
        seen_movie_ids = []

    filtered_recs = []
    processed_ids = set()

    for rec in recommendations:
        movie_id = rec["movie_id"]
        if movie_id not in processed_ids and movie_id not in seen_movie_ids:
            filtered_recs.append(rec)
            processed_ids.add(movie_id)
            
    return filtered_recs

if __name__ == '__main__':
    print("--- Testing filter.py ---")
    
    test_recs = [
        {"movie_id": 1, "title": "A", "score": 0.9},
        {"movie_id": 2, "title": "B", "score": 0.8},
        {"movie_id": 1, "title": "A", "score": 0.85}, # Duplicate
        {"movie_id": 3, "title": "C", "score": 0.7}, # Already seen
    ]
    
    seen_ids = [3, 4]
    
    print("Original:", test_recs)
    print("Seen IDs:", seen_ids)
    
    cleaned_recs = filter_recommendations(test_recs, seen_ids)
    
    print("Cleaned:", cleaned_recs)
    # Expected output: [{'movie_id': 1, ...}, {'movie_id': 2, ...}]
