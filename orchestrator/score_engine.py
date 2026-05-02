# orchestrator/score_engine.py
from typing import List, Dict, Any

def calculate_fused_scores(
    results: Dict[str, List[Dict[str, Any]]],
    weights: Dict[str, float]
) -> List[Dict[str, Any]]:
    """
    Calculates the final weighted score for each movie from different sources.
    :param results: A dictionary where keys are source names (e.g., 'ncf') 
                    and values are lists of recommendations from that source.
    :param weights: A dictionary of weights for each source.
    :return: A list of movies with their final fused scores.
    """
    fused_scores: Dict[int, float] = {}
    movie_details: Dict[int, str] = {}

    for source, recs in results.items():
        weight = weights.get(source, 0)
        if weight == 0:
            continue
        
        for rec in recs:
            movie_id = rec["movie_id"]
            score = rec["score"]
            title = rec["title"]
            
            if movie_id not in fused_scores:
                fused_scores[movie_id] = 0
                movie_details[movie_id] = title
            
            fused_scores[movie_id] += score * weight

    # Convert the fused scores back into a list of dictionaries
    final_recommendations = [
        {
            "movie_id": movie_id,
            "title": movie_details[movie_id],
            "score": score,
            "source": "hybrid"
        }
        for movie_id, score in fused_scores.items()
    ]

    # Sort by the final fused score in descending order
    final_recommendations.sort(key=lambda x: x["score"], reverse=True)
    
    return final_recommendations

if __name__ == '__main__':
    print("--- Testing score_engine.py ---")
    
    test_results = {
        "ncf": [
            {"movie_id": 1, "title": "A", "score": 0.9},
            {"movie_id": 2, "title": "B", "score": 0.8}
        ],
        "textcnn": [
            {"movie_id": 2, "title": "B", "score": 0.85},
            {"movie_id": 3, "title": "C", "score": 0.7}
        ]
    }
    
    test_weights = {"ncf": 0.6, "textcnn": 0.4}
    
    fused = calculate_fused_scores(test_results, test_weights)
    
    print("Input Results:", test_results)
    print("Weights:", test_weights)
    print("Fused and Sorted:", fused)
    # Expected score for movie 2: (0.8 * 0.6) + (0.85 * 0.4) = 0.48 + 0.34 = 0.82
