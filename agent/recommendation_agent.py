# agent/recommendation_agent.py

from .agent_core.nlu_processor import NLUProcessor
from .agent_core.tool_orchestrator import ToolOrchestrator
from .agent_core.response_generator import ResponseGenerator

class AgentManager:
    def __init__(self):
        self.nlu_processor = NLUProcessor()
        self.tool_orchestrator = ToolOrchestrator()
        self.response_generator = ResponseGenerator()

    def process_user_request(self, user_id: str, user_message: str):
        # 1. Natural Language Understanding
        intent, entities = self.nlu_processor.process(user_message)

        # 2. Tool Selection & Orchestration
        tool_results = self.tool_orchestrator.execute_tools(user_id, intent, entities)

        # 3. Response Generation
        natural_language_response, structured_results = self.response_generator.generate_response(
            user_id, intent, tool_results
        )

        return natural_language_response, structured_results
