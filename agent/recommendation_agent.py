# agent/recommendation_agent.py
import json
from typing import Dict, Any

# Import from other modules in the agent package
from agent.intent_parser import parse_intent, extract_features
from agent.strategy_selector import select_strategy

class RecommendationAgent:
    """
    The main agent that processes user requests and outputs a strategy JSON.
    """
    def decide(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes the user request and decides on a recommendation strategy.
        :param request_data: The input JSON from the user.
        :return: A structured JSON decision.
        """
        query = request_data.get("query", "")
        context = request_data.get("context", {})

        # 1. Intent Parsing
        intent = parse_intent(query)

        # 2. Feature Extraction
        features = extract_features(query)

        # 3. Strategy Decision
        strategy_decision = select_strategy(intent, context)

        # 4. Assemble the final JSON output
        final_decision = {
            "intent": intent,
            "keywords": features.get("keywords", []),
            "genres": features.get("genres", []),
            "mood": features.get("mood", None),
            **strategy_decision
        }

        return final_decision

def run_tests():
    """
    Runs a set of test cases to verify the agent's functionality.
    """
    agent = RecommendationAgent()
    print("--- Running Recommendation Agent Test Cases ---")

    # Test Case 1: Standard recommendation for a user with history
    test_case_1 = {
        "user_id": 1,
        "query": "推荐类似流浪地球的电影",
        "context": {
            "device": "web",
            "history": [123, 456]  # User has viewing history
        }
    }
    print("\n[Test Case 1: Standard Recommendation]")
    print("Input:", json.dumps(test_case_1, indent=2, ensure_ascii=False))
    output_1 = agent.decide(test_case_1)
    print("Output:", json.dumps(output_1, indent=2, ensure_ascii=False))

    # Test Case 2: Recommendation for a cold-start user
    test_case_2 = {
        "user_id": 2,
        "query": "有没有好看的科幻动画推荐",
        "context": {
            "device": "mobile",
            "history": []  # Cold-start user
        }
    }
    print("\n[Test Case 2: Cold-Start User]")
    print("Input:", json.dumps(test_case_2, indent=2, ensure_ascii=False))
    output_2 = agent.decide(test_case_2)
    print("Output:", json.dumps(output_2, indent=2, ensure_ascii=False))

    # Test Case 3: User asks for an explanation
    test_case_3 = {
        "user_id": 1,
        "query": "为什么给我推荐这部电影？",
        "context": {
            "device": "web",
            "history": [123, 456]
        }
    }
    print("\n[Test Case 3: Explanation Request]")
    print("Input:", json.dumps(test_case_3, indent=2, ensure_ascii=False))
    output_3 = agent.decide(test_case_3)
    print("Output:", json.dumps(output_3, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    # To run this script directly, you need to make sure the parent directory
    # is in Python's path to allow the `from agent...` imports.
    # Example of running from the root directory `d:\RecommendAgentProject\`:
    # python -m agent.recommendation_agent
    run_tests()
