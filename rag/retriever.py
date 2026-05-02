# rag/retriever.py
import json
import os
from typing import List, Dict, Any

from rag.embedding import TfidfVectorizer
from rag.similarity import cosine_similarity

class MovieRetriever:
    """
    Handles loading movie data, vectorizing it, and retrieving top candidates.
    """
    def __init__(self, data_path: str):
        """
        Initializes the retriever by loading and vectorizing the movie data.
        :param data_path: Path to the movies.json file.
        """
        self._vectorizer = TfidfVectorizer()
        self._movies: List[Dict[str, Any]] = []
        self._movie_vectors: List[Dict[str, float]] = []

        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Data file not found at: {data_path}")

        self._load_and_process_data(data_path)

    def _load_and_process_data(self, data_path: str):
        """Loads movie data and creates TF-IDF vectors for the corpus."""
        with open(data_path, 'r', encoding='utf-8') as f:
            self._movies = json.load(f)

        # Create a text corpus by combining title and description
        corpus = [f"{movie['title']} {movie['description']}" for movie in self._movies]

        # Fit the vectorizer and transform the corpus into vectors
        self._movie_vectors = self._vectorizer.fit_transform(corpus)

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Searches for the most relevant movies based on a query.
        :param query: The user's search query.
        :param top_k: The number of candidates to return.
        :return: A list of candidate movies with their scores.
        """
        if not self._movies:
            return []

        # Transform the query into a TF-IDF vector
        query_vector = self._vectorizer.transform([query])[0]

        # Calculate similarity scores for all movies
        scores = []
        for i, movie_vector in enumerate(self._movie_vectors):
            score = cosine_similarity(query_vector, movie_vector)
            if score > 0:
                scores.append({
                    "movie_id": self._movies[i]["movie_id"],
                    "title": self._movies[i]["title"],
                    "score": score
                })

        # Sort by score in descending order and return the top_k results
        scores.sort(key=lambda x: x['score'], reverse=True)
        return scores[:top_k]

if __name__ == '__main__':
    print("--- Testing retriever.py ---")
    
    # Assume the script is run from the project root `d:\RecommendAgentProject`
    # and the data file is at `data/datasets/movies.json`
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir) # up one level from /rag
    data_file = os.path.join(project_root, 'data', 'datasets', 'movies.json')

    try:
        retriever = MovieRetriever(data_path=data_file)
        
        test_query = "关于太空旅行和拯救人类的科幻电影"
        print(f"\nSearching for: '{test_query}'")
        
        results = retriever.search(query=test_query, top_k=3)
        
        print("\nSearch Results:")
        if results:
            for res in results:
                print(f"  - Movie ID: {res['movie_id']}, Title: {res['title']}, Score: {res['score']:.4f}")
        else:
            print("  No results found.")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure the data file exists at the correct path.")
