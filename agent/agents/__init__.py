# agent/agents/__init__.py
"""
多 Agent 协作架构子包。
包含 RouterAgent、AnalysisAgent、RecommendationAgent、ExplanationAgent、ChitchatAgent
以及核心数据结构 StructuredContext。
"""
from agent.agents.structured_context import StructuredContext
from agent.agents.router_agent import RouterAgent
from agent.agents.analysis_agent import AnalysisAgent
from agent.agents.recommendation_agent import RecommendationAgent
from agent.agents.explanation_agent import ExplanationAgent
from agent.agents.chitchat_agent import ChitchatAgent

__all__ = [
    "StructuredContext",
    "RouterAgent",
    "AnalysisAgent",
    "RecommendationAgent",
    "ExplanationAgent",
    "ChitchatAgent",
]
