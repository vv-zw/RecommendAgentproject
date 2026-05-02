# rag/rag_engine.py
import json
import os
from typing import Dict, Any

from rag.retriever import MovieRetriever

class RagEngine:
    """
    The main entry point for the RAG semantic retrieval module.
    """
    def __init__(self, data_path: str):
        """
        Initializes the engine by creating a MovieRetriever instance.
        :param data_path: Path to the movies.json file.
        """
        try:
            self._retriever = MovieRetriever(data_path=data_path)
        except FileNotFoundError as e:
            print(f"[RagEngine Error] {e}")
            self._retriever = None

    def search(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs a search based on the input request and returns the candidates.
        :param request_data: A dictionary with 'query' and 'top_k'.
        :return: A dictionary containing the query and a list of candidates.
        """
        query = request_data.get("query", "")
        top_k = request_data.get("top_k", 10)

        if not self._retriever or not query:
            return {"query": query, "candidates": []}

        candidates = self._retriever.search(query=query, top_k=top_k)

        return {
            "query": query,
            "candidates": candidates
        }

def run_tests():
    """
    Runs a set of test cases to verify the RAG engine's functionality.
    """
    print("--- Running RAG Engine Test Cases ---")
    
    # Determine the path to the data file, assuming execution from the project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    data_file = os.path.join(project_root, 'data', 'datasets', 'movies.json')

    engine = RagEngine(data_path=data_file)

    # Test Case 1: Sci-fi movie query
    test_case_1 = {
        "query": "关于太空旅行和拯救地球的科幻电影",
        "top_k": 3
    }
    print("\n[Test Case 1: Sci-fi Query]")
    print("Input:", json.dumps(test_case_1, indent=2, ensure_ascii=False))
    output_1 = engine.search(test_case_1)
    print("Output:", json.dumps(output_1, indent=2, ensure_ascii=False))

    # Test Case 2: Comedy movie query
    test_case_2 = {
        "query": "一个关于动物的搞笑喜剧",
        "top_k": 2
    }
    print("\n[Test Case 2: Comedy Query]")
    print("Input:", json.dumps(test_case_2, indent=2, ensure_ascii=False))
    output_2 = engine.search(test_case_2)
    print("Output:", json.dumps(output_2, indent=2, ensure_ascii=False))

    # Test Case 3: Query that may not have strong matches
    test_case_3 = {
        "query": "一个关于药的故事",
        "top_k": 2
    }
    print("\n[Test Case 3: Vague Query]")
    print("Input:", json.dumps(test_case_3, indent=2, ensure_ascii=False))
    output_3 = engine.search(test_case_3)
    print("Output:", json.dumps(output_3, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    # To run this script directly, you need to make sure the parent directory
    # is in Python's path to allow the `from rag...` imports.
    # Example of running from the root directory `d:\RecommendAgentProject\`:
    # python -m rag.rag_engine
    run_tests()
