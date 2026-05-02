# orchestrator/fusion.py
from typing import List, Dict, Any

from orchestrator.score_engine import calculate_fused_scores
from config import settings # Import from the new config file

def get_fusion_weights(agent_decision: Dict[str, Any], query: str) -> Dict[str, float]:
    """
    Determines the fusion weights based on the agent's decision and query.
    :param agent_decision: The decision object from the Agent.
    :param query: The original user query.
    :return: A dictionary of weights for each source.
    """
    strategy = agent_decision.get("strategy", {})
    is_cold_start = not strategy.get("use_ncf", True) # Infer cold start if NCF is disabled

    # Load weights from the central config
    if is_cold_start:
        weights = settings.COLD_START_FUSION_WEIGHTS.copy()
    elif any(k in query for k in ["类似", "相似"]):
        weights = settings.SEMANTIC_QUERY_FUSION_WEIGHTS.copy()
    else:
        weights = settings.DEFAULT_FUSION_WEIGHTS.copy()

    # Normalize weights to only include active strategies
    active_weight_sum = sum(weights[source] for source, active in strategy.items() if active and source in weights)
    
    final_weights = {}
    if active_weight_sum > 0:
        for source, weight in weights.items():
            if strategy.get(source, False):
                final_weights[source] = weight / active_weight_sum # Normalize

    return final_weights

def fuse_recommendations(
    results: Dict[str, List[Dict[str, Any]]],
    agent_decision: Dict[str, Any],
    query: str
) -> List[Dict[str, Any]]:
    """
    Orchestrates the fusion of results from multiple recommendation sources.
    :param results: Raw results from different models.
    :param agent_decision: The decision from the Agent.
    :param query: The original user query.
    :return: A single, fused, and sorted list of recommendations.
    """
    weights = get_fusion_weights(agent_decision, query)
    print(f"[Fusion] Using final weights: {weights}")
    
    fused_list = calculate_fused_scores(results, weights)
    
    return fused_list
