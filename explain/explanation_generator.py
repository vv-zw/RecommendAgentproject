# explain/explanation_generator.py
from typing import Dict, Any, List

# 定义推荐理由模板
EXPLANATION_TEMPLATES = {
    "ncf": "考虑到您过去喜欢的电影，为您推荐相似用户也喜欢的这部",
    "textcnn": "基于您提到的内容，为您推荐情节或主题相似的这部",
    "rules": "根据您偏好的类型为您推荐这部热门电影",
    "rag": "为您找到与您描述最匹配的这部电影",
    "default": "为您推荐这部优质电影"
}

def generate_per_item_explanations(recommendations: List[Dict[str, Any]]) -> Dict[int, str]:
    """
    Generates a specific explanation for each recommended item.
    :param recommendations: The list of final recommendations, which must contain a 'sources' key.
    :return: A dictionary mapping movie_id to its explanation string.
    """
    explanations = {}
    for item in recommendations:
        movie_id = item["movie_id"]
        sources = item.get("sources", [])
        
        reasons = []
        # 按优先级添加理由，避免重复
        if "textcnn" in sources:
            reasons.append(EXPLANATION_TEMPLATES["textcnn"])
        elif "ncf" in sources:
            reasons.append(EXPLANATION_TEMPLATES["ncf"])
        elif "rules" in sources:
            reasons.append(EXPLANATION_TEMPLATES["rules"])
        
        if not reasons:
            final_explanation = EXPLANATION_TEMPLATES["default"]
        else:
            final_explanation = "，".join(reasons) + "。"
            
        explanations[movie_id] = final_explanation
        
    return explanations

if __name__ == '__main__':
    print("--- Testing explanation_generator.py ---")
    
    mock_recs = [
        {
            "movie_id": 12, "title": "星际穿越", "score": 0.93, 
            "sources": ["ncf", "textcnn", "rules"]
        },
        {
            "movie_id": 8, "title": "火星救援", "score": 0.89, 
            "sources": ["ncf", "rules"]
        },
        {
            "movie_id": 15, "title": "疯狂动物城", "score": 0.85, 
            "sources": ["rules"]
        }
    ]
    
    explanations = generate_per_item_explanations(mock_recs)
    
    import json
    print(json.dumps(explanations, indent=2, ensure_ascii=False))
