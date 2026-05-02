# agent/intent_parser.py
import json
from typing import Dict, Any, List

# A very simple, predefined list of known genres for extraction.
KNOWN_GENRES = ["科幻", "喜剧", "动作", "爱情", "恐怖", "悬疑", "动画"]

def parse_intent(query: str) -> str:
    """
    Parses the user's intent from the query.
    :param query: The user's input string.
    :return: The identified intent ('recommend', 'search', 'explain', or 'unknown').
    """
    if any(keyword in query for keyword in ["为什么", "解释"]):
        return "explain"
    if any(keyword in query for keyword in ["搜索", "查找"]):
        return "search"
    if any(keyword in query for keyword in ["推荐", "类似", "找点", "有没有"]):
        return "recommend"
    # Default to recommend if no other intent is clear
    return "recommend"

def extract_features(query: str) -> Dict[str, Any]:
    """
    Extracts features like keywords, genres, and mood from the query.
    This is a simplified implementation for demonstration purposes.
    :param query: The user's input string.
    :return: A dictionary containing extracted features.
    """
    keywords = []
    # A simple heuristic: find words around keywords like "类似" or "关于".
    # This is a placeholder for a real NLP model.
    if "类似" in query:
        parts = query.split("类似")
        if len(parts) > 1:
            keyword_part = parts[1].replace("的电影", "").strip()
            if keyword_part:
                keywords.append(keyword_part)
    elif "关于" in query:
        parts = query.split("关于")
        if len(parts) > 1:
            keyword_part = parts[1].replace("的电影", "").strip()
            if keyword_part:
                keywords.append(keyword_part)
    # A placeholder for extracting a movie name from a simple recommendation query
    elif "推荐" in query and "的" not in query:
         keyword_part = query.replace("推荐", "").replace("一下","").strip()
         if keyword_part and len(keyword_part) > 1:
            keywords.append(keyword_part)


    # Extract genres from the query
    found_genres = [genre for genre in KNOWN_GENRES if genre in query]

    # Mood extraction is not implemented in this phase
    mood = None

    return {
        "keywords": keywords,
        "genres": found_genres,
        "mood": mood
    }

if __name__ == '__main__':
    print("--- Testing intent_parser.py ---")
    test_queries = [
        "推荐类似流浪地球的电影",
        "搜索一下黑客帝国",
        "为什么给我推荐这个？",
        "找点科幻片看看",
        "有没有好笑的喜剧电影"
    ]

    for q in test_queries:
        intent = parse_intent(q)
        features = extract_features(q)
        print(f"Query: '{q}'")
        print(f"  - Intent: {intent}")
        print(f"  - Features: {json.dumps(features, ensure_ascii=False)}\n")
