# agent/agents/structured_context.py
"""
StructuredContext：多 Agent 协作架构中的结构化需求上下文。
由 AnalysisAgent 输出，贯穿 Router → Analysis → Recommendation → Explanation 整个链路。
"""
from dataclasses import dataclass, field


@dataclass
class StructuredContext:
    """结构化需求上下文，包含用户意图、偏好、情绪等信息。"""
    intent: str = "recommend_movie"
    confidence: str = "low"           # high / medium / low
    mood: str = ""                     # 情绪描述，如"轻松解压"
    genres: list = field(default_factory=list)       # 类型列表，如 ["喜剧", "动画"]
    keywords: list = field(default_factory=list)     # 关键词，如 ["父女情", "末日"]
    directors: list = field(default_factory=list)    # 导演列表
    actors: list = field(default_factory=list)       # 演员列表
    content_type: str = ""             # movie / series / ""（不限）
    context: str = ""                  # 场景描述，如"用户压力大，需要治愈系内容"
    skip_preference_injection: bool = False  # True 时推荐 Agent 不强制注入用户偏好
    clarify_question: str = ""         # 非空时表示需要向用户追问
    clarify_round: int = 0             # 当前追问轮次，最大 3
