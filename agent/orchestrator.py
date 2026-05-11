# agent/orchestrator.py
"""
AgentOrchestrator：多 Agent 统一编排器。
替换现有 AgentManager，协调 RouterAgent → AnalysisAgent → RecommendationAgent → ExplanationAgent 的调用链路。
提供与现有 AgentManager.process_user_request 完全相同的方法签名，确保 API 向后兼容。
"""
import logging
from typing import Generator, Optional, Union

from agent.agents.router_agent import RouterAgent
from agent.agents.analysis_agent import AnalysisAgent
from agent.agents.recommendation_agent import RecommendationAgent
from agent.agents.explanation_agent import ExplanationAgent
from agent.agents.chitchat_agent import ChitchatAgent
from agent.agents.structured_context import StructuredContext
from agent.session_manager import session_manager, _sessions

logger = logging.getLogger(__name__)

# Session 存储中的追问轮次键名
CLARIFY_ROUND_KEY = "clarify_round"
# 上一轮是否为追问消息的标记键名
LAST_WAS_CLARIFY_KEY = "last_was_clarify"


class AgentOrchestrator:
    """
    多 Agent 统一编排器。

    编排流程：
    1. RouterAgent 意图分类
    2. 根据意图类型分发：
       - chitchat → ChitchatAgent
       - explicit_query → 直接构造 StructuredContext → RecommendationAgent
       - vague_recommendation / mixed → AnalysisAgent → RecommendationAgent
    3. RecommendationAgent 执行工具调用
    4. ExplanationAgent 生成推荐理由
    """

    def __init__(self):
        self.router = RouterAgent()
        self.analyzer = AnalysisAgent()
        self.recommender = RecommendationAgent()
        self.explainer = ExplanationAgent()
        self.chitchatter = ChitchatAgent()

    def process_user_request(
        self,
        user_id: str,
        user_message: str,
        preference_context: Optional[dict] = None,
        session_id: Optional[str] = None,
        stream: bool = False,
    ) -> Union[tuple[str, list, str], tuple[Generator, list, str]]:
        """
        处理用户请求，返回 AI 回复和推荐结果。
        方法签名与现有 AgentManager.process_user_request 完全一致。

        Args:
            user_id: 用户 ID
            user_message: 用户输入的自然语言消息
            preference_context: 用户偏好上下文 {'genres', 'directors', 'actors'}
            session_id: 对话 session ID，None 时自动创建
            stream: 是否启用流式输出

        Returns:
            (nl_response, structured_results, session_id) 三元组
            - nl_response: 自然语言回复（stream=True 时为 token 生成器）
            - structured_results: 推荐结果列表
            - session_id: 本次使用的 session ID
        """
        try:
            return self._orchestrate(
                user_id, user_message, preference_context, session_id, stream
            )
        except Exception as e:
            logger.error(f"AgentOrchestrator 编排异常：{e}", exc_info=True)
            error_msg = "抱歉，处理您的请求时出现了问题，请稍后再试。"
            return error_msg, [], session_id or ""

    def _orchestrate(
        self,
        user_id: str,
        user_message: str,
        preference_context: Optional[dict],
        session_id: Optional[str],
        stream: bool,
    ) -> Union[tuple[str, list, str], tuple[Generator, list, str]]:
        """编排主流程。"""
        # 1. 获取或创建 session
        session_id, history = session_manager.get_or_create(session_id)

        # 2. RouterAgent 意图分类
        intent_type = self.router.route(user_message, history)
        logger.info(f"[{session_id}] RouterAgent 意图分类：{intent_type}")

        # 3. 根据意图类型分发
        if intent_type == "chitchat":
            return self._handle_chitchat(user_message, history, session_id)

        # 4. 管理 clarify_round
        clarify_round = self._get_and_update_clarify_round(session_id, intent_type, history)

        # 5. explicit_query：直接构造 StructuredContext，跳过 AnalysisAgent
        if intent_type == "explicit_query":
            ctx = StructuredContext(
                skip_preference_injection=True,
                confidence="high",
                intent="search_content",
                context=user_message[:200],
            )
            return self._handle_recommendation(
                user_id, user_message, ctx, preference_context,
                history, session_id, stream,
            )

        # 6. vague_recommendation / mixed：通过 AnalysisAgent 分析
        ctx = self.analyzer.analyze(user_message, history, clarify_round)

        # 7. 如果需要追问，返回追问消息
        if ctx.clarify_question:
            session_manager.append(session_id, "user", user_message)
            session_manager.append(session_id, "assistant", ctx.clarify_question)
            self._mark_clarify(session_id, True)
            logger.info(f"[{session_id}] AnalysisAgent 追问（第 {clarify_round + 1} 轮）：{ctx.clarify_question}")
            return ctx.clarify_question, [], session_id

        # 8. 需求清晰或追问轮次已达上限，执行推荐
        self._mark_clarify(session_id, False)
        return self._handle_recommendation(
            user_id, user_message, ctx, preference_context,
            history, session_id, stream,
        )

    def _handle_chitchat(
        self,
        user_message: str,
        history: list,
        session_id: str,
    ) -> tuple[str, list, str]:
        """处理闲聊意图。"""
        nl_response = self.chitchatter.chat(user_message, history)
        session_manager.append(session_id, "user", user_message)
        session_manager.append(session_id, "assistant", nl_response)
        return nl_response, [], session_id

    def _handle_recommendation(
        self,
        user_id: str,
        user_message: str,
        ctx: StructuredContext,
        preference_context: Optional[dict],
        history: list,
        session_id: str,
        stream: bool,
    ) -> Union[tuple[str, list, str], tuple[Generator, list, str]]:
        """执行推荐链路：RecommendationAgent → ExplanationAgent。"""
        # 构建发给 RecommendationAgent 的消息列表
        messages = []
        windowed = session_manager.get_windowed_history(session_id, window=10)
        messages.extend(windowed)
        messages.append({"role": "user", "content": user_message})

        # RecommendationAgent 执行工具调用
        structured_results = self.recommender.execute(
            user_id=user_id,
            ctx=ctx,
            preference_context=preference_context,
            messages=messages,
        )

        # 生成自然语言回复
        nl_response = self.recommender.generate_response(
            results=structured_results,
            ctx=ctx,
            messages=messages,
            preference_context=preference_context,
            stream=stream,
        )

        # ExplanationAgent 生成推荐理由（非流式模式下）
        if structured_results and not stream:
            try:
                structured_results = self.explainer.explain(structured_results, ctx)
            except Exception as e:
                logger.warning(f"ExplanationAgent 推荐理由生成失败，跳过：{e}")

        # 更新 session 历史
        session_manager.append(session_id, "user", user_message)
        if not stream:
            session_manager.append(
                session_id, "assistant",
                nl_response if isinstance(nl_response, str) else ""
            )

        logger.info(f"[{session_id}] 推荐完成，返回 {len(structured_results)} 条结果")
        return nl_response, structured_results, session_id

    def _get_and_update_clarify_round(
        self,
        session_id: str,
        intent_type: str,
        history: list,
    ) -> int:
        """
        获取当前追问轮次，并根据上下文决定是否重置。

        重置条件：用户发起新的推荐请求（非追问回答）。
        判断依据：上一条 assistant 消息不是追问消息。
        """
        if session_id not in _sessions:
            return 0

        session_data = _sessions[session_id]
        current_round = session_data.get(CLARIFY_ROUND_KEY, 0)
        last_was_clarify = session_data.get(LAST_WAS_CLARIFY_KEY, False)

        # 如果上一轮不是追问，说明是新的推荐请求，重置轮次
        if not last_was_clarify:
            current_round = 0
            session_data[CLARIFY_ROUND_KEY] = 0

        return current_round

    def _mark_clarify(self, session_id: str, is_clarify: bool) -> None:
        """标记当前轮次是否为追问。"""
        if session_id not in _sessions:
            return

        session_data = _sessions[session_id]

        if is_clarify:
            session_data[CLARIFY_ROUND_KEY] = session_data.get(CLARIFY_ROUND_KEY, 0) + 1
            session_data[LAST_WAS_CLARIFY_KEY] = True
        else:
            session_data[LAST_WAS_CLARIFY_KEY] = False
