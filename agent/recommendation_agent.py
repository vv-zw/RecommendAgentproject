# agent/recommendation_agent.py

from .agent_core.nlu_processor import NLUProcessor
from .agent_core.tool_orchestrator import ToolOrchestrator
from .agent_core.response_generator import ResponseGenerator


class AgentManager:
    def __init__(self):
        self.nlu_processor = NLUProcessor()
        self.tool_orchestrator = ToolOrchestrator()
        self.response_generator = ResponseGenerator()

    def process_user_request(
        self,
        user_id: str,
        user_message: str,
        preference_context: dict | None = None
    ):
        """
        处理用户请求并返回推荐结果。

        Args:
            user_id: 用户 ID
            user_message: 用户输入的自然语言消息
            preference_context: 用户偏好上下文，格式为
                {'genres': [...], 'directors': [...], 'actors': [...]}
                为 None 时表示无偏好数据（冷启动或未登录）
        """
        # 1. 自然语言理解
        intent, entities = self.nlu_processor.process(user_message)

        # 2. 工具编排（传入偏好上下文）
        tool_results = self.tool_orchestrator.execute_tools(
            user_id, intent, entities, preference_context
        )

        # 3. 响应生成（传入偏好上下文以生成个性化回复）
        natural_language_response, structured_results = self.response_generator.generate_response(
            user_id, intent, tool_results, preference_context
        )

        return natural_language_response, structured_results
