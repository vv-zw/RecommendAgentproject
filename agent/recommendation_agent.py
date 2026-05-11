# agent/recommendation_agent.py
"""
AgentManager：向后兼容包装器。
内部委托给 AgentOrchestrator，保持原有方法签名不变。
"""
import logging
from typing import Optional, Union, Generator

logger = logging.getLogger(__name__)


class AgentManager:
    """
    向后兼容的 Agent 主入口类。
    内部委托给 AgentOrchestrator，保持原有方法签名不变。
    """

    def __init__(self):
        from agent.orchestrator import AgentOrchestrator
        self._orchestrator = AgentOrchestrator()

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
        委托给 AgentOrchestrator 处理。

        Args:
            user_id: 用户 ID
            user_message: 用户输入的自然语言消息
            preference_context: 用户偏好上下文 {'genres', 'directors', 'actors'}
            session_id: 对话 session ID，None 时自动创建
            stream: 是否启用流式输出

        Returns:
            (nl_response, structured_results, session_id) 三元组
        """
        return self._orchestrator.process_user_request(
            user_id=user_id,
            user_message=user_message,
            preference_context=preference_context,
            session_id=session_id,
            stream=stream,
        )
