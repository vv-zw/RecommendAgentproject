# agent/agent_core/response_generator.py

class ResponseGenerator:
    def generate_response(self, user_id: str, intent: str, tool_results: dict):
        nl_response = "I'm not sure how to respond to that."
        structured_results = []

        if intent == "recommend_movie" or intent == "search_movie":
            if tool_results:
                nl_response = "Here are some movies you might like:"
                structured_results = tool_results
            else:
                nl_response = "I couldn't find any movies that match your request."
        
        elif intent == "add_to_watchlist":
            if tool_results.get("status") == "success":
                nl_response = "I've added it to your watchlist."
            else:
                nl_response = "I couldn't add it to your watchlist. Please make sure to specify the movie."

        return nl_response, structured_results
