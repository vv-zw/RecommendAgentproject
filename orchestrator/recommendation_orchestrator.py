# orchestrator/recommendation_orchestrator.py
import json
from typing import Dict, Any

# Mock imports representing the existing recommendation systems
from mock_recommenders.ncf import get_ncf_recommendations
from mock_recommenders.textcnn import get_textcnn_recommendations
from mock_recommenders.rule_based import get_rule_based_recommendations

# Orchestrator components
from orchestrator.fusion import fuse_recommendations
from orchestrator.filter import filter_recommendations

class RecommendationOrchestrator:
    """
    The main orchestrator that schedules and fuses recommendations.
    """
    def orchestrate(self, request_data: Dict[str, Any], fusion_weights_override: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Takes an agent decision and produces a final recommendation list.
        :param request_data: The input data including user_id, query, and agent_decision.
        :param fusion_weights_override: Optional weights to override default logic.
        :return: A dictionary with the final recommendation list and debug info.
        """
        user_id = request_data["user_id"]
        query = request_data["query"]
        agent_decision = request_data["agent_decision"]
        strategy = agent_decision.get("strategy", {})

        raw_results = {}

        # Step 1: Call recommendation models based on agent strategy
        if strategy.get("use_ncf", False):
            raw_results["ncf"] = get_ncf_recommendations(user_id)

        if strategy.get("use_textcnn", False):
            raw_results["textcnn"] = get_textcnn_recommendations(query)

        if strategy.get("use_rules", False):
            raw_results["rules"] = get_rule_based_recommendations(agent_decision.get("genres", []))

        # Step 2: Fuse the results from different sources
        # The fusion function now reads weights from config, so we just pass the decision
        fused_list = fuse_recommendations(raw_results, agent_decision, query)

        # Step 3: Filter the results (e.g., remove seen items)
        # In a real system, seen_movie_ids would come from a user profile service
        seen_ids = [1] # Mock: user has seen "流浪地球"
        final_list = filter_recommendations(fused_list, seen_movie_ids=seen_ids)

        # Step 4: Prepare the final output
        return {
            "recommendations": final_list[:10], # Limit to top 10
            "raw_results": raw_results # Pass raw results for debug trace
        }

def run_tests():
    """
    Runs a set of test cases to verify the orchestrator's functionality.
    """
    orchestrator = RecommendationOrchestrator()
    print("--- Running Recommendation Orchestrator Test Cases ---")

    # Test Case 1: Standard user, semantic query
    test_case_1 = {
        "user_id": 1,
        "query": "推荐类似流浪地球的电影",
        "agent_decision": {
            "intent": "recommend", "keywords": ["流浪地球"], "genres": ["科幻"],
            "strategy": {"use_ncf": True, "use_textcnn": True, "use_rules": True, "use_rag": False},
            "explain_required": True
        }
    }
    print("\n[Test Case 1: Standard User, Semantic Query]")
    print("Input:", json.dumps(test_case_1, indent=2, ensure_ascii=False))
    output_1 = orchestrator.orchestrate(test_case_1)
    print("Output:", json.dumps(output_1, indent=2, ensure_ascii=False))

    # Test Case 2: Cold-start user
    test_case_2 = {
        "user_id": 2, # A user for whom NCF returns nothing
        "query": "有没有好看的科幻喜剧",
        "agent_decision": {
            "intent": "recommend", "keywords": [], "genres": ["科幻", "喜剧"],
            "strategy": {"use_ncf": False, "use_textcnn": True, "use_rules": True, "use_rag": False},
            "explain_required": True
        }
    }
    print("\n[Test Case 2: Cold-Start User]")
    print("Input:", json.dumps(test_case_2, indent=2, ensure_ascii=False))
    output_2 = orchestrator.orchestrate(test_case_2)
    print("Output:", json.dumps(output_2, indent=2, ensure_ascii=False))

    # Test Case 3: Only rule-based strategy is active
    test_case_3 = {
        "user_id": 1,
        "query": "科幻",
        "agent_decision": {
            "intent": "recommend", "keywords": [], "genres": ["科幻"],
            "strategy": {"use_ncf": False, "use_textcnn": False, "use_rules": True, "use_rag": False},
            "explain_required": False
        }
    }
    print("\n[Test Case 3: Rule-Based Only]")
    print("Input:", json.dumps(test_case_3, indent=2, ensure_ascii=False))
    output_3 = orchestrator.orchestrate(test_case_3)
    print("Output:", json.dumps(output_3, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    # To run this script, you need to make sure the parent directory is in Python's path.
    # Example of running from the root directory `d:\RecommendAgentProject\`:
    # python -m orchestrator.recommendation_orchestrator
    run_tests()
