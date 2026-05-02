# debug/debug_builder.py
from typing import Dict, Any

def build_debug_trace(
    agent_decision: Dict[str, Any],
    fusion_weights: Dict[str, float],
    raw_results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Constructs the enhanced debug trace object.
    :param agent_decision: The decision from the Agent.
    :param fusion_weights: The final weights used for fusion.
    :param raw_results: The raw, unfiltered results from each model.
    :return: A comprehensive debug trace dictionary.
    """
    models_used = {source: True for source in raw_results.keys()}
    
    # 为每个模型的原始输出添加计数
    raw_counts = {source: len(res) for source, res in raw_results.items()}

    return {
        "agent_decision": agent_decision,
        "models_used": models_used,
        "fusion_weights": fusion_weights,
        "raw_results_count": raw_counts
    }

if __name__ == '__main__':
    print("--- Testing debug_builder.py ---")
    
    mock_agent_decision = {"intent": "recommend", "strategy": {"use_ncf": True}}
    mock_weights = {"ncf": 1.0}
    mock_raw_results = {"ncf": [{"movie_id": 1}, {"movie_id": 2}]}
    
    trace = build_debug_trace(mock_agent_decision, mock_weights, mock_raw_results)
    
    import json
    print(json.dumps(trace, indent=2, ensure_ascii=False))
