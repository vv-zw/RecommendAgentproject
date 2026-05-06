# agent/recommendation_agent.py
"""
AgentManager：LLM 驱动的推荐 Agent 主入口。
协调 NLUProcessor → ToolOrchestrator → ResponseGenerator 的完整链路，
并通过 SessionManager 管理多轮对话历史。
"""
import logging
from typing import Optional, Union, Generator

from agent.agent_core.nlu_processor import NLUProcessor
from agent.agent_core.tool_orchestrator import ToolOrchestrator
from agent.agent_core.response_generator import ResponseGenerator
from agent.session_manager import session_manager
from explain.explanation_generator import explanation_generator

logger = logging.getLogger(__name__)

# Agent System Prompt：定义 Agent 的角色和行为准则
AGENT_SYSTEM_PROMPT = """你是一个专业的影视推荐助手，拥有丰富的电影和剧集知识。

你的职责：
1. 理解用户的推荐需求（类型、情绪、具体影视名称等）
2. 调用合适的工具搜索和检索影视内容
3. 根据用户偏好和搜索结果，给出个性化的推荐

工具使用原则：
- 用户提到具体影视名称时，优先用 search_content 或 get_similar_content
- 用户描述情绪/氛围时（如"温暖治愈"），优先用 semantic_search
- 需要了解用户偏好时，调用 get_user_preference
- 可以组合使用多个工具获取更好的结果

回复原则：
- 用自然流畅的中文回复
- 推荐时说明推荐理由
- 如果找不到合适内容，友好地引导用户换一种描述"""


class AgentManager:
    """LLM 驱动的推荐 Agent 主入口类。"""

    def __init__(self):
        self.nlu_processor = NLUProcessor()
        self.tool_orchestrator = ToolOrchestrator()
        self.response_generator = ResponseGenerator()

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
            - session_id: 本次使用的 session ID（供前端下次传入）
        """
        # 1. 获取或创建 session
        session_id, history = session_manager.get_or_create(session_id)

        # 2. NLU：理解用户意图（传入历史帮助理解上下文）
        intent, entities = self.nlu_processor.process(user_message, history=history)
        logger.info(f"[{session_id}] 用户意图：{intent}，实体：{entities}")

        # 3. 构建发给 ToolOrchestrator 的消息列表
        messages = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]

        # 加入历史对话（滑动窗口）
        windowed = session_manager.get_windowed_history(session_id, window=10)
        messages.extend(windowed)

        # 加入当前用户消息（附带意图和实体信息帮助 LLM 决策）
        user_content = user_message
        if intent not in ("chitchat", "unknown") and (entities.get("genres") or entities.get("keywords") or entities.get("mood")):
            # 把 NLU 提取的信息附加到消息里，帮助 LLM 更好地选择工具
            extras = []
            if entities.get("genres"):
                extras.append(f"类型：{'/'.join(entities['genres'])}")
            if entities.get("keywords"):
                extras.append(f"关键词：{'/'.join(entities['keywords'])}")
            if entities.get("mood"):
                extras.append(f"情绪：{entities['mood']}")
            if entities.get("content_title"):
                extras.append(f"参考影视：{entities['content_title']}")
            if extras:
                user_content = f"{user_message}\n[意图分析：{intent}，{', '.join(extras)}]"

        messages.append({"role": "user", "content": user_content})

        # 4. 处理闲聊意图（不调用工具，直接 LLM 回复）
        if intent == "chitchat":
            nl_response = self._handle_chitchat(user_message, history)
            session_manager.append(session_id, "user", user_message)
            session_manager.append(session_id, "assistant", nl_response if isinstance(nl_response, str) else "")
            return nl_response, [], session_id

        # 5. ToolOrchestrator：Function Calling 循环
        updated_messages, structured_results = self.tool_orchestrator.execute(
            user_id=user_id,
            messages=messages,
            preference_context=preference_context,
        )

        # 6. ResponseGenerator：生成自然语言回复
        nl_response = self.response_generator.generate(
            messages=updated_messages,
            tool_results=structured_results,
            preference_context=preference_context,
            stream=stream,
        )

        # 6.5 ExplanationGenerator：为每条推荐结果添加个性化理由
        if structured_results and not stream:
            try:
                structured_results = explanation_generator.generate_explanations(
                    structured_results, preference_context
                )
            except Exception as e:
                logger.warning(f"推荐理由生成失败，跳过：{e}")

        # 7. 更新 session 历史
        session_manager.append(session_id, "user", user_message)
        if not stream:
            session_manager.append(session_id, "assistant", nl_response if isinstance(nl_response, str) else "")

        logger.info(f"[{session_id}] 推荐完成，返回 {len(structured_results)} 条结果")
        return nl_response, structured_results, session_id

    def _handle_chitchat(self, message: str, history: list) -> str:
        """处理闲聊意图，直接调用 LLM 回复。"""
        try:
            from ai_config.llm_client import chat_completion
            msgs = [
                {"role": "system", "content": "你是一个友好的影视推荐助手，用简短自然的中文回复用户的闲聊。如果用户想聊影视相关话题，引导他们提出推荐需求。"},
            ]
            for msg in history[-4:]:
                if msg.get("role") in ("user", "assistant"):
                    msgs.append(msg)
            msgs.append({"role": "user", "content": message})
            resp = chat_completion(msgs, temperature=0.8, max_tokens=256)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"闲聊回复失败：{e}")
            return "您好！我是影视推荐助手，可以为您推荐电影或剧集。请告诉我您的喜好！"
