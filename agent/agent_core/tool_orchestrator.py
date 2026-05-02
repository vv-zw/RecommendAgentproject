# agent/agent_core/tool_orchestrator.py

# This would be expanded with actual tool classes
from movie_recommendation.db.content_repository import ContentRepository
from movie_recommendation.db.feedback_repository import FeedbackRepository

class ToolOrchestrator:
    def __init__(self):
        self.content_repo = ContentRepository()
        self.feedback_repo = FeedbackRepository()

    def execute_tools(self, user_id: str, intent: str, entities: dict):
        results = {}
        if intent == "search_movie":
            query = entities.get('query', '') # A more robust entity extraction is needed
            results, _ = self.content_repo.search_media(query)
        elif intent == "recommend_movie":
            # This is a placeholder. A real recommendation engine would be called here.
            results, _ = self.content_repo.get_media_list('movie', sort_by='popularity.desc')
        elif intent == "add_to_watchlist":
            media_id = entities.get('media_id') # Needs to be extracted from text
            if media_id:
                self.feedback_repo.add_to_watchlist(user_id, media_id)
                results = {"status": "success"}
            else:
                results = {"status": "failure", "reason": "media_id not provided"}
        
        return results
