# orchestrator/explanation_generator.py
from typing import Dict, Any, List

def generate_explanation(agent_decision: Dict[str, Any], orchestrator_output: Dict[str, Any]) -> List[str]:
    """
    Generates a human-readable explanation of the recommendation process.
    :param agent_decision: The decision object from the Agent.
    :param orchestrator_output: The final output from the Orchestrator.
    :return: A list of strings, where each string is a step in the explanation.
    """
    explanation = []
    intent = agent_decision.get("intent")
    keywords = agent_decision.get("keywords")
    genres = agent_decision.get("genres")
    strategy = agent_decision.get("strategy", {})
    debug_trace = orchestrator_output.get("debug_trace", {})

    # Step 1: Explain intent recognition
    explanation.append(f"🧠 **第一步：理解您的意图**")
    explanation.append(f"- 我判断您的意图是：**{intent}**。")
    if keywords:
        explanation.append(f"- 我提取出的核心关键词是：**'{', '.join(keywords)}'**。")
    if genres:
        explanation.append(f"- 您似乎对 **{', '.join(genres)}** 类型的电影感兴趣。")

    # Step 2: Explain strategy decision
    explanation.append(f"🤖 **第二步：制定推荐策略**")
    active_models = [model.upper() for model, used in debug_trace.items() if used]
    if not active_models:
        explanation.append("- 根据您的请求，我决定不使用任何模型。")
    else:
        explanation.append(f"- 根据您的请求和历史，我决定融合以下模型来为您推荐：**{', '.join(active_models)}**。")
    
    if strategy.get("use_ncf") is False:
        explanation.append("- (由于是冷启动用户，我排除了个性化协同过滤模型 NCF)。")

    # Step 3: Explain the result
    explanation.append(f"🎬 **第三步：生成与融合推荐结果**")
    if not orchestrator_output.get("recommendations"):
        explanation.append("- 抱歉，根据您的要求，我没有找到合适的电影。")
    else:
        explanation.append("- 我将上述模型的结果进行了加权融合与排序，并为您过滤掉了已看过的电影，最终得到了以下推荐列表。")

    return explanation

if __name__ == '__main__':
    print("--- Testing explanation_generator.py ---")
    
    # Mock data for testing
    mock_agent_decision = {
        "intent": "recommend", "keywords": ["流浪地球"], "genres": ["科幻"],
        "strategy": {"use_ncf": True, "use_textcnn": True, "use_rules": True}
    }
    mock_orchestrator_output = {
        "recommendations": [{"movie_id": 12, "title": "星际穿越"}],
        "debug_trace": {"ncf_used": True, "textcnn_used": True, "rules_used": True}
    }

    exp = generate_explanation(mock_agent_decision, mock_orchestrator_output)
    
    print("Generated Explanation:")
    for line in exp:
        print(line)
