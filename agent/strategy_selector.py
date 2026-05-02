# agent/strategy_selector.py
from typing import Dict, Any

def select_strategy(intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Selects the recommendation strategy based on intent, features, and user context.
    :param intent: The user's intent (e.g., 'recommend').
    :param context: The user's context, including history.
    :return: A dictionary containing the strategy decisions.
    """
    use_ncf = False
    use_textcnn = False
    use_rules = False
    use_rag = False  # RAG is always false in this phase, as per requirements.

    # Default strategy for recommendation intent
    if intent == "recommend":
        use_ncf = True
        use_textcnn = True
        use_rules = True

        # Cold-start scenario: user has no history
        user_history = context.get("history", [])
        if not user_history:
            use_ncf = False  # NCF is not suitable for cold starts

    # As per the example, explain_required is true for recommend intent.
    # It is also true if the user explicitly asks for an explanation.
    explain_required = (intent == "explain" or intent == "recommend")

    return {
        "strategy": {
            "use_ncf": use_ncf,
            "use_textcnn": use_textcnn,
            "use_rules": use_rules,
            "use_rag": use_rag
        },
        "explain_required": explain_required
    }

if __name__ == '__main__':
    print("--- Testing strategy_selector.py ---")
    
    # Test Case 1: Standard user
    intent_1 = "recommend"
    context_1 = {"history": [123, 456]}
    strategy_1 = select_strategy(intent_1, context_1)
    print(f"Intent: {intent_1}, Context: Has History -> Strategy: {strategy_1}")

    # Test Case 2: Cold-start user
    intent_2 = "recommend"
    context_2 = {"history": []}
    strategy_2 = select_strategy(intent_2, context_2)
    print(f"Intent: {intent_2}, Context: No History -> Strategy: {strategy_2}")

    # Test Case 3: Search intent
    intent_3 = "search"
    context_3 = {"history": [123, 456]}
    strategy_3 = select_strategy(intent_3, context_3)
    print(f"Intent: {intent_3}, Context: Has History -> Strategy: {strategy_3}")
