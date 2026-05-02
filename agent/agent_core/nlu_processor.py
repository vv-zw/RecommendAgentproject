# agent/agent_core/nlu_processor.py

class NLUProcessor:
    def process(self, text: str):
        # Basic rule-based intent and entity recognition
        text = text.lower()
        if "recommend" in text or "suggest" in text:
            intent = "recommend_movie"
        elif "search" in text or "find" in text:
            intent = "search_movie"
        elif "add" in text and "watchlist" in text:
            intent = "add_to_watchlist"
        else:
            intent = "unknown_intent"
        
        entities = {}
        # Dummy entity extraction
        if "comedy" in text:
            entities['genre'] = 'Comedy'
        if "sci-fi" in text:
            entities['genre'] = 'Science Fiction'

        return intent, entities
