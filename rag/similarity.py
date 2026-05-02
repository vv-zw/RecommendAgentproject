# rag/similarity.py
import math
from typing import Dict

def cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    """
    Calculates the cosine similarity between two vectors represented as dictionaries.
    This implementation is from scratch and does not use any external libraries.
    :param vec1: The first vector (e.g., {word: tf-idf_score}).
    :param vec2: The second vector.
    :return: The cosine similarity, a float between 0 and 1.
    """
    # Find the intersection of words to calculate the dot product
    intersection = set(vec1.keys()) & set(vec2.keys())
    
    # Calculate the dot product
    dot_product = sum(vec1[word] * vec2[word] for word in intersection)

    # Calculate the magnitude (L2 norm) of the first vector
    norm_vec1 = math.sqrt(sum(val**2 for val in vec1.values()))

    # Calculate the magnitude (L2 norm) of the second vector
    norm_vec2 = math.sqrt(sum(val**2 for val in vec2.values()))

    # Calculate cosine similarity
    if norm_vec1 == 0 or norm_vec2 == 0:
        # If one of the vectors is a zero vector, similarity is 0
        return 0.0
    else:
        return dot_product / (norm_vec1 * norm_vec2)

if __name__ == '__main__':
    print("--- Testing similarity.py ---")
    
    # Example vectors
    v1 = {'a': 1, 'b': 2, 'c': 3}
    v2 = {'b': 4, 'c': 5, 'd': 6}
    v3 = {'x': 1, 'y': 2}
    v4 = {'a': 1, 'b': 2, 'c': 3} # Identical to v1

    sim_12 = cosine_similarity(v1, v2)
    sim_13 = cosine_similarity(v1, v3)
    sim_14 = cosine_similarity(v1, v4)

    print(f"Similarity between v1 and v2: {sim_12:.4f}") # Should be non-zero
    print(f"Similarity between v1 and v3: {sim_13:.4f}") # Should be 0.0
    print(f"Similarity between v1 and v4: {sim_14:.4f}") # Should be 1.0
